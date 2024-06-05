import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from utils import save_data, load_data, rank_sort_key, get_time_until_next_reset, scores, quiz_data
from views import ClaimButton, GemButton, Paginator, GlobalPaginator, ImagePaginator
import os
from PIL import Image
import requests
import io
import aiohttp
import sys
from config import guild_data
import yt_dlp
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# Define global variables for tracking rolls
roll_cooldowns = {}
max_rolls_per_hour = 5
claim_cooldowns = {}
max_claims_per_3_hours = 1
MAX_WISHES = 3

# Define probability distribution
base_probabilities = {
    'SS': 0.0005,
    'S': 0.01,
    'A': 0.07,
    'B': 0.14,
    'C': 0.20,
    'D': 0.25,
    'E': 0.33
}

max_increment = {
    'SS': 0.00005,
    'S': 0.001,
    'A': 0.007,
    'B': 0.014,
    'C': 0.02,
    'D': 0.025,
    'E': 0.033
}

roll_cooldown = commands.CooldownMapping.from_cooldown(5, 3600, commands.BucketType.user)

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def reload_bot():
    os.execv(sys.executable, ['python'] + sys.argv)

def get_cooldown(bucket):
    retry_after = bucket.update_rate_limit()
    if retry_after:
        return False, retry_after
    return True, None

