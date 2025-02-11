import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from utils import load_data, save_data
from config import initialize_guild_data, load_guild_data, guild_data
from commands import setup_commands
from utils import get_time_until_next_reset

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@tasks.loop(minutes=1)
async def reset_rolls():
    now = datetime.utcnow()
    next_reset = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    await asyncio.sleep((next_reset - now).total_seconds())
    global roll_cooldowns
    roll_cooldowns = {}
    for guildid in guild_data:
        for memberid in guild_data[guildid][2]:
            user_data = guild_data[guildid][2]
            user_data[str(memberid)]['rolls'] = 5
            print("roll reset for" + memberid)

@tasks.loop(minutes=1)
async def reset_claim():
    next_reset = get_time_until_next_reset()
    print("Next claim reset in : next_reset")
    await asyncio.sleep((next_reset).total_seconds())
    for guildid in guild_data:
        for memberid in guild_data[guildid][2]:
                user_data = guild_data[guildid][2]
                user_data[str(memberid)]['claims'] = 1
                print("claim reset for" + memberid)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        initialize_guild_data(bot)
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
        reset_rolls.start() 
        reset_claim.start()
    except Exception as e:
        print(f'Error syncing commands: {e}')

setup_commands(bot)

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
