import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from utils import load_data, save_data
from commands import setup_commands

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # Ensure message content intent is enabled

bot = commands.Bot(command_prefix="!", intents=intents)

guild_data = {}
for guild in bot.guilds:
    guild_data[guild.id] = load_data(guild.id)

@bot.event
async def on_guild_join(guild):
    guild_data[guild.id] = load_data(guild.id)


@tasks.loop(minutes=1)
async def reset_rolls():
    now = datetime.utcnow()
    next_reset = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    await asyncio.sleep((next_reset - now).total_seconds())
    global roll_cooldowns, claim_cooldowns
    roll_cooldowns = {}
    claim_cooldowns = {}
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                user_data[str(member.id)]['rolls'] = 5
                user_data[str(member.id)]['claims'] = 1

setup_commands(bot, cards, user_collections, user_data)


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
        reset_rolls.start() 
    except Exception as e:
        print(f'Error syncing commands: {e}')

setup_commands(bot, cards, user_collections, user_data)

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
