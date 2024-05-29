import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # Ensure message content intent is enabled

bot = commands.Bot(command_prefix="!", intents=intents)

# Paths to JSON files
CARDS_FILE = 'cards.json'
COLLECTIONS_FILE = 'collections.json'
USER_DATA_FILE = 'userdata.json'

# Load data from JSON files
def load_data():
    try:
        with open(CARDS_FILE, 'r') as f:
            cards = json.load(f)
    except FileNotFoundError:
        cards = []

    try:
        with open(COLLECTIONS_FILE, 'r') as f:
            user_collections = json.load(f)
    except FileNotFoundError:
        user_collections = {}

    try:
        with open(USER_DATA_FILE, 'r') as f:
            user_data = json.load(f)
    except FileNotFoundError:
        user_data = {}

    return cards, user_collections, user_data

# Save data to JSON files
def save_data(cards, user_collections, user_data):
    with open(CARDS_FILE, 'w') as f:
        json.dump(cards, f, indent=4)

    with open(COLLECTIONS_FILE, 'w') as f:
        json.dump(user_collections, f, indent=4)

    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)

cards, user_collections, user_data = load_data()

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

@bot.tree.command(name="add_card", description="Add a new card")
@app_commands.describe(name="Name of the card", value="Value of the card", rank="Rank of the card", description="Description of the card", image_url="Image URL of the card")
async def add_card(interaction: discord.Interaction, name: str, value: int, rank: str, description: str, image_url: str):
    """Command to add a new card."""
    card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_url': image_url, 'claimed_by': None}
    cards.append(card)
    save_data(cards, user_collections, user_data)
    await interaction.response.send_message(f'Card {name} added successfully!', ephemeral=True)

class ClaimButton(discord.ui.Button):
    def __init__(self, card, user_data, user_collections):
        super().__init__(label="Claim", style=discord.ButtonStyle.primary)
        self.card = card
        self.user_data = user_data
        self.user_collections = user_collections

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if 'last_claim_time' not in self.user_data.get(user_id, {}):
            self.user_data.setdefault(user_id, {})['last_claim_time'] = str(datetime.utcnow() - timedelta(hours=4))

        last_claim_time = datetime.fromisoformat(self.user_data[user_id]['last_claim_time'])
        if datetime.utcnow() - last_claim_time < timedelta(hours=3):
            await interaction.response.send_message("You can only claim once every 3 hours.", ephemeral=True)
            return

        self.user_data[user_id]['last_claim_time'] = str(datetime.utcnow())

        if self.card['claimed_by']:
            await interaction.response.send_message(f"This card is already claimed by <@{self.card['claimed_by']}>. You receive 100 coins!", ephemeral=True)
            self.user_data.setdefault(user_id, {}).setdefault('coins', 0)
            self.user_data[user_id]['coins'] += 100
        else:
            self.card['claimed_by'] = user_id
            self.user_collections.setdefault(user_id, []).append(self.card)
            await interaction.response.send_message(f"You have claimed {self.card['name']}!", ephemeral=True)
        
        save_data(cards, user_collections, user_data)

class GemButton(discord.ui.Button):
    def __init__(self, card, user_data, user_collections):
        super().__init__(label="💎", style=discord.ButtonStyle.secondary)
        self.card = card
        self.user_data = user_data
        self.user_collections = user_collections

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if 'last_gem_time' not in self.user_data.get(user_id, {}):
            self.user_data.setdefault(user_id, {})['last_gem_time'] = str(datetime.utcnow() - timedelta(hours=4))

        last_gem_time = datetime.fromisoformat(self.user_data[user_id]['last_gem_time'])
        if datetime.utcnow() - last_gem_time < timedelta(hours=3):
            await interaction.response.send_message("You can only collect gems once every 3 hours.", ephemeral=True)
            return

        self.user_data[user_id]['last_gem_time'] = str(datetime.utcnow())
        self.user_data.setdefault(user_id, {}).setdefault('coins', 0)
        self.user_data[user_id]['coins'] += self.card['value']

        save_data(cards, user_collections, user_data)
        await interaction.response.send_message(f"You received {self.card['value']} coins from the gem!", ephemeral=True)

@bot.command()
@commands.cooldown(5, 3600, commands.BucketType.user)
async def roll(ctx):
    """Command to roll a random card."""
    if not cards:
        await ctx.send('No cards available. Please add cards first.')
        return

    card = random.choice(cards)
    user_id = str(ctx.author.id)

    embed = discord.Embed(title=card['name'], description=card['description'])
    embed.add_field(name="Rank", value=card['rank'])
    embed.add_field(name="Value", value=f"{card['value']} 💎")
    embed.set_image(url=card['image_url'])

    view = discord.ui.View()
    if card['claimed_by']:
        embed.color = discord.Color.red()
        view.add_item(GemButton(card, user_data, user_collections))
    else:
        embed.color = discord.Color.orange()
        view.add_item(ClaimButton(card, user_data, user_collections))

    await ctx.send(embed=embed, view=view)

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    coins = user_data.get(user_id, {}).get('coins', 0)
    await ctx.send(f"You have {coins} coins.")

@bot.command()
async def buyluck(ctx):
    user_id = str(ctx.author.id)
    coins = user_data.get(user_id, {}).get('coins', 0)
    if coins < 500:
        await ctx.send("You need at least 500 coins to buy more luck.")
        return

    user_data[user_id]['coins'] -= 500
    user_data[user_id].setdefault('luck', 0)
    user_data[user_id]['luck'] += 1
    save_data(cards, user_collections, user_data)
    await ctx.send("You have purchased more luck for 500 coins!")

