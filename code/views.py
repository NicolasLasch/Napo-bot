import discord
from datetime import datetime, timedelta
from discord.ext import commands
from utils import save_data, get_time_until_next_reset
import random

def get_gem_value():
    probabilities = [0.6, 0.3, 0.1]
    values = [100, 200, 350]
    colors = ["<:bluegem:1246468408963367003>", "<:redgem:1246468384628150324>", "<:purplegem:1246470459168526376>"]
    value = random.choices(values, probabilities)[0]
    color = colors[values.index(value)]
    return value, color


class ClaimButton(discord.ui.Button):
    def __init__(self, guild_id, card, user_data, user_collections, cards):
        super().__init__(label="🐷", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id
        self.card = card
        self.user_data = user_data
        self.user_collections = user_collections
        self.cards = cards

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        time_until_reset = get_time_until_next_reset()

        if self.user_data[user_id]['claims'] == 0:
            await interaction.response.send_message(f"You can only claim once every 3 hours. The next reset is in **{time_until_reset.seconds // 3600}h {time_until_reset.seconds % 3600 // 60}m**.", ephemeral=True)
            return

        if self.card['claimed_by']:
            await interaction.response.send_message(f"This card is already claimed by **<@{self.card['claimed_by']}>**. You receive **100** <:bluegem:1246468408963367003>!", ephemeral=True)
            self.user_data.setdefault(user_id, {}).setdefault('coins', 0)
            self.user_data[user_id]['coins'] += 100
        else:
            self.card['claimed_by'] = user_id
            self.user_collections.setdefault(user_id, []).append(self.card)
            await interaction.response.send_message(f"You have claimed **{self.card['name']}**!", ephemeral=True)
            embed = discord.Embed(title=self.card['name'], description=self.card['description'], color=discord.Color.red())
            embed.add_field(name=f"{self.card['rank']} • {self.card['value']} <:bluegem:1246468408963367003>", value="")
            embed.set_image(url=self.card['image_urls'][0])
            user = await interaction.guild.fetch_member(user_id)
            claimed_by = f'Claimed by {user.display_name}'
            profile_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed.set_footer(text=claimed_by, icon_url=profile_url)
            self.user_data[user_id]['claims'] = 0

            await interaction.message.edit(embed=embed, view=None)

        save_data(self.guild_id, self.cards, self.user_collections, self.user_data)

class GemButton(discord.ui.Button):
    def __init__(self, guild_id, card, user_data, user_collections, cards):
        gem_value, gem_color = get_gem_value()
        super().__init__(label=gem_color, style=discord.ButtonStyle.primary)
        self.guild_id = guild_id
        self.card = card
        self.user_data = user_data
        self.user_collections = user_collections
        self.cards = cards
        self.gem_value = gem_value

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.utcnow()
        
        if 'last_gem_time' not in self.user_data[user_id]:
            self.user_data[user_id]['last_gem_time'] = (now - timedelta(hours=6)).isoformat()

        last_gem_time = datetime.fromisoformat(self.user_data[user_id]['last_gem_time'])
        if now - last_gem_time < timedelta(hours=5):
            time_left = timedelta(hours=5) - (now - last_gem_time)
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(f"You can claim another gem in {hours}h {minutes}m.", ephemeral=True)
            return
        
        if self.card.get('gem_claimed', False):
            await interaction.response.send_message(f"This card's gem has already been claimed.", ephemeral=True)
            return
        
        self.card['gem_claimed'] = True
        self.user_data[user_id]['coins'] += self.gem_value
        self.user_data[user_id]['last_gem_time'] = now.isoformat()

        save_data(self.guild_id, self.cards, self.user_collections, self.user_data)
        await interaction.response.send_message(f"You received {self.gem_value} coins from the gem <:bluegem:1246468408963367003>!", ephemeral=True)
        embed = interaction.message.embeds[0]
        embed.add_field(name="Gem Claimed", value=f"{self.gem_value} coins received", inline=False)
        await interaction.message.edit(embed=embed, view=None)


class Paginator(discord.ui.View):
    def __init__(self, guild_id, collection):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.collection = collection
        self.current_page = 0

    async def send_initial_message(self, ctx_or_interaction):
        embed = await self.create_embed(ctx_or_interaction)
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed, view=self)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=self)

    async def create_embed(self, ctx_or_interaction):
        card = self.collection[self.current_page]
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name=f"{card['rank']} • {card['value']} <:bluegem:1246468408963367003>", value="")
        embed.set_image(url=card["image_urls"][0])
        embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)}')
        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()

        if card["claimed_by"]:
            user = await ctx_or_interaction.guild.fetch_member(card["claimed_by"])
            claimed_by = f'Claimed by {user.display_name}'
            profile_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)} • {claimed_by}', icon_url=profile_url)
        else:
            embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)} • Not claimed')

        return embed

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.collection)
        embed = await self.create_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.collection)
        embed = await self.create_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

