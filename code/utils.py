import json

# Paths to JSON files
CARDS_FILE = 'cards.json'
COLLECTIONS_FILE = 'collections.json'
USER_DATA_FILE = 'userdata.json'

def load_data():
    try:
        with open(CARDS_FILE, 'r') as f:
            cards = json.load(f)
    except FileNotFoundError:
        cards = []

    try:
        with open(COLLECTIONS_FILE, 'r') as f:
            user_collections = json.load(f)
    except FileNotFoundError:
        user_collections = {}

    try:
        with open(USER_DATA_FILE, 'r') as f:
            user_data = json.load(f)
    except FileNotFoundError:
        user_data = {}

    return cards, user_collections, user_data

def save_data(cards, user_collections, user_data):
    with open(CARDS_FILE, 'w') as f:
        json.dump(cards, f, indent=4)

    with open(COLLECTIONS_FILE, 'w') as f:
        json.dump(user_collections, f, indent=4)

    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)

def rank_sort_key(card):
    rank_order = {'SS': 1, 'S': 2, 'A': 3, 'B': 4, 'C': 5, 'D': 6, 'E': 7}
    return rank_order.get(card['rank'], 8)
