import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils import load_data, save_data
from commands import setup_commands

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # Ensure message content intent is enabled

bot = commands.Bot(command_prefix="!", intents=intents)

cards, user_collections, user_data = load_data()

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

setup_commands(bot, cards, user_collections, user_data)

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
