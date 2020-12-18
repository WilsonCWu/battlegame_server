# Constants
from enum import Enum

QUICKPLAY = 0
DUNGEON = 1
TOURNAMENT = 2

NUM_DAILY_QUESTS = 3
NUM_WEEKLY_QUESTS = 5
DAILY_QUEST_POOL_IDS = [9, 10, 13]
WEEKLY_QUEST_POOL_IDS = [17, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32]

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
ATTEMPT_DUNGEON_GAMES = 17

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
    16,  # Potion Master
]

RARITY_INDEX = [1, 2, 3, 4]

# Summon rarity constants
SUMMON_RARITY_BASE = [500, 350, 100, 50]
SUMMON_RARITY_TOURNAMENT = [300, 300, 300, 100]

# Matcher constants
MATCHER_DEFAULT_COUNT = 30
MATCHER_START_RANGE = 100
MATCHER_INCREASE_RANGE = 50

# Inventory constants
MAX_PLAYER_LEVEL = 120
MAX_CHARACTER_LEVEL = 170
MAX_PRESTIGE_LEVEL = 10
PRESTIGE_COPIES_REQUIRED = [1, 2, 4, 10, 20, 50, 100, 200, 400, 800]
PRESTIGE_CAP_BY_RARITY = [0, MAX_PRESTIGE_LEVEL - 1, MAX_PRESTIGE_LEVEL - 3, MAX_PRESTIGE_LEVEL - 5]

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


# Chest Constants
class ChestType(Enum):
    SILVER = 1
    GOLD = 2
    MYTHICAL = 3
    EPIC = 4
    LEGENDARY = 5


CHEST_ODDS = [650, 250, 100, 0, 0]
MIN_REWARDS_PER_CHEST = [7, 7, 7, 6, 5]
MAX_REWARDS_PER_CHEST = [10, 10, 10, 7, 6]

REWARD_TYPE_INDEX = ['coins', 'gems', 'essence', 'char_id', 'item_id']

# The odds for getting each type of reward for respective chest rarity
# Ex: RESOURCE_TYPE_ODDS[0][0] are the odds to get a 'coins' reward for a SILVER chest
# NOTE: each row should total to 1000
RESOURCE_TYPE_ODDS_PER_CHEST = [
    [200, 200, 100, 300, 200],  # SILVER
    [200, 200, 100, 300, 200],  # GOLD
    [200, 200, 100, 300, 200],  # MYTHICAL
    [200, 200, 100, 300, 200],  # EPIC
    [200, 200, 100, 300, 200],  # LEGENDARY
]

CHEST_GEMS_PER_HOUR = 24

# The number of chars of each char_rarity guaranteed for a chest_rarity
# Ex: CHAR_RARITY_GUARANTEE[0][0] is number of guaranteed rarity=1 chars for a SILVER chest
GUARANTEED_CHARS_PER_RARITY_PER_CHEST = [
    [0, 3, 0, 0],  # SILVER
    [0, 2, 1, 0],  # GOLD
    [0, 2, 2, 0],  # MYTHICAL
    [0, 0, 5, 0],  # EPIC
    [0, 0, 4, 1],  # LEGENDARY
]

# Odds of getting each rarity char on non-guaranteed roll
# NOTE: each row should total to 1000
REGULAR_CHAR_ODDS_PER_CHEST = [
    [500, 400, 100, 00],  # SILVER
    [300, 450, 250, 00],  # GOLD
    [200, 350, 450, 0],  # MYTHICAL
    [0, 0, 1000, 0],  # EPIC
    [0, 100, 550, 350],  # LEGENDARY
]

# Odds of getting each rarity item on non-guaranteed roll
# NOTE: each row should total to 1000
REGULAR_ITEM_ODDS_PER_CHEST = [
    [400, 400, 200, 0, 0],  # SILVER
    [300, 400, 300, 0, 0],  # GOLD
    [200, 350, 450, 0, 0],  # MYTHICAL
    [0, 0, 0, 1000, 0],  # EPIC
    [0, 0, 100, 550, 350],  # LEGENDARY
]
