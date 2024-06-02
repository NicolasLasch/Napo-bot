import json
import os
from datetime import datetime, timedelta

DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_guild_data_file(guild_id, file_type):
    return os.path.join(DATA_DIR, f'{guild_id}_{file_type}.json')

def load_data(guild_id):
    cards_file = get_guild_data_file(guild_id, 'cards')
    collections_file = get_guild_data_file(guild_id, 'collections')
    user_data_file = get_guild_data_file(guild_id, 'user_data')

    try:
        with open(cards_file, 'r') as f:
            cards = json.load(f)
    except FileNotFoundError:
        cards = []

    try:
        with open(collections_file, 'r') as f:
            user_collections = json.load(f)
    except FileNotFoundError:
        user_collections = {}

    try:
        with open(user_data_file, 'r') as f:
            user_data = json.load(f)
    except FileNotFoundError:
        user_data = {}

    for user in user_data.values():
        if 'last_gem_time' not in user:
            user['last_gem_time'] = (datetime.utcnow() - timedelta(hours=6)).isoformat()
        if 'wishes' not in user:
            user['wishes'] = []
            
    return cards, user_collections, user_data

def save_data(guild_id, cards, user_collections, user_data):
    cards_file = get_guild_data_file(guild_id, 'cards')
    collections_file = get_guild_data_file(guild_id, 'collections')
    user_data_file = get_guild_data_file(guild_id, 'user_data')

    with open(cards_file, 'w') as f:
        json.dump(cards, f, indent=4)

    with open(collections_file, 'w') as f:
        json.dump(user_collections, f, indent=4)

    with open(user_data_file, 'w') as f:
        json.dump(user_data, f, indent=4)

def rank_sort_key(card):
    rank_order = {'SS': 0, 'S': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5, 'E': 6}
    return rank_order.get(card['rank'], 7)

def get_time_until_next_reset():
    now = datetime.utcnow()
    next_reset_hour = (now.hour // 3 + 1) * 3
    next_reset_time = now.replace(hour=next_reset_hour % 24, minute=0, second=0, microsecond=0)
    if next_reset_hour >= 24:
        next_reset_time += timedelta(days=1)
    return next_reset_time - now

scores = {}

quiz_data = {
    'Naruto': 'https://www.youtube.com/watch?v=4t__wczfpRI',
    'One Piece': 'https://www.youtube.com/watch?v=hBi9wavp2w4',
    'Attack on Titan': 'https://www.youtube.com/watch?v=CbvQKBaDUWI',
    'My Hero Academia': 'https://www.youtube.com/watch?v=iYZIUtDAFIw'

}

quiz_data = {
    'Naruto': 'https://www.youtube.com/watch?v=4t__wczfpRI',
    'Naruto': 'https://www.youtube.com/watch?v=SRn99oN1p_c',
    'One Piece': 'https://www.youtube.com/watch?v=hBi9wavp2w4',
    'Attack on Titan': 'https://www.youtube.com/watch?v=CbvQKBaDUWI',
    'My Hero Academia': 'https://www.youtube.com/watch?v=iYZIUtDAFIw',
    'FullMetal Alchemists': 'https://www.youtube.com/watch?v=elyXcwunIYA',
    'Jujutsu Kaisen': 'https://www.youtube.com/watch?v=6riDJMI-Y8U',
    'Oshi No Ko': 'https://www.youtube.com/watch?v=ZYlaUrj2Zkk',
    'Erased': 'https://www.youtube.com/watch?v=fodAJ-1dN3I',
    'Mob Psycho': 'https://www.youtube.com/watch?v=Bw-5Lka7gPE',
    'Your Lie In April': 'https://www.youtube.com/watch?v=fWRPihlt2ho',
    'Demon Slayer': 'https://www.youtube.com/watch?v=pmanD_s7G3U',
    'Love Is War': 'https://www.youtube.com/watch?v=lTlzDfhPtFA',
    'Fairy Tail': 'https://www.youtube.com/watch?v=9jvVBVcZ0-Y',
    'Horimiya': 'https://www.youtube.com/watch?v=md_jaWVuaCM',
    'Chainsaw Man': 'https://www.youtube.com/watch?v=dFlDRhvM4L0',
    'Haikyuu': 'https://www.youtube.com/watch?v=attNJ5pluDE',
    'Mirai Nikki': 'https://www.youtube.com/watch?v=09r-78dfrvc',
    'Dororo': 'https://www.youtube.com/watch?v=9Q1rTavZBJo',
    'Toradora': 'https://www.youtube.com/watch?v=BDoNRDqgmT0'
}