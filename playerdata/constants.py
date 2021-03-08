# Constants
from enum import Enum

QUICKPLAY = 0
DUNGEON = 1
TOURNAMENT = 2

NUM_DAILY_QUESTS = 3
NUM_WEEKLY_QUESTS = 5
DAILY_QUEST_POOL_IDS = [9, 10, 13, 44]
WEEKLY_QUEST_POOL_IDS = [34, 45, 46]

DUNGEON_REFERRAL_CONVERSION_STAGE = 120
REFFERAL_GEMS_REWARD = 2500


class DungeonType(Enum):
    CAMPAIGN = 0
    TOWER = 1


MAX_DUNGEON_STAGE = [400, 45]
NUM_DUNGEON_SUBSTAGES = [20, 5]
CHAR_LEVEL_DIFF_BETWEEN_STAGES = [1, 5]

# Constant Quest types
# Comments are for reference of how these quests should track progress / total
DAMAGE_DEALT = 0  # Tracked / total damage
COINS_EARNED = 1
ULTS_USED = 2
LEVEL_UP_A_HERO = 3  # Tracked
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
REACH_DUNGEON_LEVEL = 15  # Tracked / total level
REFERRAL = 16  # Tracked / total referrals
ATTEMPT_DUNGEON_GAMES = 17  # Tracked / total games
ATTEMPT_TOWER_GAMES = 18  # Tracked / total games
WIN_TOWER_GAMES = 19  # Tracked / total games
REACH_TOWER_LEVEL = 20  # Tracked / total level
WIN_STREAK = 21  # Tracked / winstreak

# Namespace: everything in the 100s is a char_id + 100 for a quest 'Win X games' with that char
# so for Archer (id: 1), quest_type would be 101
WIN_X_GAMES_WITH_CHAR_NAMESPACE = 100

# Tournament constants
TOURNEY_SIZE = 8

# Purchases constants
class PurchaseID(Enum):
    MYTHIC_CHEST = "MYTHIC_CHEST"

SUMMON_GEM_COST = {
    "SUMMON1": 300,
    "SUMMON10": 2700,
    "MYTHIC_CHEST": 2700
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

GEMS_499 = 'com.salutationstudio.tinytitans.gems.499'
GEMS_999 = 'com.salutationstudio.tinytitans.gems.999'
GEMS_1999 = 'com.salutationstudio.tinytitans.gems.1999'

GEMS_2999 = 'com.salutationstudio.tinytitans.gems.2999'
GEMS_4999 = 'com.salutationstudio.tinytitans.gems.4999'
GEMS_9999 = 'com.salutationstudio.tinytitans.gems.9999'

IAP_GEMS_AMOUNT = {
    GEMS_499: 800,
    GEMS_999: 2060,
    GEMS_1999: 4360,
    GEMS_2999: 7060,
    GEMS_4999: 12660,
    GEMS_9999: 32160,
}

# These characters cannot be rolled as they're not playable / limited time /
# other misc. reason.
_MOBS = [
    14,  # Skeleton
    15,  # Deckhand
]

CHAR_RARITY_INDEX = [1, 2, 3, 4]
ITEM_RARITY_INDEX = [0, 1, 2, 3]

FRONTLINE_CHARS = [0, 4, 5, 6, 8, 11, 13, 19, 24]
BACKLINE_CHARS = [7, 9, 10, 12, 16, 17, 18, 21, 22, 23]

FRONTLINE_POS = range(1, 16)
BACKLINE_POS = range(16, 26)

# Summon rarity constants
SUMMON_RARITY_BASE = [500, 350, 100, 50]
SUMMON_RARITY_TOURNAMENT = [300, 300, 300, 100]

# Matcher constants
MATCHER_DEFAULT_COUNT = 30
MATCHER_START_RANGE = 100
MATCHER_INCREASE_RANGE = 50

# Inventory constants
MAX_PLAYER_LEVEL = 120
MAX_CHARACTER_LEVEL = 240
MAX_PRESTIGE_LEVEL = 10
PRESTIGE_COPIES_REQUIRED = [1, 2, 4, 10, 20, 50, 100, 200, 400, 800]
PRESTIGE_CAP_BY_RARITY = {
    1: MAX_PRESTIGE_LEVEL,
    2: MAX_PRESTIGE_LEVEL - 1,
    3: MAX_PRESTIGE_LEVEL - 3,
    4: MAX_PRESTIGE_LEVEL - 5,
}

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
    DAILY_DUNGEON = 6


CHEST_ODDS = [750, 250, 0, 0, 0, 0]
MIN_REWARDS_PER_CHEST = [3, 6, 10, 6, 5, 3]
MAX_REWARDS_PER_CHEST = [4, 6, 10, 7, 6, 3]

# Index for chest reward types corresponding to the values in the RESOURCE_TYPE_ODDS_PER_CHEST buckets
REWARD_TYPE_INDEX = ['coins', 'gems', 'essence', 'char_id', 'item_id']

# The odds for getting each type of reward for respective chest rarity
# Each column represents: ['coins', 'gems', 'essence', 'char_id', 'item_id']
# Ex: RESOURCE_TYPE_ODDS[0][0] are the odds to get a 'coins' reward for a SILVER chest
# NOTE: each row should total to 1000
RESOURCE_TYPE_ODDS_PER_CHEST = [
    [200, 600, 200, 0, 0],  # SILVER
    [200, 600, 200, 0, 0],  # GOLD
    [100, 400, 100, 200, 200],  # MYTHICAL
    [200, 200, 100, 300, 200],  # EPIC
    [200, 200, 100, 300, 200],  # LEGENDARY
    [350, 0, 350, 150, 150],  # DAILY_DUNGEON
]

CHEST_GEMS_PER_HOUR = 120

# Number of guaranteed summons per chest rarity
GUARANTEED_SUMMONS = [1, 3, 6, 0, 0, 1]

# The number of chars of each char_rarity guaranteed for a chest_rarity
# Ex: CHAR_RARITY_GUARANTEE[0][0] is number of guaranteed rarity=1 chars for a SILVER chest
GUARANTEED_CHARS_PER_RARITY_PER_CHEST = [
    [0, 0, 0, 0],  # SILVER
    [0, 0, 0, 0],  # GOLD
    [0, 0, 1, 0],  # MYTHICAL
    [0, 0, 5, 0],  # EPIC
    [0, 0, 4, 1],  # LEGENDARY
    [0, 0, 0, 0],  # DAILY_DUNGEON
]

# Odds of getting each rarity char on non-guaranteed roll
# NOTE: each row should total to 1000
REGULAR_CHAR_ODDS_PER_CHEST = [
    [0, 890, 100, 10],  # SILVER
    [0, 890, 100, 10],  # GOLD
    [0, 770, 200, 30],  # MYTHICAL
    [0, 0, 1000, 0],  # EPIC
    [0, 100, 550, 350],  # LEGENDARY
    [0, 890, 100, 10],  # DAILY_DUNGEON
]

# Odds of getting each rarity item on non-guaranteed roll
# NOTE: each row should total to 1000
REGULAR_ITEM_ODDS_PER_CHEST = [
    [400, 400, 200, 0, 0],  # SILVER
    [300, 400, 300, 0, 0],  # GOLD
    [420, 350, 200, 30, 0],  # MYTHICAL
    [0, 0, 0, 1000, 0],  # EPIC
    [0, 0, 100, 550, 350],  # LEGENDARY
    [400, 400, 200, 0, 0],  # DAILY_DUNGEON
]

SKIP_GEM_COST = 2
MAX_DAILY_QUICKPLAY_WINS_FOR_GOLD = 75
