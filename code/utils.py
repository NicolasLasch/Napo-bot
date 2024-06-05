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
    'Toradora': 'https://www.youtube.com/watch?v=BDoNRDqgmT0',
    'DARLING in the FRANXX': 'https://www.youtube.com/watch?v=hCzkkHwR2gg',
    'Re:Zero': 'https://www.youtube.com/watch?v=0Vwwr3VGsYg',
    'Code Geass': 'https://www.youtube.com/watch?v=G8CFuZ9MseQ',
    'JoJo\'s Bizarre Adventure':'https://www.youtube.com/watch?v=L9DK-DRg85w',
    'Neon Genesis Evangelion': 'https://www.youtube.com/watch?v=fShlVhCfHig',
    'Log Horizon': 'https://www.youtube.com/watch?v=SXTLVPt2GD4',
    'KONOSUBA': 'https://www.youtube.com/watch?v=fpG3BPNQepY',
    'Fire Force': 'https://www.youtube.com/watch?v=JBqxVX_LXvk',
    'Psycho-Pass': 'https://www.youtube.com/watch?v=5diaZzBr4_M',
    'Bleach': 'https://www.youtube.com/watch?v=wW9TwZdWpjw',
    'Hunter X Hunter': 'https://www.youtube.com/watch?v=3wQiyOmAUOA',
    'Grand Blue': 'https://www.youtube.com/watch?v=BU3Uvy-YX8Q',
    'Death Note': 'https://www.youtube.com/watch?v=kNyR46eHDxE',
    'Blue Exorcist': 'https://www.youtube.com/watch?v=s99s4VCtCP8',
    'Bunny Girl Senpai': 'https://www.youtube.com/watch?v=qCn46TYZlyU',
    'Noragami': 'https://www.youtube.com/watch?v=aZenmeRytEM',
    'Black Clover': 'https://www.youtube.com/watch?v=dUiDZJMPh-s',
    'Charlotte': 'https://www.youtube.com/watch?v=R69bekXNpGE&t=9s',
    'Made in Abyss': 'https://www.youtube.com/watch?v=e91G8m9uM_0',
    'Kill la Kill': 'https://www.youtube.com/watch?v=qaLeO-2Fytg',
    'Dr. STONE': 'https://www.youtube.com/watch?v=fkAL_LeCsZs',
    'The Seven Deadly Sins': 'https://www.youtube.com/watch?v=dRsKZt9vAyM',
    'Sword Art Online': 'https://www.youtube.com/watch?v=yPU0ykIeumw',
    'Assassination Classroom': 'https://www.youtube.com/watch?v=iug12DnMNHQ',
    'BEASTARS': 'https://www.youtube.com/watch?v=bgo9dJB_icw',
    'Akame ga Kill': 'https://www.youtube.com/watch?v=mAzFWd5WqOg',
    'Blend S': 'https://www.youtube.com/watch?v=ugZ2EsnnGxk',
    'Tokyo Ghoul': 'https://www.youtube.com/watch?v=7aMOurgDB-o',
    'Steins;Gate': 'https://www.youtube.com/watch?v=1xJbdY9B3A8',
    'Soul Eater': 'https://www.youtube.com/watch?v=-eYK3YP524A',
    'Food Wars': 'https://www.youtube.com/watch?v=sCqmg9CMzv4',
    'My Dress Up Darling': 'https://www.youtube.com/watch?v=oG4eu4HMtbo',
    'Spy X Family': 'https://www.youtube.com/watch?v=U_rWZK_8vUY',
    'Death Parade': 'https://www.youtube.com/watch?v=UjjTMNDZi-A',
    'Vinland Saga': 'https://www.youtube.com/watch?v=xEVcTStgA4A',
    'Blue Lock': 'https://www.youtube.com/watch?v=5Iv3Fi8eb7w',
    'Hell\'s Paradise': 'https://www.youtube.com/watch?v=04WuoQMhhxw',
    'Tensura': 'https://youtu.be/SqdeDAbejkQ?si=B32dsjR0rbUNFfZk',
    'Beastars': 'https://www.youtube.com/watch?v=-5M4lbEpn6c',
    'Overlord': 'https://www.youtube.com/watch?v=erCxCAh8Wcw',
    'Serial Experiments Lain': 'https://www.youtube.com/watch?v=MM8RufZr5lw',
    'Fate/stay night': 'https://www.youtube.com/watch?v=7vZp3yGxZXE',
    'Ranking of Kings': 'https://www.youtube.com/watch?v=dWZAH5w8jkQ',
    'Kuroko\'s Basketball': 'https://www.youtube.com/watch?v=5RVEM8-UKlg',
    'Zom 100': 'https://www.youtube.com/watch?v=Tt4_enX63K0',
    'One Piece': 'https://www.youtube.com/watch?v=XSo75BY-es4',
    'Watakoi': 'https://www.youtube.com/watch?v=lIvhg8mjaDk',
    'No Game No Life': 'https://www.youtube.com/watch?v=6CBp4qylX6I',
    'Violet Evergarden': 'https://www.youtube.com/watch?v=ZAKuyZEyZjY',
    'Frieren': 'https://www.youtube.com/watch?v=wfmYSuPiYEQ',
    'The Promised Neverland': 'https://www.youtube.com/watch?v=yB2t5y7ujlg',
    'Angel Beats': 'https://www.youtube.com/watch?v=uyMEGGkHSFQ',
    'Fruits Basket': 'https://www.youtube.com/watch?v=49YTHLkcPZE',
    'Yu-Gi-Oh': 'https://www.youtube.com/watch?v=WHUcHw7j2Mc',
    'Date A Live': 'https://www.youtube.com/watch?v=146v6ZGHOaM',
    'Sailor Moon': 'https://www.youtube.com/watch?v=LGQCPOMcYJQ',
    'Cowboy Bebop': 'https://www.youtube.com/watch?v=0hfOyOBHIq4',
    'Durarara': 'https://www.youtube.com/watch?v=NYmJ15b8FmI',
    'Yuri!!! on Ice': 'https://www.youtube.com/watch?v=bKfTXRT0OeM',
    'Solo Leveling': 'https://www.youtube.com/watch?v=XqD0oCHLIF8',
    'Rent-a-Girlfriend': 'https://www.youtube.com/watch?v=cM1WSovcn4I',
    'Parasite': 'https://www.youtube.com/watch?v=ziatgnrtG0Y',
    'Your Name': 'https://www.youtube.com/watch?v=lFsg_sDwlak',
    'Classroom of the Elite': 'https://www.youtube.com/watch?v=hsfBOwAIhOw',
    'Overtake': 'https://www.youtube.com/watch?v=UMav8qtZWbc',
    'Danmachi': 'https://www.youtube.com/watch?v=0H_RCGEcjhs',
    'Domestic Girlfriend': 'https://www.youtube.com/watch?v=BV0hSfa2Cds',
    'Tokyo ghoul': 'https://www.youtube.com/watch?v=uMeR2W19wT0&list=RDQMOtZRavy7fkM&start_radio=1',
    'Fullmetal alchemist': 'https://www.youtube.com/watch?v=elyXcwunIYA&list=RDQMOtZRavy7fkM&index=2',
    'Demon slayer': 'https://www.youtube.com/watch?v=pmanD_s7G3U&list=RDQMOtZRavy7fkM&index=3',
    'Attack on titan': 'https://www.youtube.com/watch?v=CID-sYQNCew&list=RDQMOtZRavy7fkM&index=6',
    "jojo's bizarre adventure": 'https://www.youtube.com/watch?v=SJkCLcnGB-c&list=RDQMOtZRavy7fkM&index=9',
    'Naruto shippuden': 'https://www.youtube.com/watch?v=aJRu5ltxXjc&list=RDQMOtZRavy7fkM&index=11',
    'black clover': 'https://www.youtube.com/watch?v=xj9aaqzKBwM&list=RDQMOtZRavy7fkM&index=14',
    'naruto shippuden': 'https://www.youtube.com/watch?v=zVgKnfN9i34&list=RDQMOtZRavy7fkM&index=22',
    'death parade': 'https://www.youtube.com/watch?v=UjjTMNDZi-A&list=RDQMOtZRavy7fkM&index=19',
    'Dr stone': 'https://www.youtube.com/watch?v=tF4faMbs5oQ&list=RDQMOtZRavy7fkM&index=20',
    'my hero academia': 'https://www.youtube.com/watch?v=-77UEct0cZM&list=RDQMOtZRavy7fkM&index=21',
    'soul eater': 'https://www.youtube.com/watch?v=zzJ8U8OtEsE&list=RDQMOtZRavy7fkM&index=26',
    'jujutsu kaisen': 'https://www.youtube.com/watch?v=6riDJMI-Y8U&list=RDQMOtZRavy7fkM&index=28',
    'tokyo revengers': 'https://www.youtube.com/watch?v=By_JYrhx-WY&list=RDQMOtZRavy7fkM&index=24',
    'steins gate': 'https://www.youtube.com/watch?v=1FPdtR_5KFo',
    'psycho pass': ' https://www.youtube.com/watch?v=5diaZzBr4_M',
    'Yuukoku No Moriarty': 'https://www.youtube.com/watch?v=KlqRjoUU7PA',
    'The millionaire detective': 'https://www.youtube.com/watch?v=SJKQS5eYDTU',
    'haikyuu': 'https://www.youtube.com/watch?v=VKviyEGvb94',
    'Call of the Night': 'https://www.youtube.com/watch?v=rckYQnPW-wk',
    'Sakurasou': 'https://www.youtube.com/watch?v=U11Cm0mr1LY'
}