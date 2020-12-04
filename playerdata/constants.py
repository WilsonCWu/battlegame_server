# Constants
from enum import Enum

QUICKPLAY = 0
DUNGEON = 1
TOURNAMENT = 2

NUM_DAILY_QUESTS = 3
NUM_WEEKLY_QUESTS = 5

DUNGEON_REFERRAL_CONVERSION_STAGE = 40

# Constant Quest types
# Comments are for reference of how these quests should track progress / total
DAMAGE_DEALT = 0  # Tracked / total damage
COINS_EARNED = 1
ULTS_USED = 2
LEVEL_UP_A_HERO = 3
PURCHASE_ITEM = 4  # Tracked
DISCORD = 5  # Tracked / 1
TWITTER = 6
ACCOUNT_LINK = 7  # Tracked / 1
JOIN_GUILD = 8  # Tracked / 1
FIGHT_GUILD_WAR = 9
MAKE_A_FRIEND = 10  # Tracked / 1
WIN_QUICKPLAY_GAMES = 11  # Tracked / total games
WIN_DUNGEON_GAMES = 12  # Tracked / total games
OWN_HEROES = 13  # Tracked / total heroes
REACH_PLAYER_LEVEL = 14
REACH_DUNGEON_LEVEL = 15  # Tracked / total dungeon level
REFERRAL = 16  # Tracked / total referrals

# Namespace: everything in the 100s is a char_id + 100 for a quest 'Win X games' with that char
# so for Archer (id: 1), quest_type would be 101
WIN_X_GAMES_WITH_CHAR_NAMESPACE = 100


# Tournament constants
TOURNEY_SIZE = 8


# Purchases constants
SUMMON_GEM_COST = {
    "SUMMON1": 300,
    "SUMMON10": 2700,
}

SUMMON_COUNT = {
    "SUMMON1": 1,
    "SUMMON10": 10,
}

DUSTING_GEMS_COST = 100

ESSENCE_PER_COMMON_CHAR_RETIRE = 100

DEAL_DAILY_0 = 'com.salutationstudio.tinytitans.deal.daily0'
DEAL_DAILY_1 = 'com.salutationstudio.tinytitans.deal.daily1'
DEAL_DAILY_2 = 'com.salutationstudio.tinytitans.deal.daily2'

DEAL_WEEKLY_0 = 'com.salutationstudio.tinytitans.deal.weekly0'
DEAL_WEEKLY_1 = 'com.salutationstudio.tinytitans.deal.weekly1'
DEAL_WEEKLY_2 = 'com.salutationstudio.tinytitans.deal.weekly2'

DEAL_GEMS_COST_0 = 'com.salutationstudio.tinytitans.deal.gemscost0'
DEAL_GEMS_COST_1 = 'com.salutationstudio.tinytitans.deal.gemscost1'
DEAL_GEMS_COST_2 = 'com.salutationstudio.tinytitans.deal.gemscost2'

# These characters cannot be rolled as they're not playable / limited time /
# other misc. reason.
_MOBS = [
    14,  # Skeleton
    15,  # Deckhand
]

_IN_PROGRESS_CHARACTERS = [
    16, # Potion Master
]

# Summon rarity constants
SUMMON_RARITY_BASE = [5, 15, 50, 100]
#SUMMON_RARITY_BASE = [2, 8, 50, 100]
SUMMON_RARITY_TOURNAMENT = [10, 40, 100, 100]

# Matcher constants
MATCHER_DEFAULT_COUNT = 30
MATCHER_START_RANGE = 100
MATCHER_INCREASE_RANGE = 50

# Inventory constants
MAX_PLAYER_LEVEL = 120
MAX_CHARACTER_LEVEL = 170

# coin shop constants
# various experimental items for closed beta
COIN_SHOP_ITEMS = [
    1016,
    1015,
    1018,
    1023,
    1004,
    1012,
    2004,
    2007,
    2002,
    2006,
    2008,
    2009,
    2028,
    2029,
    2001,
]


# Deal types
class DealType(Enum):
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2
    GEMS_COST = 3


# Chest rarity types
class ChestType(Enum):
    SILVER = 1
    GOLD = 2
    MYTHICAL = 3
    EPIC = 4
    LEGENDARY = 5

REWARD_TYPE_INDEX = ['coins', 'gems', 'essence', 'char_id', 'item_id']
CHEST_GEMS_PER_HOUR = 24
