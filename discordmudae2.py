import json
import discord
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont
import io

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Paths to JSON files
CARDS_FILE = 'cards.json'
COLLECTIONS_FILE = 'collections.json'

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

    return cards, user_collections

# Save data to JSON files
def save_data(cards, user_collections):
    with open(CARDS_FILE, 'w') as f:
        json.dump(cards, f, indent=4)

    with open(COLLECTIONS_FILE, 'w') as f:
        json.dump(user_collections, f, indent=4)

cards, user_collections = load_data()

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.command()
async def add_card(ctx, name: str, value: int, rank: str, description: str, image_url: str):
    """Command to add a new card."""
    card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_url': image_url, 'claimed_by': None}
    cards.append(card)
    save_data(cards, user_collections)
    await ctx.send(f'Card {name} added successfully!')

@bot.command()
async def roll(ctx):
    """Command to roll a random card."""
    if not cards:
        await ctx.send('No cards available. Please add cards first.')
        return
    
    card = random.choice(cards)
    user = ctx.message.author
    
    if str(user.id) not in user_collections:
        user_collections[str(user.id)] = []
    
    user_collections[str(user.id)].append(card)
    card['claimed_by'] = user.id
    save_data(cards, user_collections)
    await ctx.send(f'You rolled: {card["name"]} ({card["rank"]}) - {card["description"]}')

@bot.command()
async def mm(ctx):
    """Command to display the user's collection in text."""
    user = ctx.message.author
    if str(user.id) not in user_collections or not user_collections[str(user.id)]:
        await ctx.send('You have no cards in your collection.')
        return
    
    collection = user_collections[str(user.id)]
    collection_list = '\n'.join([f'{card["name"]} ({card["rank"]}) - {card["description"]} (Value: {card["value"]})' for card in collection])
    await ctx.send(f'Your collection:\n{collection_list}')

@bot.command()
async def mmi(ctx):
    """Command to display the user's collection with images."""
    user = ctx.message.author
    if str(user.id) not in user_collections or not user_collections[str(user.id)]:
        await ctx.send('You have no cards in your collection.')
        return
    
    collection = user_collections[str(user.id)]
    for card in collection:
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name="Rank", value=card["rank"])
        embed.add_field(name="Value", value=card["value"])
        embed.set_image(url=card["image_url"])
        await ctx.send(embed=embed)

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
    embed.add_field(name="Value", value=card["value"])
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
    
    save_data(cards, user_collections)
    await ctx.send(f'Trade successful! {sender.display_name} traded {card_name} with {user.display_name} for {trade_card_name}.')

@bot.command()
async def add_card_code(name: str, value: int, rank: str, description: str, image_url: str):
    """Function to add a new card directly in the code."""
    card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_url': image_url, 'claimed_by': None}
    cards.append(card)
    save_data(cards, user_collections)
    print(f'Card {name} added successfully!')

# Add cards directly in the code
add_card_code('Hero', 150, 'A', 'A brave hero.', 'http://example.com/hero.png')
add_card_code('Villain', 120, 'B', 'A cunning villain.', 'http://example.com/villain.png')

bot.run('YOUR_DISCORD_BOT_TOKEN')
