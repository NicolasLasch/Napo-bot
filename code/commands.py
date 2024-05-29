import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from utils import save_data, load_data, rank_sort_key
from views import ClaimButton, GemButton, Paginator, GlobalPaginator

# Define global variables for tracking rolls
roll_cooldowns = {}
max_rolls_per_hour = 5
claim_cooldowns = {}
max_claims_per_3_hours = 1

# Define probability distribution
base_probabilities = {
    'SS': 0.01,
    'S': 0.05,
    'A': 0.1,
    'B': 0.2,
    'C': 0.25,
    'D': 0.2,
    'E': 0.19
}

def setup_commands(bot, cards, user_collections, user_data):

    def get_user_probabilities(user_id):
        base_chances = base_probabilities.copy()
        if user_id in user_data and 'luck' in user_data[user_id]:
            luck_bonus = user_data[user_id]['luck']
            for rank in base_chances:
                base_chances[rank] += luck_bonus.get(rank, 0)
            total = sum(base_chances.values())
            for rank in base_chances:
                base_chances[rank] /= total
        return base_chances

    def roll_card(user_id):
        probabilities = get_user_probabilities(user_id)
        ranks = list(probabilities.keys())
        chances = list(probabilities.values())
        rank = random.choices(ranks, chances)[0]
        possible_cards = [card for card in cards if card['rank'] == rank]
        return random.choice(possible_cards)

    @bot.tree.command(name="add_character", description="Add a new character card")
    @app_commands.describe(name="name", value="value", rank="rank", description="description", image_urls="image_urls")
    async def add_character(interaction: discord.Interaction, name: str, value: int, rank: str, description: str, image_urls: str):
        """Command to add a new card."""
        image_url_list = image_urls.split(';')
        card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_urls': image_url_list, 'claimed_by': None}
        cards.append(card)
        save_data(cards, user_collections, user_data)
        await interaction.response.send_message(f'Character {name} added successfully!', ephemeral=True)

    @bot.command(name="add_character")
    async def add_character_cmd(ctx, name: str, value: int, rank: str, description: str, image_urls: str):
        """Command to add a new card."""
        image_url_list = image_urls.split(';')
        card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_urls': image_url_list, 'claimed_by': None}
        cards.append(card)
        save_data(cards, user_collections, user_data)
        await ctx.send(f'Character {name} added successfully!')

    @bot.command(name="roll")
    @commands.cooldown(max_rolls_per_hour, 3600, commands.BucketType.user)
    async def roll(ctx):
        """Command to roll a random card."""
        user_id = str(ctx.author.id)
        now = datetime.utcnow()

        if user_id in roll_cooldowns and now < roll_cooldowns[user_id]:
            remaining_time = roll_cooldowns[user_id] - now
            await ctx.send(f'You have to wait {remaining_time.seconds // 60} minutes before being able to roll again.')
            return

        card = roll_card(user_id)

        embed = discord.Embed(title=card['name'], description=card['description'])
        embed.add_field(name="Rank", value=card['rank'])
        embed.add_field(name="Value", value=f"{card['value']} 💎")
        claimed_by = f"Claimed: None" if not card['claimed_by'] else f"Claimed: <@{card['claimed_by']}>"
        embed.add_field(name="Claimed", value=claimed_by)
        embed.set_image(url=card['image_urls'][0])

        view = discord.ui.View()
        if card['claimed_by']:
            embed.color = discord.Color.red()
            view.add_item(GemButton(card, user_data, user_collections, cards))
        else:
            embed.color = discord.Color.orange()
            view.add_item(ClaimButton(card, user_data, user_collections, cards))

        message = await ctx.send(embed=embed, view=view)
        await asyncio.sleep(45)
        await message.edit(content="Time to claim the character has expired.", view=None)

        roll_cooldowns[user_id] = now + timedelta(seconds=3600)

    @bot.tree.command(name="roll", description="Roll a random character card")
    async def roll_app(interaction: discord.Interaction):
        """Command to roll a random card."""
        user_id = str(interaction.user.id)
        now = datetime.utcnow()

        if user_id in roll_cooldowns and now < roll_cooldowns[user_id]:
            remaining_time = roll_cooldowns[user_id] - now
            await interaction.response.send_message(f'You have to wait {remaining_time.seconds // 60} minutes before being able to roll again.', ephemeral=True)
            return

        card = roll_card(user_id)

        embed = discord.Embed(title=card['name'], description=card['description'])
        embed.add_field(name="Rank", value=card['rank'])
        embed.add_field(name="Value", value=f"{card['value']} 💎")
        claimed_by = f"Claimed: None" if not card['claimed_by'] else f"Claimed: <@{card['claimed_by']}>"
        embed.add_field(name="Claimed", value=claimed_by)
        embed.set_image(url=card['image_urls'][0])

        view = discord.ui.View()
        if card['claimed_by']:
            embed.color = discord.Color.red()
            view.add_item(GemButton(card, user_data, user_collections, cards))
        else:
            embed.color = discord.Color.orange()
            view.add_item(ClaimButton(card, user_data, user_collections, cards))

        message = await interaction.response.send_message(embed=embed, view=view)
        await asyncio.sleep(45)
        await message.edit(content="Time to claim the character has expired.", view=None)

        roll_cooldowns[user_id] = now + timedelta(seconds=3600)

    @bot.command(name="mm")
    async def mm(ctx):
        """Command to display the user's collection."""
        user_id = str(ctx.author.id)
        if user_id not in user_collections or not user_collections[user_id]:
            await ctx.send('You have no cards in your collection.')
            return

        collection = user_collections[user_id]
        collection_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']})" for card in collection[:10]])
        embed = discord.Embed(title="Your Collection", description=collection_list)
        await ctx.send(embed=embed)

    @bot.tree.command(name="mm", description="Display your card collection")
    async def mm_app(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in user_collections or not user_collections[user_id]:
            await interaction.response.send_message('You have no cards in your collection.', ephemeral=True)
            return

        collection = user_collections[user_id]
        collection_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']})" for card in collection[:10]])
        embed = discord.Embed(title="Your Collection", description=collection_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="top")
    async def top(ctx):
        """Command to display the top characters globally."""
        if not cards:
            await ctx.send('No cards available.')
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        top_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']})" for card in sorted_cards[:10]])
        embed = discord.Embed(title="Top Characters", description=top_list)
        await ctx.send(embed=embed)

    @bot.tree.command(name="top", description="Display the top characters globally")
    async def top_app(interaction: discord.Interaction):
        if not cards:
            await interaction.response.send_message('No cards available.', ephemeral=True)
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        top_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']})" for card in sorted_cards[:10]])
        embed = discord.Embed(title="Top Characters", description=top_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="mmi")
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

        paginator = Paginator(collection)
        await paginator.send_initial_message(ctx)

    @bot.tree.command(name="mmi", description="Display your claimed cards with images")
    async def mmi_app(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if str(user_id) not in user_collections or not user_collections[str(user_id)]:
            await interaction.response.send_message('You have no cards in your collection.', ephemeral=True)
            return

        collection = [card for card in user_collections[str(user_id)] if card['claimed_by'] == str(user_id)]
        if not collection:
            await interaction.response.send_message('You have no claimed cards in your collection.', ephemeral=True)
            return

        paginator = Paginator(collection)
        await paginator.send_initial_message(interaction)

    @bot.command(name="topi")
    async def topi(ctx):
        """Command to display the top characters globally with images."""
        if not cards:
            await ctx.send('No cards available.')
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        paginator = GlobalPaginator(sorted_cards)
        await paginator.send_initial_message(ctx)

    @bot.tree.command(name="topi", description="Display the top characters globally with images")
    async def topi_app(interaction: discord.Interaction):
        if not cards:
            await interaction.response.send_message('No cards available.', ephemeral=True)
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        paginator = GlobalPaginator(sorted_cards)
        await paginator.send_initial_message(interaction)

    @bot.command(name="im")
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
        embed.set_image(url=card["image_urls"][0])
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
        await ctx.send(embed=embed)

    @bot.tree.command(name="im", description="Display detailed information about a card")
    async def im_app(interaction: discord.Interaction, name: str):
        card = next((c for c in cards if c['name'].lower() == name.lower()), None)
        if not card:
            await interaction.response.send_message('Card not found.', ephemeral=True)
            return

        claimed_status = "Not claimed" if not card["claimed_by"] else f'Claimed by <@{card["claimed_by"]}>'
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name="Rank", value=card["rank"])
        embed.add_field(name="Value", value=card["value"])
        embed.add_field(name="Claimed", value=claimed_status)
        embed.set_image(url=card["image_urls"][0])
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="luck")
    async def luck(ctx):
        """Command to display the user's current luck percentages."""
        user_id = str(ctx.author.id)
        probabilities = get_user_probabilities(user_id)
        embed = discord.Embed(title="Your Luck Percentages")
        for rank, chance in probabilities.items():
            embed.add_field(name=rank, value=f"{chance:.2%}")
        await ctx.send(embed=embed)

    @bot.tree.command(name="luck", description="Display your current luck percentages")
    async def luck_app(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        probabilities = get_user_probabilities(user_id)
        embed = discord.Embed(title="Your Luck Percentages")
        for rank, chance in probabilities.items():
            embed.add_field(name=rank, value=f"{chance:.2%}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="buyluck")
    async def buyluck(ctx):
        """Command to buy increased luck percentages."""
        user_id = str(ctx.author.id)
        if user_id not in user_data:
            user_data[user_id] = {}
        if 'coins' not in user_data[user_id] or user_data[user_id]['coins'] < 100:
            await ctx.send("You don't have enough coins to buy luck.")
            return

        user_data[user_id]['coins'] -= 100
        if 'luck' not in user_data[user_id]:
            user_data[user_id]['luck'] = {'SS': 0.01, 'S': 0.02, 'A': 0.03, 'B': 0.04, 'C': 0.05, 'D': 0.05, 'E': 0.05}
        else:
            for rank in user_data[user_id]['luck']:
                user_data[user_id]['luck'][rank] += 0.01

        save_data(cards, user_collections, user_data)
        await ctx.send("Your luck percentages have been increased!")

    @bot.tree.command(name="buyluck", description="Buy increased luck percentages")
    async def buyluck_app(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in user_data:
            user_data[user_id] = {}
        if 'coins' not in user_data[user_id] or user_data[user_id]['coins'] < 100:
            await interaction.response.send_message("You don't have enough coins to buy luck.", ephemeral=True)
            return

        user_data[user_id]['coins'] -= 100
        if 'luck' not in user_data[user_id]:
            user_data[user_id]['luck'] = {'SS': 0.01, 'S': 0.02, 'A': 0.03, 'B': 0.04, 'C': 0.05, 'D': 0.05, 'E': 0.05}
        else:
            for rank in user_data[user_id]['luck']:
                user_data[user_id]['luck'][rank] += 0.01

        save_data(cards, user_collections, user_data)
        await interaction.response.send_message("Your luck percentages have been increased!", ephemeral=True)

    @bot.command(name="download_data")
    async def download_data(ctx):
        """Command to download the JSON files."""
        await ctx.send(file=discord.File('cards.json'))
        await ctx.send(file=discord.File('collections.json'))
        await ctx.send(file=discord.File('user_data.json'))

    @bot.tree.command(name="download_data", description="Download the current data as JSON files")
    async def download_data_app(interaction: discord.Interaction):
        """Slash command to download the JSON files."""
        await interaction.response.send_message("Downloading data...", ephemeral=True)
        await interaction.followup.send(file=discord.File('cards.json'))
        await interaction.followup.send(file=discord.File('collections.json'))
        await interaction.followup.send(file=discord.File('user_data.json'))

    @bot.command(name="upload_data")
    async def upload_data(ctx, cards_file: discord.Attachment, collections_file: discord.Attachment, user_data_file: discord.Attachment):
        """Command to upload the JSON files."""
        await cards_file.save('cards.json')
        await collections_file.save('collections.json')
        await user_data_file.save('user_data.json')
        global cards, user_collections, user_data
        cards, user_collections, user_data = load_data()
        await ctx.send("Data uploaded and loaded successfully!")

    @bot.tree.command(name="upload_data", description="Upload the current data as JSON files")
    @app_commands.describe(cards_file="The cards JSON file", collections_file="The collections JSON file", user_data_file="The user data JSON file")
    async def upload_data_app(interaction: discord.Interaction, cards_file: discord.Attachment, collections_file: discord.Attachment, user_data_file: discord.Attachment):
        """Slash command to upload the JSON files."""
        await cards_file.save('cards.json')
        await collections_file.save('collections.json')
        await user_data_file.save('user_data.json')
        global cards, user_collections, user_data
        cards, user_collections, user_data = load_data()
        await interaction.response.send_message("Data uploaded and loaded successfully!", ephemeral=True)
