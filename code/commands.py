import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from utils import save_data, rank_sort_key
from views import ClaimButton, GemButton, Paginator, GlobalPaginator

def setup_commands(bot, cards, user_collections, user_data):

    @bot.tree.command(name="add_character", description="Add a new character card")
    @app_commands.describe(name="Name of the character", value="Value of the character", rank="Rank of the character", description="Description of the character", image_url="Image URL of the character")
    async def add_character(interaction: discord.Interaction, name: str, value: int, rank: str, description: str, image_url: str):
        """Command to add a new card."""
        card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_url': image_url, 'claimed_by': None}
        cards.append(card)
        save_data(cards, user_collections, user_data)
        await interaction.response.send_message(f'Character {name} added successfully!', ephemeral=True)

    @bot.command(name="add_character")
    async def add_character_cmd(ctx, name: str, value: int, rank: str, description: str, image_url: str):
        """Command to add a new card."""
        card = {'name': name, 'value': value, 'rank': rank, 'description': description, 'image_url': image_url, 'claimed_by': None}
        cards.append(card)
        save_data(cards, user_collections, user_data)
        await ctx.send(f'Character {name} added successfully!')

    
    @bot.command(name="roll")
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
            view.add_item(ClaimButton(card, user_data, user_collections, cards))

        message = await ctx.send(embed=embed, view=view)
        await asyncio.sleep(45)
        await message.edit(content="Time to claim the character has expired.", view=None)

    @bot.tree.command(name="roll", description="Roll a random character card")
    async def roll_app(interaction: discord.Interaction):
        """Command to roll a random card."""
        if not cards:
            await interaction.response.send_message('No cards available. Please add cards first.', ephemeral=True)
            return

        card = random.choice(cards)
        user_id = str(interaction.user.id)

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
            view.add_item(ClaimButton(card, user_data, user_collections, cards))

        message = await interaction.response.send_message(embed=embed, view=view)
        await asyncio.sleep(45)
        await message.edit(content="Time to claim the character has expired.", view=None)

    @bot.command(name="balance")
    async def balance(ctx):
        user_id = str(ctx.author.id)
        coins = user_data.get(user_id, {}).get('coins', 0)
        await ctx.send(f"You have {coins} coins.")

    @bot.tree.command(name="balance", description="Check your coin balance")
    async def balance_app(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        coins = user_data.get(user_id, {}).get('coins', 0)
        await interaction.response.send_message(f"You have {coins} coins.", ephemeral=True)

    @bot.command(name="buyluck")
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

    @bot.tree.command(name="buyluck", description="Buy more luck for 500 coins")
    async def buyluck_app(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        coins = user_data.get(user_id, {}).get('coins', 0)
        if coins < 500:
            await interaction.response.send_message("You need at least 500 coins to buy more luck.", ephemeral=True)
            return

        user_data[user_id]['coins'] -= 500
        user_data[user_id].setdefault('luck', 0)
        user_data[user_id]['luck'] += 1
        save_data(cards, user_collections, user_data)
        await interaction.response.send_message("You have purchased more luck for 500 coins!", ephemeral=True)

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

        paginator = Paginator(ctx, collection, user_data)
        await paginator.send_initial_message()

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

        paginator = Paginator(interaction, collection, user_data)
        await paginator.send_initial_message()

    @bot.command(name="mm")
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
        embed = discord.Embed(title=f'Your collection (Page {page}/{total_pages})', description=collection_list)
        await ctx.send(embed=embed)

    @bot.tree.command(name="mm", description="Display your collection in text")
    @app_commands.describe(page="Page number to display")
    async def mm_app(interaction: discord.Interaction, page: int = 1):
        user_id = str(interaction.user.id)
        if str(user_id) not in user_collections or not user_collections[str(user_id)]:
            await interaction.response.send_message('You have no cards in your collection.', ephemeral=True)
            return

        collection = user_collections[str(user_id)]
        items_per_page = 10
        total_pages = (len(collection) + items_per_page - 1) // items_per_page

        if page < 1 or page > total_pages:
            await interaction.response.send_message(f'Page {page} is out of range. There are {total_pages} pages in total.', ephemeral=True)
            return

        start = (page - 1) * items_per_page
        end = start + items_per_page
        collection_page = collection[start:end]
        collection_list = '\n'.join([f'**{card["name"]}** ({card["rank"]}) - {card["description"]} (Value: {card["value"]} 💎)' for card in collection_page])
        embed = discord.Embed(title=f'Your collection (Page {page}/{total_pages})', description=collection_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="top")
    async def top(ctx, page: int = 1):
        """Command to display the top characters globally in text."""
        if not cards:
            await ctx.send('No cards available.')
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        items_per_page = 10
        total_pages = (len(sorted_cards) + items_per_page - 1) // items_per_page

        if page < 1 or page > total_pages:
            await ctx.send(f'Page {page} is out of range. There are {total_pages} pages in total.')
            return

        start = (page - 1) * items_per_page
        end = start + items_per_page
        top_page = sorted_cards[start:end]
        top_list = '\n'.join([f'**{card["name"]}** ({card["rank"]}) - {card["description"]} (Value: {card["value"]} 💎)' for card in top_page])
        embed = discord.Embed(title=f'Top characters globally (Page {page}/{total_pages})', description=top_list)
        await ctx.send(embed=embed)

    @bot.tree.command(name="top", description="Display the top characters globally in text")
    @app_commands.describe(page="Page number to display")
    async def top_app(interaction: discord.Interaction, page: int = 1):
        if not cards:
            await interaction.response.send_message('No cards available.', ephemeral=True)
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        items_per_page = 10
        total_pages = (len(sorted_cards) + items_per_page - 1) // items_per_page

        if page < 1 or page > total_pages:
            await interaction.response.send_message(f'Page {page} is out of range. There are {total_pages} pages in total.', ephemeral=True)
            return

        start = (page - 1) * items_per_page
        end = start + items_per_page
        top_page = sorted_cards[start:end]
        top_list = '\n'.join([f'**{card["name"]}** ({card["rank"]}) - {card["description"]} (Value: {card["value"]} 💎)' for card in top_page])
        embed = discord.Embed(title=f'Top characters globally (Page {page}/{total_pages})', description=top_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="topi")
    async def topi(ctx):
        """Command to display the top characters globally with images."""
        if not cards:
            await ctx.send('No cards available.')
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        paginator = GlobalPaginator(ctx, sorted_cards, user_data)
        await paginator.send_initial_message()

    @bot.tree.command(name="topi", description="Display the top characters globally with images")
    async def topi_app(interaction: discord.Interaction):
        if not cards:
            await interaction.response.send_message('No cards available.', ephemeral=True)
            return

        sorted_cards = sorted(cards, key=rank_sort_key)
        paginator = GlobalPaginator(interaction, sorted_cards, user_data)
        await paginator.send_initial_message()

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
        embed.add_field(name="Value", value=f'{card["value"]} 💎')
        embed.add_field(name="Claimed", value=claimed_status)
        embed.set_image(url=card["image_url"])
        await ctx.send(embed=embed)

    @bot.tree.command(name="im", description="Display detailed information about a card")
    @app_commands.describe(name="Name of the card")
    async def im_app(interaction: discord.Interaction, name: str):
        card = next((c for c in cards if c['name'].lower() == name.lower()), None)
        if not card:
            await interaction.response.send_message('Card not found.', ephemeral=True)
            return

        claimed_status = "Not claimed" if not card["claimed_by"] else f'Claimed by <@{card["claimed_by"]}>'
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name="Rank", value=card["rank"])
        embed.add_field(name="Value", value=f'{card["value"]} 💎')
        embed.add_field(name="Claimed", value=claimed_status)
        embed.set_image(url=card["image_url"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.command(name="trade")
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

    @bot.tree.command(name="trade", description="Trade cards with another user")
    @app_commands.describe(user="User to trade with", card_name="Name of the card you are trading", trade_card_name="Name of the card you want in exchange")
    async def trade_app(interaction: discord.Interaction, user: discord.User, card_name: str, trade_card_name: str):
        sender = interaction.user

        if str(sender.id) not in user_collections or not user_collections[str(sender.id)]:
            await interaction.response.send_message('You have no cards to trade.', ephemeral=True)
            return

        sender_card = next((c for c in user_collections[str(sender.id)] if c['name'].lower() == card_name.lower()), None)
        receiver_card = next((c for c in user_collections[str(user.id)] if c['name'].lower() == trade_card_name.lower()), None)

        if not sender_card:
            await interaction.response.send_message(f'You do not have the card {card_name}.', ephemeral=True)
            return

        if not receiver_card:
            await interaction.response.send_message(f'{user.display_name} does not have the card {trade_card_name}.', ephemeral=True)
            return

        # Perform the trade
        user_collections[str(sender.id)].remove(sender_card)
        user_collections[str(user.id)].remove(receiver_card)
        user_collections[str(sender.id)].append(receiver_card)
        user_collections[str(user.id)].append(sender_card)

        sender_card['claimed_by'] = user.id
        receiver_card['claimed_by'] = sender.id

        save_data(cards, user_collections, user_data)
        await interaction.response.send_message(f'Trade successful! {sender.display_name} traded {card_name} with {user.display_name} for {trade_card_name}.', ephemeral=True)

    @bot.command(name="divorce")
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

    @bot.tree.command(name="divorce", description="Divorce a character and receive their value")
    @app_commands.describe(name="Name of the card to divorce")
    async def divorce_app(interaction: discord.Interaction, name: str):
        user_id = str(interaction.user.id)
        if str(user_id) not in user_collections or not user_collections[str(user_id)]:
            await interaction.response.send_message('You have no cards in your collection.', ephemeral=True)
            return

        card = next((c for c in user_collections[str(user_id)] if c['name'].lower() == name.lower()), None)
        if not card:
            await interaction.response.send_message(f'You do not have the card {name}.', ephemeral=True)
            return

        user_collections[str(user_id)].remove(card)
        user_data[str(user_id)]['coins'] = user_data.get(str(user_id), {}).get('coins', 0) + card['value']
        card['claimed_by'] = None

        save_data(cards, user_collections, user_data)
        await interaction.response.send_message(f'You have divorced {name} and received {card["value"]} coins.', ephemeral=True)