def setup_commands(bot):
    def initialize_guild(guild_id):
        if guild_id not in guild_data:
            guild_data[guild_id] = load_data(guild_id)

    def initialize_user(guild_id, user_id):
        if user_id not in guild_data[guild_id][2]:
            guild_data[guild_id][2][user_id] = {
                'coins': 0,
                'luck_purchases': 0,
                'luck': base_probabilities,
                'rolls': max_rolls_per_hour,
                'claims': max_claims_per_3_hours
            }

    def get_user_probabilities(guild_id, user_id):
        initialize_user(guild_id, user_id)
        base_chances = base_probabilities.copy()
        luck_bonus = guild_data[guild_id][2][user_id]['luck']
        for rank in base_chances:
            base_chances[rank] += luck_bonus.get(rank, 0)
        total = sum(base_chances.values())
        for rank in base_chances:
            base_chances[rank] /= total
        return base_chances

    def roll_card(guild_id, user_id):
        probabilities = get_user_probabilities(guild_id, user_id)
        ranks = list(probabilities.keys())
        rank_probabilities = []

        # Adjust probabilities based on the available cards
        for rank in ranks:
            rank_count = sum(1 for card in guild_data[guild_id][0] if card['rank'] == rank)
            if rank_count == 0:
                rank_probabilities.append(0)
            else:
                rank_probabilities.append(probabilities[rank])

        total_prob = sum(rank_probabilities)
        if total_prob == 0:
            return None

        # Normalize probabilities
        rank_probabilities = [prob / total_prob for prob in rank_probabilities]
        rank = random.choices(ranks, rank_probabilities)[0]

        possible_cards = [card for card in guild_data[guild_id][0] if card['rank'] == rank]
        return random.choice(possible_cards)

    @bot.tree.command(name="add_character", description="Add a new character card")
    @is_admin()
    @app_commands.describe(name="name", value="value", rank="rank", description="description", image_urls="image_urls")
    async def add_character(interaction: discord.Interaction, name: str, value: int, rank: str, description: str, image_urls: str):
        """Command to add a new card."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        image_url_list = image_urls.split(';')
        card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_urls': image_url_list, 'claimed_by': None}
        guild_data[guild_id][0].append(card)
        save_data(guild_id, *guild_data[guild_id])
        await interaction.response.send_message(f'Character {name} added successfully!', ephemeral=True)

    @bot.command(name="add_character")
    @is_admin()
    async def add_character_cmd(ctx, name: str, value: int, rank: str, description: str, image_urls: str):
        """Command to add a new card."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        image_url_list = image_urls.split(';')
        card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_urls': image_url_list, 'claimed_by': None}
        guild_data[guild_id][0].append(card)
        save_data(guild_id, *guild_data[guild_id])
        await ctx.send(f'Character {name} added successfully!')

    @bot.command(name="divorce")
    async def divorce(ctx, *, character_name: str):
        """Command to unclaim a character in exchange for its value."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        card = next((c for c in guild_data[guild_id][1].get(user_id, []) if c['name'].lower() == character_name.lower()), None)

        if not card:
            await ctx.send('Character not found in your collection.')
            return

        if card['claimed_by'] != user_id:
            await ctx.send('You do not own this character.')
            return

        guild_data[guild_id][1][user_id].remove(card)
        card['claimed_by'] = None
        guild_data[guild_id][2][user_id]['coins'] += card['value']

        save_data(guild_id, *guild_data[guild_id])
        await ctx.send(f'You have successfully divorced {character_name} and received {card["value"]} coins.')

    @bot.tree.command(name="divorce", description="Unclaim a character in exchange for its value")
    @app_commands.describe(character_name="Character name")
    async def divorce_app(interaction: discord.Interaction, character_name: str):
        """Slash command to unclaim a character in exchange for its value."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        user_id = str(interaction.user.id)
        card = next((c for c in guild_data[guild_id][1].get(user_id, []) if c['name'].lower() == character_name.lower()), None)

        if not card:
            await interaction.response.send_message('Character not found in your collection.', ephemeral=True)
            return

        if card['claimed_by'] != user_id:
            await interaction.response.send_message('You do not own this character.', ephemeral=True)
            return

        guild_data[guild_id][1][user_id].remove(card)
        card['claimed_by'] = None
        guild_data[guild_id][2][user_id]['coins'] += card['value']

        save_data(guild_id, *guild_data[guild_id])
        await interaction.response.send_message(f'You have successfully divorced {character_name} and received {card["value"]} coins.', ephemeral=True)

    @bot.command(name="roll")
    async def roll(ctx):
        """Command to roll (5 times) every hour."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        rolls_left = user_data[user_id].get('rolls', max_rolls_per_hour)
        if rolls_left <= 0:
            now = datetime.utcnow()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            minutes_left = (next_hour - now).seconds // 60
            await ctx.send(f'No rolls left. Rolls reset in {minutes_left} minutes.')
            return

        user_data[user_id]['rolls'] -= 1

        card = roll_card(guild_id, user_id)
        if not card:
            await ctx.send('No cards available for the current probability distribution.')
            return

        embed = discord.Embed(title=card['name'], description=card['description'])
        wished_by = []
        for member_id, data in guild_data[guild_id][2].items():
            if 'wishes' in data and card['name'] in data['wishes']:
                wished_by.append(f"<@{member_id}>")

        if wished_by:
            wished_users = ", ".join(wished_by)
            await ctx.send(f"🎉 Wished card! {wished_users}")

        if card['claimed_by']:
            user = await ctx.guild.fetch_member(card['claimed_by'])
            claimed_by = f'Claimed by {user.name}'
            profile_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed.set_footer(text=claimed_by, icon_url=profile_url)
            embed.color = discord.Color.red()
        else:
            embed.set_footer(text="Claimed by no one")
            embed.color = discord.Color.green() if wished_by else discord.Color.orange()

        embed.add_field(name=f"{card['value']} <:bluegem:1246468408963367003> - {card['rank']}", value="")
        embed.set_image(url=card['image_urls'][0])

        view = discord.ui.View()
        if card['claimed_by']:
            view.add_item(GemButton(guild_id, card, user_data, user_collections, cards))
        else:
            view.add_item(ClaimButton(guild_id, card, user_data, user_collections, cards))

        message = await ctx.send(embed=embed, view=view)
        await asyncio.sleep(45)
        await message.edit(content="Time to claim the character has expired.", view=None)

        save_data(guild_id, cards, user_collections, user_data)

    @bot.command(name="mm")
    async def mm(ctx, member: discord.Member = None):
        """Command to display the user's collection or another user's collection."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = ctx.author
        user_id = str(member.id)
        user_collections = guild_data[guild_id][1]
        if user_id not in user_collections or not user_collections[user_id]:
            await ctx.send(f'{member.display_name} has no cards in their collection.')
            return

        collection = user_collections[user_id]
        collection_list = '\n'.join([f"**({card['rank']})** • {card['name']} - *{card['description']}*" for card in collection[:10]])
        embed = discord.Embed(title="", description=collection_list)
        embed.set_author(name=f" • {member.display_name}'s Collection", icon_url=member.avatar.url)
        embed.set_thumbnail(url=collection[0]['image_urls'][0])
        await ctx.send(embed=embed)

    @bot.tree.command(name="mm", description="Display your card collection or another user's collection")
    @app_commands.describe(member="The member whose collection you want to see")
    async def mm_app(interaction: discord.Interaction, member: discord.Member = None):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = interaction.user
        user_id = str(member.id)
        user_collections = guild_data[guild_id][1]
        if user_id not in user_collections or not user_collections[user_id]:
            await interaction.response.send_message(f'{member.display_name} has no cards in their collection.', ephemeral=True)
            return

        collection = user_collections[user_id]
        collection_list = '\n'.join([f"**({card['rank']})** • {card['name']} - *{card['description']}*" for card in collection[:10]])
        embed = discord.Embed(title="", description=collection_list)
        embed.set_author(name=f" • {member.display_name}'s Collection", icon_url=member.avatar.url)
        embed.set_thumbnail(url=collection[0]['image_urls'][0])
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @bot.command(name="top")
    async def top(ctx):
        """Command to display the top characters globally."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        if not cards:
            await ctx.send('No cards available.')
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        top_list = '\n'.join([f"**({card['rank']})** • {card['name']} {'❤️' if card['claimed_by'] else ''}" for card in sorted_cards[:10]])
        embed = discord.Embed(title="<:naporight:1246789280211406888> • Top Characters", description=top_list)
        embed.set_thumbnail(url=sorted_cards[0]['image_urls'][0])
        await ctx.send(embed=embed)

    @bot.tree.command(name="top", description="Display the top characters globally")
    async def top_app(interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        if not cards:
            await interaction.response.send_message('No cards available.', ephemeral=True)
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        top_list = '\n'.join([f"**({card['rank']})** • {card['name']} {'❤️' if card['claimed_by'] else ''}" for card in sorted_cards[:10]])
        embed = discord.Embed(title="<:naporight:1246789280211406888> • Top Characters", description=top_list)
        embed.set_thumbnail(url=sorted_cards[0]['image_urls'][0])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="mmi")
    async def mmi(ctx, member: discord.Member = None):
        """Command to display the user's collection with images or another user's collection."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = ctx.author
        user_id = str(member.id)
        user_collections = guild_data[guild_id][1]
        if user_id not in user_collections or not user_collections[user_id]:
            await ctx.send(f'{member.display_name} has no cards in their collection.')
            return

        collection = [card for card in user_collections[user_id] if card['claimed_by'] == user_id]
        if not collection:
            await ctx.send(f'{member.display_name} has no claimed cards in their collection.')
            return

        paginator = Paginator(guild_id, collection)
        await paginator.send_initial_message(ctx)

    @bot.tree.command(name="mmi", description="Display your claimed cards with images or another user's claimed cards")
    @app_commands.describe(member="The member whose claimed cards you want to see")
    async def mmi_app(interaction: discord.Interaction, member: discord.Member = None):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = interaction.user
        user_id = str(member.id)
        user_collections = guild_data[guild_id][1]
        if user_id not in user_collections or not user_collections[user_id]:
            await interaction.response.send_message(f'{member.display_name} has no cards in their collection.', ephemeral=True)
            return

        collection = [card for card in user_collections[user_id] if card['claimed_by'] == user_id]
        if not collection:
            await interaction.response.send_message(f'{member.display_name} has no claimed cards in their collection.', ephemeral=True)
            return

        paginator = Paginator(guild_id, collection)
        await paginator.send_initial_message(interaction)


    @bot.command(name="topi")
    async def topi(ctx):
        """Command to display the top characters globally with images."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        if not cards:
            await ctx.send('No cards available.')
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        paginator = GlobalPaginator(guild_id, sorted_cards)
        await paginator.send_initial_message(ctx)

    @bot.tree.command(name="topi", description="Display the top characters globally with images")
    async def topi_app(interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        if not cards:
            await interaction.response.send_message('No cards available.', ephemeral=True)
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        paginator = GlobalPaginator(guild_id, sorted_cards)
        await paginator.send_initial_message(interaction)

    @bot.command(name="mu")
    async def mu(ctx):
        """Command to check the remaining time before the next global claim reset and if the user can claim."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        user_data = guild_data[guild_id][2]
        initialize_user(guild_id, user_id)

        time_until_reset = get_time_until_next_reset()
        hours, remainder = divmod(time_until_reset.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if 'claims' in user_data.get(user_id, {}):
            if user_data[user_id]['claims'] == 0:
                can_claim = False
            else:
                can_claim = True
        else:
            can_claim = True

        claim_status = "You can claim now!" if can_claim else f"You can claim again in **{hours}h {minutes}m**."
        await ctx.send(f"The next global claim reset is in **{hours}h {minutes}m**.\n{claim_status}")

    @bot.tree.command(name="mu", description="Check the remaining time before the next global claim reset and if the user can claim")
    async def mu_app(interaction: discord.Interaction):
        """Slash command to check the remaining time before the next global claim reset and if the user can claim."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        user_id = str(interaction.user.id)
        user_data = guild_data[guild_id][2]
        initialize_user(guild_id, user_id)

        time_until_reset = get_time_until_next_reset()
        hours, remainder = divmod(time_until_reset.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if 'claims' in user_data.get(user_id, {}):
            if user_data[user_id]['claims'] == 0:
                can_claim = False
            else:
                can_claim = True
        else:
            can_claim = True

        claim_status = "You can claim now!" if can_claim else f"You can claim again in **{hours}h {minutes}m**."
        await interaction.response.send_message(f"The next global claim reset is in **{hours}h {minutes}m**.\n{claim_status}", ephemeral=True)

    @bot.command(name="im")
    async def im(ctx, *, args: str):
        """Command to display detailed information about a card."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        
        # Split the arguments on the '$' character
        parts = args.split(" $ ")
        character_name = parts[0].strip()
        page_number = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 1

        card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
        if not card:
            await ctx.send('Card not found.')
            return

        paginator = ImagePaginator(guild_id, card, page_number - 1)
        await paginator.send_initial_message(ctx)

    @bot.tree.command(name="im", description="Display detailed information about a card with image navigation")
    @app_commands.describe(name="Character name", page_number="Page number (optional)")
    async def im_app(interaction: discord.Interaction, name: str, page_number: int = 1):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]

        card = next((c for c in cards if c['name'].lower() == name.lower()), None)
        if not card:
            await interaction.response.send_message('Card not found.', ephemeral=True)
            return

        paginator = ImagePaginator(guild_id, card, page_number - 1)
        await paginator.send_initial_message(interaction)

    
    @bot.command(name="ai")
    @is_admin()
    async def add_image(ctx, *, args: str):
        """Command to add an image to an existing character. Usage: !ai <character_name> $ <image_url>"""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        try:
            character_name, image_url = args.split(" $ ")
            character_name = character_name.strip()
            image_url = image_url.strip()
        except ValueError:
            await ctx.send("Invalid format. Use: !ai <character_name> $ <image_url>")
            return

        card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
        if not card:
            await ctx.send('Character not found.')
            return

        if 'image_urls' not in card:
            card['image_urls'] = []

        card['image_urls'].append(image_url)
        save_data(guild_id, *guild_data[guild_id])
        await ctx.send(f'Image added to character {character_name} successfully!')

    @bot.tree.command(name="add_image", description="Add an image to an existing character")
    @is_admin()
    @app_commands.describe(character_name="Character name", image_url="Image URL")
    async def add_image_app(interaction: discord.Interaction, character_name: str, image_url: str):
        """Slash command to add an image to an existing character."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
        if not card:
            await interaction.response.send_message('Character not found.', ephemeral=True)
            return

        if 'image_urls' not in card:
            card['image_urls'] = []

        card['image_urls'].append(image_url)
        save_data(guild_id, *guild_data[guild_id])
        await interaction.response.send_message(f'Image added to character {character_name} successfully!', ephemeral=True)

    @bot.command(name="balance")
    async def balance(ctx):
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        coins = user_data[user_id].get('coins', 0)
        await ctx.send(f'You have {coins} coins.')

    @bot.command(name="luck")
    async def luck(ctx, member: discord.Member = None):
        """Command to display the user's luck percentages or another user's luck percentages."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = ctx.author
        user_id = str(member.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        probabilities = get_user_probabilities(guild_id, user_id)
        embed = discord.Embed(title=f"{member.display_name}'s Luck Percentages")
        for rank, chance in probabilities.items():
            embed.add_field(name=rank, value=f"{chance:.2%}")
        await ctx.send(embed=embed)

    @bot.tree.command(name="luck", description="Display your luck percentages or another user's luck percentages")
    @app_commands.describe(member="The member whose luck percentages you want to see")
    async def luck_app(interaction: discord.Interaction, member: discord.Member = None):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = interaction.user
        user_id = str(member.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        probabilities = get_user_probabilities(guild_id, user_id)
        embed = discord.Embed(title=f"{member.display_name}'s Luck Percentages")
        for rank, chance in probabilities.items():
            embed.add_field(name=rank, value=f"{chance:.2%}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @bot.command(name="buyluck")
    async def buyluck(ctx):
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        user_info = user_data[user_id]
        coins = user_info['coins']
        luck_purchases = user_info['luck_purchases']

        cost = 500 * (2 ** luck_purchases)
        if luck_purchases >= 3:
            cost = 500 * (2 ** 2) + 2000 * (luck_purchases - 5)
            if cost >= 10000:
                cost = 10000

        if coins < cost:
            await ctx.send(f"You don't have enough coins to buy luck. You need {cost} coins.")
            return

        user_info['coins'] -= cost
        user_info['luck_purchases'] += 1

        # Adjust probabilities
        total_increment = sum(max_increment[rank] for rank in ['SS', 'S', 'A'])
        decrement_fraction = total_increment / sum(base_probabilities[rank] for rank in ['B', 'C', 'D', 'E'])

        for rank in base_probabilities:
            if rank in ['SS', 'S', 'A']:
                user_info['luck'][rank] += max_increment[rank]
            elif rank in ['B', 'C', 'D', 'E']:
                user_info['luck'][rank] -= base_probabilities[rank] * decrement_fraction

        # Normalize probabilities
        total = sum(user_info['luck'].values())
        for rank in user_info['luck']:
            user_info['luck'][rank] /= total

        save_data(guild_id, cards, user_collections, user_data)
        luck_purchases += 1
        next_cost = 500 * (2 ** luck_purchases)
        if luck_purchases >= 3:
            next_cost = 500 * (2 ** 2) + 2000 * (luck_purchases - 5)
            if next_cost >= 10000:
                next_cost = 10000
        await ctx.send(f"Your luck percentages have been increased! The next upgrade will cost {next_cost} coins.")
    
    @bot.command(name="upgrade")
    async def roulette(ctx, *, args: str):
        """Command to gamble a card for a chance to upgrade to another card."""
        try:
            character_name, target_character_name = args.split(" $ ")
            character_name = character_name.strip()
            target_character_name = target_character_name.strip()
        except ValueError:
            await ctx.send("Invalid format. Use: !upgrade <character_name> $ <target_character_name>")
            return

        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        user_id = str(ctx.author.id)
        user_collections = guild_data[guild_id][1]
        user_data = guild_data[guild_id][2]
        initialize_user(guild_id, user_id)

        # Check if the user owns the character they want to gamble
        card = next((c for c in user_collections.get(user_id, []) if c['name'].lower() == character_name.lower()), None)
        if not card:
            await ctx.send('You do not own this character.')
            return

        # Check if the target character is not claimed
        target_card = next((c for c in cards if c['name'].lower() == target_character_name.lower()), None)
        if not target_card:
            await ctx.send('Target character not found.')
            return

        if target_card['claimed_by']:
            await ctx.send('Target character is already claimed.')
            return

        # Calculate the upgrade cost and probability
        card_value = card['value']
        target_value = target_card['value']
        if card_value >= target_value:
            success_probability = 0.4 + 0.5 * (card_value / target_value) if card_value < target_value * 2 else 0.9
        else:
            success_probability = 0.4 * (card_value / target_value)

        success_probability = min(success_probability, 0.9)  # Cap the success probability at 90%

        # Ask for confirmation
        await ctx.send(f'The success probability for upgrading **{character_name}** to **{target_character_name}** is **{success_probability:.2%}**. Do you want to proceed? (yes/no)')

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in ['yes', 'no']

        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() == 'no':
                await ctx.send('Upgrade cancelled.')
                return
        except asyncio.TimeoutError:
            await ctx.send('Upgrade timed out. Please try again.')
            return

        # Create the roulette bar
        total_segments = 20
        success_segments = int(success_probability * total_segments)
        roulette_bar = ["🟥"] * total_segments
        for i in range(success_segments):
            roulette_bar[i] = "🟩"

        msg = await ctx.send(f'Attempting to upgrade **{character_name}** to **{target_character_name}**...\nChance: **{success_probability:.2%}**\nUpgrade: {"".join(roulette_bar)}')

        await asyncio.sleep(2)  # Simulate the roulette spinning

        # Animate the cursor over the roulette bar
        cursor = "🔷"
        animation_steps = 10
        for _ in range(animation_steps):
            position = random.randint(0, total_segments - 1)
            current_bar = roulette_bar[:]
            current_bar.insert(position, cursor)
            await msg.edit(content=f'Attempting to upgrade **{character_name}** to **{target_character_name}**...\nChance: **{success_probability:.2%}**\nUpgrade: {"".join(current_bar)}')
            await asyncio.sleep(0.5)

        # Determine the outcome
        if random.random() < success_probability:
            # Successful upgrade
            user_collections[user_id].remove(card)
            card['claimed_by'] = None  # Unclaim the card
            target_card['claimed_by'] = user_id
            user_collections[user_id].append(target_card)
            await msg.edit(content=f'🎉 Success! You upgraded **{character_name}** to **{target_character_name}**!')
        else:
            # Failed upgrade
            user_collections[user_id].remove(card)
            card['claimed_by'] = None  # Unclaim the card
            await msg.edit(content=f'❌ Failed! You lost **{character_name}** and did not gain **{target_character_name}**.')

        save_data(guild_id, cards, user_collections, user_data)

    # Add the same command in app_commands format for slash commands
    @bot.tree.command(name="upgrade", description="Gamble a card for a chance to upgrade to another card")
    @app_commands.describe(character_name="Character name to gamble", target_character_name="Character name to upgrade to")
    async def roulette_app(interaction: discord.Interaction, character_name: str, target_character_name: str):
        """Slash command to gamble a card for a chance to upgrade to another card."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]
        user_id = str(interaction.user.id)
        user_collections = guild_data[guild_id][1]
        user_data = guild_data[guild_id][2]
        initialize_user(guild_id, user_id)

        # Check if the user owns the character they want to gamble
        card = next((c for c in user_collections.get(user_id, []) if c['name'].lower() == character_name.lower()), None)
        if not card:
            await interaction.response.send_message('You do not own this character.', ephemeral=True)
            return

        # Check if the target character is not claimed
        target_card = next((c for c in cards if c['name'].lower() == target_character_name.lower()), None)
        if not target_card:
            await interaction.response.send_message('Target character not found.', ephemeral=True)
            return

        if target_card['claimed_by']:
            await interaction.response.send_message('Target character is already claimed.', ephemeral=True)
            return

        # Calculate the upgrade cost and probability
        card_value = card['value']
        target_value = target_card['value']
        if card_value >= target_value:
            success_probability = 0.4 + 0.5 * (card_value / target_value) if card_value < target_value * 2 else 0.9
        else:
            success_probability = 0.4 * (card_value / target_value)

        success_probability = min(success_probability, 0.9)

        # Ask for confirmation
        await interaction.response.send_message(f'The success probability for upgrading **{character_name}** to **{target_character_name}** is**{success_probability:.2%}**. Do you want to proceed? (yes/no)')

        def check(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel and msg.content.lower() in ['yes', 'no']

        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() == 'no':
                await interaction.followup.send('Upgrade cancelled.', ephemeral=True)
                return
        except asyncio.TimeoutError:
            await interaction.followup.send('Upgrade timed out. Please try again.', ephemeral=True)
            return

        # Create the roulette bar
        total_segments = 20
        success_segments = int(success_probability * total_segments)
        roulette_bar = ["🟥"] * total_segments
        for i in range(success_segments):
            roulette_bar[i] = "🟩"

        msg = await interaction.followup.send(f'Attempting to upgrade **{character_name}** to **{target_character_name}**...\nChance: **{success_probability:.2%}**\nUpgrade: {"".join(roulette_bar)}')

        await asyncio.sleep(2)  # Simulate the roulette spinning

        # Animate the cursor over the roulette bar
        cursor = "🔷"
        animation_steps = 10
        for _ in range(animation_steps):
            position = random.randint(0, total_segments - 1)
            current_bar = roulette_bar[:]
            current_bar.insert(position, cursor)
            await interaction.edit_original_response(content=f'Attempting to upgrade **{character_name}** to **{target_character_name}**...\nChance: **{success_probability:.2%}**\nUpgrade: {"".join(current_bar)}')
            await asyncio.sleep(0.5)

        # Determine the outcome
        if random.random() < success_probability:
            # Successful upgrade
            user_collections[user_id].remove(card)
            card['claimed_by'] = None  # Unclaim the card
            target_card['claimed_by'] = user_id
            user_collections[user_id].append(target_card)
            await interaction.edit_original_response(content=f'🎉 Success! You upgraded **{character_name}** to **{target_character_name}**!')
        else:
            # Failed upgrade
            user_collections[user_id].remove(card)
            card['claimed_by'] = None  # Unclaim the card
            await interaction.edit_original_response(content=f'❌ Failed! You lost **{character_name}** and did not gain **{target_character_name}**.')

        save_data(guild_id, cards, user_collections, user_data)

    
    @bot.command(name="ci")
    async def change_image(ctx, *, args: str):
        """Command to change the first image of the character to the specified image number."""
        try:
            character_name, img_num_str = args.split(" $ ")
            img_num = int(img_num_str.strip())
        except ValueError:
            await ctx.send("Invalid format. Use: !ci <character_name> $ <img_num>")
            return

        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]

        # Find the card by character name
        card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
        if not card:
            await ctx.send('Character not found.')
            return

        # Check if the specified image number is valid
        if img_num < 1 or img_num > len(card['image_urls']):
            await ctx.send(f'Invalid image number. Please choose a number between 1 and {len(card["image_urls"])}.')
            return

        # Swap the images
        card['image_urls'][0], card['image_urls'][img_num - 1] = card['image_urls'][img_num - 1], card['image_urls'][0]
        save_data(guild_id, *guild_data[guild_id])
        await ctx.send(f'Image {img_num} has been set as the first image for {character_name}.')

    # Add the same command in app_commands format for slash commands
    @bot.tree.command(name="ci", description="Change the first image of a character to the specified image number")
    @app_commands.describe(character_name="Character name", img_num="Image number")
    async def change_image_app(interaction: discord.Interaction, character_name: str, img_num: int):
        """Slash command to change the first image of the character to the specified image number."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        cards = guild_data[guild_id][0]

        # Find the card by character name
        card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
        if not card:
            await interaction.response.send_message('Character not found.', ephemeral=True)
            return

        # Check if the specified image number is valid
        if img_num < 1 or img_num > len(card['image_urls']):
            await interaction.response.send_message(f'Invalid image number. Please choose a number between 1 and {len(card["image_urls"])}.', ephemeral=True)
            return

        # Swap the images
        card['image_urls'][0], card['image_urls'][img_num - 1] = card['image_urls'][img_num - 1], card['image_urls'][0]
        save_data(guild_id, *guild_data[guild_id])
        await interaction.response.send_message(f'Image {img_num} has been set as the first image for {character_name}.', ephemeral=True)

    @bot.command(name="wish")
    async def wish(ctx, *, character_name: str):
        """Command to add a character to the user's wish list."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        if 'wishes' not in user_data[user_id]:
            user_data[user_id]['wishes'] = []

        if len(user_data[user_id]['wishes']) >= MAX_WISHES:
            await ctx.send(f"You can only have a maximum of {MAX_WISHES} wishes.")
            return

        card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
        if not card:
            await ctx.send(f"Character {character_name} not found.")
            return

        user_data[user_id]['wishes'].append(card['name'])
        save_data(guild_id, cards, user_collections, user_data)
        await ctx.send(f"Character {character_name} has been added to your wish list!")

    @bot.command(name="wishremove")
    async def wishremove(ctx, *, character_name: str):
        """Command to remove a character from the user's wish list."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        if 'wishes' not in user_data[user_id]:
            await ctx.send("You don't have any wishes.")
            return

        if character_name not in user_data[user_id]['wishes']:
            await ctx.send(f"Character {character_name} is not in your wish list.")
            return

        user_data[user_id]['wishes'].remove(character_name)
        save_data(guild_id, cards, user_collections, user_data)
        await ctx.send(f"Character {character_name} has been removed from your wish list!")

    @bot.command(name="wishlist")
    async def wishlist(ctx, member: discord.Member = None):
        """Command to display the user's wish list."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        if member is None:
            member = ctx.author
        user_id = str(member.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        if 'wishes' not in user_data[user_id]:
            await ctx.send("You don't have any wishes.")
            return
        wishlist = user_data[user_id]['wishes']
        wishlist_display = []
        firstcharacter = None
        for character_name in wishlist:
            card = next((c for c in cards if c['name'].lower() == character_name.lower()), None)
            if firstcharacter == None:
                firstcharacter = card['image_urls'][0]
            if not card:
                continue
            status = ""
            if card['claimed_by'] == user_id:
                status = " ✅"
            elif card['claimed_by']:
                status = " ❌"
            wishlist_display.append(f"**{character_name}** {status}")
    
        if not wishlist_display:
            await ctx.send("Your wish list is empty.")
        else:
            top_list = "\n\n\n"
            top_list += '\n'.join([card for card in wishlist_display[:10]])
            embed = discord.Embed(title="", description=top_list)
            embed.set_author(name=f" • {member.display_name}'s Wishlist", icon_url=member.avatar.url)
            embed.set_thumbnail(url=firstcharacter)
            await ctx.send(embed=embed)
    
    @bot.command(name="daily")
    async def daily(ctx):
        """Command get free coins every day"""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        last_daily_time = datetime.fromisoformat(user_data[user_id].get('last_daily_time', '1970-01-01T00:00:00'))
        if datetime.utcnow() - last_daily_time < timedelta(hours=20):
            remaining_time = timedelta(hours=20) - (datetime.utcnow() - last_daily_time)
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await ctx.send(f"You can use !daily again in **{hours}h {minutes}m**.")
            return

        coins_received = random.randint(100, 400)
        user_data[user_id]['coins'] += coins_received
        user_data[user_id]['last_daily_time'] = datetime.utcnow().isoformat()
        save_data(guild_id, cards, user_collections, user_data)
        await ctx.send(f"You received {coins_received} coins!")

    @bot.command(name="dailyreset")
    async def dailyreset(ctx):
        """Command to reset the claim timer every day"""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_id = str(ctx.author.id)
        cards, user_collections, user_data = guild_data[guild_id]
        initialize_user(guild_id, user_id)

        if 'claims' not in user_data[user_id]:
            user_data[user_id]['claims'] = 1
            
        if user_data[user_id]['claims'] == 1:
            pass
            await ctx.send("Your still have a claim left... You cannot use this command right now")
        else:
            last_daily_reset_time = datetime.fromisoformat(user_data[user_id].get('last_daily_reset_time', '1970-01-01T00:00:00'))
            if datetime.utcnow() - last_daily_reset_time < timedelta(hours=20):
                remaining_time = timedelta(hours=20) - (datetime.utcnow() - last_daily_reset_time)
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(f"You can use !dailyreset again in **{hours}h {minutes}m**.")
                return

            user_data[user_id]['claims'] = 1
            user_data[user_id]['last_daily_reset_time'] = datetime.utcnow().isoformat()
            save_data(guild_id, cards, user_collections, user_data)
            await ctx.send("Your claim has been reset!")

    @bot.command(name="trade")
    async def trade(ctx, user: discord.User, *, args: str):
        """Command to trade cards with another player"""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        user_collections = guild_data[guild_id][1]
        sender = ctx.message.author
        sender_id = str(sender.id)
        receiver_id = str(user.id)

        sender_cards = [name.strip() for name in args.split(" $ ")]

        # Vérifier si l'expéditeur possède toutes les cartes
        for card_name in sender_cards:
            if not any(c for c in user_collections.get(sender_id, []) if c['name'].lower() == card_name.lower()):
                await ctx.send(f'You do not have the card {card_name}.')
                return

        await ctx.send(f'{user.mention}, {sender.display_name} wants to trade {", ".join(sender_cards)}. What card(s) will you trade in return? (Reply with card names separated by $)')

        def check(msg):
            return msg.author == user and msg.channel == ctx.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            receiver_cards = [name.strip() for name in msg.content.split(" $ ")]

            # Vérifier si le récepteur possède toutes les cartes
            for card_name in receiver_cards:
                if not any(c for c in user_collections.get(receiver_id, []) if c['name'].lower() == card_name.lower()):
                    await ctx.send(f'{user.display_name} does not have the card {card_name}.')
                    return

            await ctx.send(f'{sender.mention}, {user.display_name} wants to trade {", ".join(receiver_cards)} for {", ".join(sender_cards)}. Do you accept? (yes/no)')

            def check_confirm(msg):
                return msg.author == sender and msg.channel == ctx.channel and msg.content.lower() in ['yes', 'y', 'no', 'n']

            try:
                confirm_msg = await bot.wait_for('message', check=check_confirm, timeout=60)
                if confirm_msg.content.lower() in ['yes', 'y']:
                    for card_name in sender_cards:
                        sender_card = next(c for c in user_collections[sender_id] if c['name'].lower() == card_name.lower())
                        user_collections[sender_id].remove(sender_card)
                        sender_card['claimed_by'] = receiver_id
                        user_collections[receiver_id].append(sender_card)

                    for card_name in receiver_cards:
                        receiver_card = next(c for c in user_collections[receiver_id] if c['name'].lower() == card_name.lower())
                        user_collections[receiver_id].remove(receiver_card)
                        receiver_card['claimed_by'] = sender_id
                        user_collections[sender_id].append(receiver_card)
                    

                    save_data(guild_id, *guild_data[guild_id])
                    await ctx.send(f'Trade successful! {sender.display_name} traded {", ".join(sender_cards)} with {user.display_name} for {", ".join(receiver_cards)}.')
                else:
                    await ctx.send('Trade cancelled.')
            except asyncio.TimeoutError:
                await ctx.send('Trade confirmation timed out.')

        except asyncio.TimeoutError:
            await ctx.send('Trade response timed out.')

    @bot.tree.command(name="trade", description="Trade cards with another user")
    @app_commands.describe(user="The user to trade with", cards="The cards you want to trade, separated by $")
    async def trade_app(interaction: discord.Interaction, user: discord.User, cards: str):
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        user_collections = guild_data[guild_id][1]
        sender = interaction.user
        sender_id = str(sender.id)
        receiver_id = str(user.id)

        sender_cards = [name.strip() for name in cards.split(" $ ")]

        # Vérifier si l'expéditeur possède toutes les cartes
        for card_name in sender_cards:
            if not any(c for c in user_collections.get(sender_id, []) if c['name'].lower() == card_name.lower()):
                await interaction.response.send_message(f'You do not have the card {card_name}.', ephemeral=True)
                return

        await interaction.response.send_message(f'{user.mention}, {sender.display_name} wants to trade {", ".join(sender_cards)}. What card(s) will you trade in return? (Reply with card names separated by $)', ephemeral=True)

        def check(msg):
            return msg.author == user and msg.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            receiver_cards = [name.strip() for name in msg.content.split(" $ ")]

            # Vérifier si le récepteur possède toutes les cartes
            for card_name in receiver_cards:
                if not any(c for c in user_collections.get(receiver_id, []) if c['name'].lower() == card_name.lower()):
                    await interaction.channel.send(f'{user.display_name} does not have the card {card_name}.')
                    return

            await interaction.channel.send(f'{sender.mention}, {user.display_name} wants to trade {", ".join(receiver_cards)} for {", ".join(sender_cards)}. Do you accept? (yes/no)')

            def check_confirm(msg):
                return msg.author == sender and msg.channel == interaction.channel and msg.content.lower() in ['yes', 'y', 'no', 'n']

            try:
                confirm_msg = await bot.wait_for('message', check=check_confirm, timeout=60)
                if confirm_msg.content.lower() in ['yes', 'y']:
                    for card_name in sender_cards:
                        sender_card = next(c for c in user_collections[sender_id] if c['name'].lower() == card_name.lower())
                        user_collections[sender_id].remove(sender_card)
                        sender_card['claimed_by'] = receiver_id
                        user_collections[receiver_id].append(sender_card)

                    for card_name in receiver_cards:
                        receiver_card = next(c for c in user_collections[receiver_id] if c['name'].lower() == card_name.lower())
                        user_collections[receiver_id].remove(receiver_card)
                        receiver_card['claimed_by'] = sender_id
                        user_collections[sender_id].append(receiver_card)
                        
                    save_data(guild_id, *guild_data[guild_id])
                    await interaction.channel.send(f'Trade successful! {sender.display_name} traded {", ".join(sender_cards)} with {user.display_name} for {", ".join(receiver_cards)}.')
                else:
                    await interaction.channel.send('Trade cancelled.')
            except asyncio.TimeoutError:
                await interaction.channel.send('Trade confirmation timed out.')

        except asyncio.TimeoutError:
            await interaction.channel.send('Trade response timed out.')



    @bot.command(name="download_data")
    @is_admin()
    async def download_data(ctx):
        """Command to download the JSON files."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        await ctx.send(file=discord.File(f'data/{guild_id}_cards.json'))
        await ctx.send(file=discord.File(f'data/{guild_id}_collections.json'))
        await ctx.send(file=discord.File(f'data/{guild_id}_user_data.json'))

    @bot.tree.command(name="download_data", description="Download the current data as JSON files")
    @is_admin()
    async def download_data_app(interaction: discord.Interaction):
        """Slash command to download the JSON files."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        await interaction.response.send_message("Downloading data...", ephemeral=True)
        await interaction.followup.send(file=discord.File(f'data/{guild_id}_cards.json'))
        await interaction.followup.send(file=discord.File(f'data/{guild_id}_collections.json'))
        await interaction.followup.send(file=discord.File(f'data/{guild_id}_user_data.json'))

    @bot.command(name="upload_data")
    @is_admin()
    async def upload_data(ctx, cards_file: discord.Attachment, collections_file: discord.Attachment, user_data_file: discord.Attachment):
        """Command to upload the JSON files."""
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        await cards_file.save(f'data/{guild_id}_cards.json')
        await collections_file.save(f'data/{guild_id}_collections.json')
        await user_data_file.save(f'data/{guild_id}_user_data.json')
        
        # Reload the data
        global guild_data
        guild_data[guild_id] = load_data(guild_id)
        
        # Debug print statements to verify data loading
        print(f'Loaded {len(guild_data[guild_id][0])} cards')
        print(f'Loaded {len(guild_data[guild_id][1])} user collections')
        print(f'Loaded {len(guild_data[guild_id][2])} user data entries')

        await ctx.send("Data uploaded and loaded successfully!")
        
        # Restart the bot to apply the new data
        reload_bot()

    @bot.tree.command(name="upload_data", description="Upload the current data as JSON files")
    @is_admin()
    @app_commands.describe(cards_file="The cards JSON file", collections_file="The collections JSON file", user_data_file="The user data JSON file")
    async def upload_data_app(interaction: discord.Interaction, cards_file: discord.Attachment, collections_file: discord.Attachment, user_data_file: discord.Attachment):
        """Slash command to upload the JSON files."""
        guild_id = str(interaction.guild.id)
        initialize_guild(guild_id)
        await cards_file.save(f'data/{guild_id}_cards.json')
        await collections_file.save(f'data/{guild_id}_collections.json')
        await user_data_file.save(f'data/{guild_id}_user_data.json')
        
        # Reload the data
        global guild_data
        guild_data[guild_id] = load_data(guild_id)
        
        # Debug print statements to verify data loading
        print(f'Loaded {len(guild_data[guild_id][0])} cards')
        print(f'Loaded {len(guild_data[guild_id][1])} user collections')
        print(f'Loaded {len(guild_data[guild_id][2])} user data entries')

        await interaction.response.send_message("Data uploaded and loaded successfully!", ephemeral=True)
        reload_bot()
    
    @bot.command(name='start_quiz')
    async def start_quiz(ctx):
        guild = ctx.guild
        existing_channel = discord.utils.get(guild.voice_channels, name='Quizz')
        if not existing_channel:
            channel = await guild.create_voice_channel('Quizz')
        else:
            channel = existing_channel

        await ctx.send(f'Quiz starting in {channel.mention}. Join the voice channel to participate!')

        # Move bot to the voice channel
        voice_channel = discord.utils.get(ctx.guild.voice_channels, name='Quizz')
        if voice_channel:
            vc = ctx.voice_client
            if vc:
                if vc.channel != voice_channel:
                    await vc.move_to(voice_channel)
            else:
                vc = await voice_channel.connect()

            await play_quiz(vc, ctx)
        else:
            await ctx.send("Couldn't create/find a voice channel named 'Quizz'.")

    async def play_quiz(vc, ctx):
        while True:
            anime, youtube_url = random.choice(list(quiz_data.items()))

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'audio.%(ext)s',
                'quiet': True
            }

            audio_file = None
            while not audio_file:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(youtube_url, download=True)
                        audio_file = ydl.prepare_filename(info_dict).replace('.webm', '.mp3').replace('.m4a', '.mp3')
                except Exception as e:
                    await ctx.send(f"Error downloading audio from YouTube: {e}")
                    anime, youtube_url = random.choice(list(quiz_data.items()))

            await ctx.send(f'Playing an opening, guess the anime!')

            def check(m):
                return m.channel == ctx.channel and m.author.voice and m.author.voice.channel == vc.channel

            vc.play(discord.FFmpegPCMAudio(audio_file), after=lambda e: print('done', e))

            try:
                correct = False
                start_time = asyncio.get_event_loop().time()
                while vc.is_playing():
                    try:
                        msg = await bot.wait_for('message', check=check, timeout=1)
                        matched_anime, score = process.extractOne(msg.content, quiz_data.keys(), scorer=fuzz.ratio)
                        if score >= 70 and matched_anime == anime:
                            user = msg.author
                            if user not in scores:
                                scores[user] = 0
                            scores[user] += 1
                            await ctx.send(f'{user.name} guessed it right! The correct answer was {matched_anime}. They now have **{scores[user]}** points.')
                            vc.stop()
                            correct = True
                            break
                        elif msg.content.lower() == 'skip':
                            vc.stop()
                            correct = True
                            await ctx.send(f'Music skipped because the song is unknown, it was: {anime}')
                            break
                        elif msg.content.lower() == 'end':
                            fastend = True
                            vc.stop()
                            correct = True
                            break
                    except asyncio.TimeoutError:
                        pass

                if not correct:
                    await asyncio.sleep(max(0, 30 - (asyncio.get_event_loop().time() - start_time)))
                    await ctx.send(f'Music skipped because no one found it, it was: {anime}')
                        
            except Exception as e:
                print(f"Error playing audio: {e}")
                await ctx.send(f"Error playing audio: {e}")

            os.remove(audio_file)

            if any(score >= 10 for score in scores.values()) or fastend == True:
                if fastend == True:
                    scores.clear()
                    fastend = False
                    await ctx.send(f'Game ended because of !end.')
                    break
                else: 
                    winner = max(scores, key=scores.get)
                    await ctx.send(f'**{winner.name}** has won the quiz with **{scores[winner]}** points!')
                    scores.clear()
                    break

        await vc.disconnect()

    @bot.command()
    async def upload(ctx):
        if not ctx.message.attachments:
            await ctx.send("Please attach an image.")
            return

        attachment = ctx.message.attachments[0]
        image_data = await attachment.read()
        
        # Resize the image
        with Image.open(io.BytesIO(image_data)) as img:
            img = img.resize((225, 350))
            img = img.convert("RGB")
            # Save the image to a bytes buffer
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)

        # Upload the image to imgchest.com
        upload_url = "https://api.imgchest.com/v1/post"
        files = {'images[]': ('image.jpg', buffer, 'image/jpeg')}
        data = {'title': 'Napo Discord Bot', 'privacy': 'hidden'}
        headers = {'Authorization': 'Bearer SpEMZxXfd0VCVLPTyLbslGGGls3Ahei5a2RQcZqZ3263746c'}
        
        response = requests.post(upload_url, headers=headers, data=data, files=files)

        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content.decode('utf-8')}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                image_url = response_data['data']['images'][0]['link']
                await ctx.send(f"Image uploaded: {image_url}")
            except requests.exceptions.JSONDecodeError:
                await ctx.send("Failed to parse JSON response from the server.")
                print(f"Response content: {response.content}")
        else:
            await ctx.send("Failed to upload image.")
            
    async def upload_image(image_data):
        with Image.open(io.BytesIO(image_data)) as img:
            img = img.resize((225, 350))
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
        
        upload_url = "https://api.imgchest.com/v1/post"
        files = {'images[]': ('image.jpg', buffer, 'image/jpeg')}
        data = {'title': 'Napo Discord Bot', 'privacy': 'hidden'}
        headers = {'Authorization': 'Bearer SpEMZxXfd0VCVLPTyLbslGGGls3Ahei5a2RQcZqZ3263746c'}
        
        response = requests.post(upload_url, headers=headers, data=data, files=files)
        if response.status_code == 200:
            response_data = response.json()
            return response_data['data']['images'][0]['link']
        else:
            print(f"Failed to upload image. HTTP Status Code: {response.status_code}")
            print(f"Response content: {response.content.decode('utf-8')}")
            return None
        
    @is_admin()
    @bot.command()
    async def init_server(ctx):
        guild_id = str(ctx.guild.id)
        initialize_guild(guild_id)
        cards, user_collections, user_data = guild_data[guild_id]
        
        async with aiohttp.ClientSession() as session:
            for member in ctx.guild.members:
                if member.bot:
                    continue
                user_id = str(member.id)
                nickname = member.display_name
                profile_picture = member.avatar.url if member.avatar else member.default_avatar.url

                if ctx.guild.owner_id == member.id:
                    rank = 'SS'
                elif any(role.permissions.administrator for role in member.roles):
                    rank = 'S'
                elif any(role.name.lower() == 'la squad' for role in member.roles):
                    rank = 'A'
                else:
                    rank = random.choice(['B', 'C', 'D', 'E'])
                
                rank_description = rank
                price = {'SS': 1200, 'S': 1000, 'A': 800, 'B': 600, 'C': 350, 'D': 150, 'E': 40}[rank]

                # Fetch profile picture
                async with session.get(profile_picture) as resp:
                    if resp.status != 200:
                        await ctx.send(f"Failed to fetch profile picture for {nickname}.")
                        continue
                    image_data = await resp.read()
                img_url = []
                img = await upload_image(image_data)
                if not img:
                    await ctx.send(f"Failed to upload image for {nickname}.")
                    continue
                
                img_url.append(img)
                
                card = {
                    'name': nickname,
                    'value': price,
                    'rank': rank,
                    'description': rank_description,
                    'image_urls': img_url,
                    'claimed_by': None
                }
                cards.append(card)
        
        save_data(guild_id, cards, user_collections, user_data)
        await ctx.send("Server initialized successfully with member cards.")
