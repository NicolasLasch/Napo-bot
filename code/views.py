import discord
from datetime import datetime, timedelta
from discord.ext import commands
from utils import save_data

class ClaimButton(discord.ui.Button):
    def __init__(self, card, user_data, user_collections, cards):
        super().__init__(label="Claim", style=discord.ButtonStyle.success)
        self.card = card
        self.user_data = user_data
        self.user_collections = user_collections
        self.cards = cards

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.utcnow()
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {'coins': 0, 'luck_purchases': 0, 'last_claim_time': None}

        last_claim_time = self.user_data[user_id].get('last_claim_time')
        if last_claim_time and now - last_claim_time < timedelta(hours=3):
            remaining_time = timedelta(hours=3) - (now - last_claim_time)
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(f"You can only claim once every 3 hours. Please wait **{hours}h {minutes}m**.", ephemeral=True)
            return

        self.card['claimed_by'] = user_id
        if user_id not in self.user_collections:
            self.user_collections[user_id] = []
        self.user_collections[user_id].append(self.card)
        self.user_data[user_id]['last_claim_time'] = now
        
        save_data(self.cards, self.user_collections, self.user_data)
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_field_at(index=2, name="Claimed", value=f"Claimed: <@{user_id}>")
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.followup.send(f"You have claimed {self.card['name']}!", ephemeral=True)

class GemButton(discord.ui.Button):
    def __init__(self, card, user_data, user_collections, cards):
        super().__init__(label="Claim Gems", style=discord.ButtonStyle.primary)
        self.card = card
        self.user_data = user_data
        self.user_collections = user_collections
        self.cards = cards

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.utcnow()
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {'coins': 0, 'luck_purchases': 0, 'last_claim_time': None, 'last_gem_claim_time': None}

        last_gem_claim_time = self.user_data[user_id].get('last_gem_claim_time')
        if last_gem_claim_time and now - last_gem_claim_time < timedelta(hours=3):
            remaining_time = timedelta(hours=3) - (now - last_gem_claim_time)
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(f"You can only claim gems once every 3 hours. Please wait **{hours}h {minutes}m**.", ephemeral=True)
            return

        self.user_data[user_id]['coins'] += self.card['value']
        self.user_data[user_id]['last_gem_claim_time'] = now

        save_data(self.cards, self.user_collections, self.user_data)
        
        await interaction.response.send_message(f"You have claimed {self.card['value']} gems!", ephemeral=True)

class Paginator(discord.ui.View):
    def __init__(self, collection):
        super().__init__(timeout=60)
        self.collection = collection
        self.current_page = 0

    async def send_initial_message(self, ctx_or_interaction):
        embed = self.create_embed()
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed, view=self)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=self)

    def create_embed(self):
        card = self.collection[self.current_page]
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name="Rank", value=card["rank"])
        embed.add_field(name="Value", value=f'{card["value"]} 💎')
        embed.set_image(url=card["image_urls"][0])
        embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)}')
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.collection)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.collection)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class GlobalPaginator(discord.ui.View):
    def __init__(self, collection):
        super().__init__(timeout=60)
        self.collection = collection
        self.current_page = 0

    async def send_initial_message(self, ctx_or_interaction):
        embed = self.create_embed()
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed, view=self)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=self)

    def create_embed(self):
        card = self.collection[self.current_page]
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name="Rank", value=card["rank"])
        embed.add_field(name="Value", value=f'{card["value"]} 💎')
        embed.set_image(url=card["image_urls"][0])
        embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)}')
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.collection)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.collection)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class ImagePaginator(discord.ui.View):
    def __init__(self, card):
        super().__init__(timeout=60)
        self.card = card
        self.current_image = 0

    async def send_initial_message(self, ctx_or_interaction):
        embed = self.create_embed()
        if isinstance(ctx_or_interaction, discord.ext.commands.Context):
            await ctx_or_interaction.send(embed=embed, view=self)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=self)

    def create_embed(self):
        image_url = self.card["image_urls"][self.current_image]
        embed = discord.Embed(title=self.card["name"], description=self.card["description"])
        embed.add_field(name="Rank", value=self.card["rank"])
        embed.add_field(name="Value", value=f'{self.card["value"]} 💎')
        claimed_by = "Not claimed" if not self.card["claimed_by"] else f'Claimed by <@{self.card["claimed_by"]}>'
        embed.add_field(name="Claimed", value=claimed_by)
        embed.set_image(url=image_url)
        embed.set_footer(text=f'{self.current_image + 1}/{len(self.card["image_urls"])}')
        embed.color = discord.Color.red() if self.card['claimed_by'] else discord.Color.orange()
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_image = (self.current_image - 1) % len(self.card["image_urls"])
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_image = (self.current_image + 1) % len(self.card["image_urls"])
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)