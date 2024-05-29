import discord
from utils import save_data
import asyncio

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
            remaining_time = timedelta(hours=3) - (datetime.utcnow() - last_claim_time)
            await interaction.response.send_message(f"You can only claim once every 3 hours. Please wait **{remaining_time}**.", ephemeral=True)
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
            embed = discord.Embed(title=self.card['name'], description=self.card['description'], color=discord.Color.red())
            embed.add_field(name="Rank", value=self.card['rank'])
            embed.add_field(name="Value", value=f"{self.card['value']} 💎")
            embed.add_field(name="Claimed", value=f"Claimed by <@{user_id}>")
            embed.set_image(url=self.card['image_url'])
            await interaction.message.edit(embed=embed, view=None)

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
            remaining_time = timedelta(hours=3) - (datetime.utcnow() - last_gem_time)
            await interaction.response.send_message(f"You can only collect gems once every 3 hours. Please wait **{remaining_time}**.", ephemeral=True)
            return

        self.user_data[user_id]['last_gem_time'] = str(datetime.utcnow())
        self.user_data.setdefault(user_id, {}).setdefault('coins', 0)
        self.user_data[user_id]['coins'] += self.card['value']

        save_data(cards, user_collections, user_data)
        await interaction.response.send_message(f"You received {self.card['value']} coins from the gem!", ephemeral=True)

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
        embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)}')
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
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

class GlobalPaginator(discord.ui.View):
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
        embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)}')
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
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