class GlobalPaginator(discord.ui.View):
    def __init__(self, guild_id, collection):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.collection = collection
        self.current_page = 0

    async def send_initial_message(self, ctx_or_interaction):
        embed = await self.create_embed(ctx_or_interaction)
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed, view=self)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=self)

    async def create_embed(self, ctx_or_interaction):
        card = self.collection[self.current_page]
        embed = discord.Embed(title=card["name"], description=card["description"])
        embed.add_field(name=f"{card['rank']} • {card['value']} <:bluegem:1246468408963367003>", value="")
        embed.set_image(url=card["image_urls"][0])

        if card["claimed_by"]:
            user = await ctx_or_interaction.guild.fetch_member(card["claimed_by"])
            claimed_by = f'Claimed by {user.display_name}'
            profile_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)} • {claimed_by}', icon_url=profile_url)
        else:
            embed.set_footer(text=f'{self.current_page + 1}/{len(self.collection)} • Not claimed')

        embed.color = discord.Color.red() if card['claimed_by'] else discord.Color.orange()
        return embed

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.collection)
        embed = await self.create_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.collection)
        embed = await self.create_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

class ImagePaginator(discord.ui.View):
    def __init__(self, guild_id, card, current_image=0):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.card = card
        self.current_image = current_image

    async def send_initial_message(self, ctx_or_interaction):
        embed = await self.create_embed(ctx_or_interaction)
        if isinstance(ctx_or_interaction, discord.ext.commands.Context):
            await ctx_or_interaction.send(embed=embed, view=self)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=self)

    async def create_embed(self, ctx_or_interaction):
        image_url = self.card["image_urls"][self.current_image]
        embed = discord.Embed(title=self.card["name"], description=self.card["description"])
        embed.add_field(name=f"{self.card['rank']} • {self.card['value']} <:bluegem:1246468408963367003>", value="")

        if self.card["claimed_by"]:
            user = await ctx_or_interaction.guild.fetch_member(self.card["claimed_by"])
            claimed_by = f'Claimed by {user.display_name}'
            profile_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed.set_footer(text=f'{self.current_image + 1}/{len(self.card["image_urls"])} • {claimed_by}', icon_url=profile_url)
        else:
            embed.set_footer(text=f'{self.current_image + 1}/{len(self.card["image_urls"])} • Not claimed')

        embed.set_image(url=image_url)
        embed.color = discord.Color.red() if self.card['claimed_by'] else discord.Color.orange()
        return embed

    @discord.ui.button(label="<:left:1246472391052234762>", style=discord.ButtonStyle.secondary)
    async def previous_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_image = (self.current_image - 1) % len(self.card["image_urls"])
        embed = await self.create_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="<:right:1246472426410217594>", style=discord.ButtonStyle.secondary)
    async def next_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_image = (self.current_image + 1) % len(self.card["image_urls"])
        embed = await self.create_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)
