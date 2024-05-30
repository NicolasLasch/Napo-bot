import json
import os

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
