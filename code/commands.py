import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from utils import save_data, load_data, rank_sort_key
from views import ClaimButton, GemButton, Paginator, GlobalPaginator, ImagePaginator
import os
import sys
from config import guild_data

# Define global variables for tracking rolls
roll_cooldowns = {}
max_rolls_per_hour = 5
claim_cooldowns = {}
max_claims_per_3_hours = 1

# Define probability distribution
base_probabilities = {
    'SS': 0.005,
    'S': 0.05,
    'A': 0.1,
    'B': 0.2,
    'C': 0.185,
    'D': 0.21,
    'E': 0.25
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
                'luck': {'SS': 0.005, 'S': 0.05, 'A': 0.1, 'B': 0.2, 'C': 0.185, 'D': 0.21, 'E': 0.25},
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
        claimed_by = f"appartien à personne" if not card['claimed_by'] else f"appartien à <@{card['claimed_by']}>"
        embed.add_field(name=f"{card['value']} 💎- {card['rank']} ", value=claimed_by)
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

        save_data(guild_id, cards, user_collections, user_data)

        @bot.command(name="mm")
        async def mm(ctx):
            """Command to display the user's collection."""
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            user_id = str(ctx.author.id)
            user_collections = guild_data[guild_id][1]
            if user_id not in user_collections or not user_collections[user_id]:
                await ctx.send('You have no cards in your collection.')
                return

            collection = user_collections[user_id]
            collection_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']})" for card in collection[:10]])
            embed = discord.Embed(title="Your Collection", description=collection_list)
            await ctx.send(embed=embed)

        @bot.tree.command(name="mm", description="Display your card collection")
        async def mm_app(interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)
            initialize_guild(guild_id)
            user_id = str(interaction.user.id)
            user_collections = guild_data[guild_id][1]
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
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            cards = guild_data[guild_id][0]
            if not cards:
                await ctx.send('No cards available.')
                return

            sorted_cards = sorted(cards, key=rank_sort_key)
            top_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']}){' ❤️' if card['claimed_by'] else ''}" for card in sorted_cards[:10]])
            embed = discord.Embed(title="Top Characters", description=top_list)
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
            top_list = '\n'.join([f"**{card['name']}** ({card['rank']}) - {card['description']} (Value: {card['value']}){' ❤️' if card['claimed_by'] else ''}" for card in sorted_cards[:10]])
            embed = discord.Embed(title="Top Characters", description=top_list)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @bot.command(name="mmi")
        async def mmi(ctx):
            """Command to display the user's collection with images."""
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            user_id = str(ctx.author.id)
            user_collections = guild_data[guild_id][1]
            if user_id not in user_collections or not user_collections[user_id]:
                await ctx.send('You have no cards in your collection.')
                return

            collection = [card for card in user_collections[user_id] if card['claimed_by'] == user_id]
            if not collection:
                await ctx.send('You have no claimed cards in your collection.')
                return

            paginator = Paginator(collection)
            await paginator.send_initial_message(ctx)

        @bot.tree.command(name="mmi", description="Display your claimed cards with images")
        async def mmi_app(interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)
            initialize_guild(guild_id)
            user_id = str(interaction.user.id)
            user_collections = guild_data[guild_id][1]
            if user_id not in user_collections or not user_collections[user_id]:
                await interaction.response.send_message('You have no cards in your collection.', ephemeral=True)
                return

            collection = [card for card in user_collections[user_id] if card['claimed_by'] == user_id]
            if not collection:
                await interaction.response.send_message('You have no claimed cards in your collection.', ephemeral=True)
                return

            paginator = Paginator(collection)
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
            paginator = GlobalPaginator(sorted_cards)
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
            paginator = GlobalPaginator(sorted_cards)
            await paginator.send_initial_message(interaction)

        @bot.command(name="im")
        async def im(ctx, name: str):
            """Command to display detailed information about a card with image navigation."""
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            cards = guild_data[guild_id][0]
            card = next((c for c in cards if c['name'].lower() == name.lower()), None)
            if not card:
                await ctx.send('Card not found.')
                return

            paginator = ImagePaginator(card)
            await paginator.send_initial_message(ctx)

        @bot.tree.command(name="im", description="Display detailed information about a card with image navigation")
        @app_commands.describe(name="Character name")
        async def im_app(interaction: discord.Interaction, name: str):
            guild_id = str(interaction.guild.id)
            initialize_guild(guild_id)
            cards = guild_data[guild_id][0]
            card = next((c for c in cards if c['name'].lower() == name.lower()), None)
            if not card:
                await interaction.response.send_message('Card not found.', ephemeral=True)
                return

            paginator = ImagePaginator(card)
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
        async def luck(ctx):
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            user_id = str(ctx.author.id)
            cards, user_collections, user_data = guild_data[guild_id]
            initialize_user(guild_id, user_id)

            probabilities = get_user_probabilities(guild_id, user_id)
            embed = discord.Embed(title="Your Luck Percentages")
            for rank, chance in probabilities.items():
                embed.add_field(name=rank, value=f"{chance:.2%}")
            await ctx.send(embed=embed)

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
            if luck_purchases >= 5:
                cost = 500 * (2 ** 5) + 2000 * (luck_purchases - 5)

            if coins < cost:
                await ctx.send(f"You don't have enough coins to buy luck. You need {cost} coins.")
                return

            user_info['coins'] -= cost
            user_info['luck_purchases'] += 1

            for rank in user_info['luck']:
                user_info['luck'][rank] += 0.01

            save_data(guild_id, cards, user_collections, user_data)
            next_cost = 500 * (2 ** user_info['luck_purchases']) if user_info['luck_purchases'] < 6 else 500 * (2 ** 5) + 2000 * (user_info['luck_purchases'] + 1 - 5)
            await ctx.send(f"Your luck percentages have been increased! The next upgrade will cost {next_cost} coins.")

        @bot.command(name="daily")
        async def daily(ctx):
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            user_id = str(ctx.author.id)
            cards, user_collections, user_data = guild_data[guild_id]
            initialize_user(guild_id, user_id)

            last_daily_time = datetime.fromisoformat(user_data[user_id].get('last_daily_time', '1970-01-01T00:00:00'))
            if datetime.utcnow() - last_daily_time < timedelta(hours=20):
                remaining_time = timedelta(hours=20) - (datetime.utcnow() - last_daily_time)
                await ctx.send(f"You can use !daily again in {remaining_time}.")
                return

            coins_received = random.randint(100, 400)
            user_data[user_id]['coins'] += coins_received
            user_data[user_id]['last_daily_time'] = datetime.utcnow().isoformat()
            save_data(guild_id, cards, user_collections, user_data)
            await ctx.send(f"You received {coins_received} coins!")

        @bot.command(name="dailyreset")
        async def dailyreset(ctx):
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            user_id = str(ctx.author.id)
            cards, user_collections, user_data = guild_data[guild_id]
            initialize_user(guild_id, user_id)

            last_daily_reset_time = datetime.fromisoformat(user_data[user_id].get('last_daily_reset_time', '1970-01-01T00:00:00'))
            if datetime.utcnow() - last_daily_reset_time < timedelta(hours=20):
                remaining_time = timedelta(hours=20) - (datetime.utcnow() - last_daily_reset_time)
                await ctx.send(f"You can use !dailyreset again in {remaining_time}.")
                return

            user_data[user_id]['last_claim_time'] = (datetime.utcnow() - timedelta(hours=3)).isoformat()
            user_data[user_id]['last_daily_reset_time'] = datetime.utcnow().isoformat()
            save_data(guild_id, cards, user_collections, user_data)
            await ctx.send("Your claim has been reset!")

        @bot.command(name="trade")
        async def trade(ctx, user: discord.User, card_name: str):
            guild_id = str(ctx.guild.id)
            initialize_guild(guild_id)
            user_collections = guild_data[guild_id][1]
            sender = ctx.message.author
            sender_id = str(sender.id)
            receiver_id = str(user.id)

            sender_card = next((c for c in user_collections.get(sender_id, []) if c['name'].lower() == card_name.lower()), None)

            if not sender_card:
                await ctx.send(f'You do not have the card {card_name}.')
                return

            await ctx.send(f'{user.mention}, {sender.display_name} wants to trade {card_name}. What card will you trade in return?')

            def check(msg):
                return msg.author == user and msg.channel == ctx.channel

            try:
                msg = await bot.wait_for('message', check=check, timeout=30)
                receiver_card_name = msg.content
                receiver_card = next((c for c in user_collections.get(receiver_id, []) if c['name'].lower() == receiver_card_name.lower()), None)

                if not receiver_card:
                    await ctx.send(f'{user.display_name} does not have the card {receiver_card_name}.')
                    return

                await ctx.send(f'{sender.mention}, {user.display_name} wants to trade {receiver_card_name} for {card_name}. Do you accept? (yes/no)')

                def check_confirm(msg):
                    return msg.author == sender and msg.channel == ctx.channel and msg.content.lower() in ['yes', 'y', 'no', 'n']

                try:
                    confirm_msg = await bot.wait_for('message', check=check_confirm, timeout=30)
                    if confirm_msg.content.lower() in ['yes', 'y']:
                        user_collections[sender_id].remove(sender_card)
                        user_collections[receiver_id].remove(receiver_card)
                        user_collections[sender_id].append(receiver_card)
                        user_collections[receiver_id].append(sender_card)

                        sender_card['claimed_by'] = receiver_id
                        receiver_card['claimed_by'] = sender_id

                        save_data(guild_id, *guild_data[guild_id])
                        await ctx.send(f'Trade successful! {sender.display_name} traded {card_name} with {user.display_name} for {receiver_card_name}.')
                    else:
                        await ctx.send('Trade cancelled.')
                except asyncio.TimeoutError:
                    await ctx.send('Trade confirmation timed out.')

            except asyncio.TimeoutError:
                await ctx.send('Trade response timed out.')

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
