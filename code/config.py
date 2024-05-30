from utils import load_data

guild_data = {}

def initialize_guild_data(bot):
    global guild_data
    for guild in bot.guilds:
        guild_data[guild.id] = load_data(guild.id)

def load_guild_data(guild):
    global guild_data
    guild_data[guild.id] = load_data(guild.id)