class Paginator(discord.ui.View):
    def __init__(self, ctx, collection, user_data):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.collection = collection
        self.user_data = user_data
        self.current_page = 0

    async def send_initial_message(self):
        embed = self.create_embed()
        await self.ctx.send(embed=embed, view=self)

    def create_embed(self):
        card = self.collection[self.current_page]
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name="Rank", value=card["rank"])
        embed.add_field(name="Value", value=f'{card["value"]} 💎')
        embed.set_image(url=card["image_url"])
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page < len(self.collection) - 1:
            self.current_page += 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

@bot.command()
async def mmi(ctx):
    """Command to display the user's collection with images."""
    user = ctx.message.author
    if str(user.id) not in user_collections or not user_collections[str(user.id)]:
        await ctx.send('You have no cards in your collection.')
        return

    collection = [card for card in user_collections[str(user.id)] if card['claimed_by'] == str(user.id)]
    if not collection:
        await ctx.send('You have no claimed cards in your collection.')
        return

    paginator = Paginator(ctx, collection, user_data)
    await paginator.send_initial_message()

@bot.command()
async def mm(ctx, page: int = 1):
    """Command to display the user's collection in text."""
    user = ctx.message.author
    if str(user.id) not in user_collections or not user_collections[str(user.id)]:
        await ctx.send('You have no cards in your collection.')
        return

    collection = user_collections[str(user.id)]
    items_per_page = 10
    total_pages = (len(collection) + items_per_page - 1) // items_per_page

    if page < 1 or page > total_pages:
        await ctx.send(f'Page {page} is out of range. There are {total_pages} pages in total.')
        return

    start = (page - 1) * items_per_page
    end = start + items_per_page
    collection_page = collection[start:end]
    collection_list = '\n'.join([f'**{card["name"]}** ({card["rank"]}) - {card["description"]} (Value: {card["value"]} 💎)' for card in collection_page])
    await ctx.send(f'Your collection (Page {page}/{total_pages}):\n{collection_list}')

@bot.command()
async def im(ctx, name: str):
    """Command to display detailed information about a card."""
    card = next((c for c in cards if c['name'].lower() == name.lower()), None)
    if not card:
        await ctx.send('Card not found.')
        return

    claimed_status = "Not claimed" if not card["claimed_by"] else f'Claimed by <@{card["claimed_by"]}>'
    embed = discord.Embed(title=card["name"], description=card["description"])
    embed.add_field(name="Rank", value=card["rank"])
    embed.add_field(name="Value", value=f'{card["value"]} 💎')
    embed.add_field(name="Claimed", value=claimed_status)
    embed.set_image(url=card["image_url"])
    await ctx.send(embed=embed)

@bot.command()
async def trade(ctx, user: discord.User, card_name: str, trade_card_name: str):
    """Command to trade cards with another user."""
    sender = ctx.message.author

    if str(sender.id) not in user_collections or not user_collections[str(sender.id)]:
        await ctx.send('You have no cards to trade.')
        return

    sender_card = next((c for c in user_collections[str(sender.id)] if c['name'].lower() == card_name.lower()), None)
    receiver_card = next((c for c in user_collections[str(user.id)] if c['name'].lower() == trade_card_name.lower()), None)

    if not sender_card:
        await ctx.send(f'You do not have the card {card_name}.')
        return

    if not receiver_card:
        await ctx.send(f'{user.display_name} does not have the card {trade_card_name}.')
        return

    # Perform the trade
    user_collections[str(sender.id)].remove(sender_card)
    user_collections[str(user.id)].remove(receiver_card)
    user_collections[str(sender.id)].append(receiver_card)
    user_collections[str(user.id)].append(sender_card)

    sender_card['claimed_by'] = user.id
    receiver_card['claimed_by'] = sender.id

    save_data(cards, user_collections, user_data)
    await ctx.send(f'Trade successful! {sender.display_name} traded {card_name} with {user.display_name} for {trade_card_name}.')

@bot.command()
async def divorce(ctx, name: str):
    """Command to divorce a character and receive their value."""
    user = ctx.message.author
    if str(user.id) not in user_collections or not user_collections[str(user.id)]:
        await ctx.send('You have no cards in your collection.')
        return

    card = next((c for c in user_collections[str(user.id)] if c['name'].lower() == name.lower()), None)
    if not card:
        await ctx.send(f'You do not have the card {name}.')
        return

    user_collections[str(user.id)].remove(card)
    user_data[str(user.id)]['coins'] = user_data.get(str(user.id), {}).get('coins', 0) + card['value']
    card['claimed_by'] = None

    save_data(cards, user_collections, user_data)
    await ctx.send(f'You have divorced {name} and received {card["value"]} coins.')

# Add initial cards directly to the list
initial_cards = [
    {'name': 'Hero', 'value': 150, 'rank': 'A', 'description': 'A brave hero.', 'image_url': 'http://example.com/hero.png', 'claimed_by': None},
    {'name': 'Villain', 'value': 120, 'rank': 'B', 'description': 'A cunning villain.', 'image_url': 'http://example.com/villain.png', 'claimed_by': None}
]
cards.extend(initial_cards)
save_data(cards, user_collections, user_data)

bot.run(os.getenv('DISCORD_BOT_TOKEN'))