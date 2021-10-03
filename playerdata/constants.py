# Constants
from enum import Enum, auto

QUICKPLAY = 0
DUNGEON = 1
TOURNAMENT = 2

NUM_DAILY_QUESTS = 3
NUM_WEEKLY_QUESTS = 5
DAILY_QUEST_POOL_IDS = [9, 44, 150, 323, 327]
WEEKLY_QUEST_POOL_IDS = [13, 34, 45, 46, 151, 328]

DUNGEON_REFERRAL_CONVERSION_STAGE = 200
REFEREE_GEMS_REWARD = 2500
REFERER_GEMS_REWARD = 500


class DungeonType(Enum):
    CAMPAIGN = 0
    TOWER = 1
    TUNNELS = 2

MAX_DUNGEON_STAGE = [1440, 60]
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
COMPLETE_DUNGEON_LEVEL = 15  # Tracked / total level
REFERRAL = 16  # Tracked / total referrals
ATTEMPT_DUNGEON_GAMES = 17  # Tracked / total games
ATTEMPT_TOWER_GAMES = 18  # Tracked / total games
WIN_TOWER_GAMES = 19  # Tracked / total games
COMPLETE_TOWER_LEVEL = 20  # Tracked / total level
WIN_STREAK = 21  # Tracked / winstreak
CHESTS_OPENED = 22  # Tracked / chests opened
EQUIP_GEAR = 23
FIGHT_MONSTER_HUNT = 24

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


# Pity caps guarantee in how many rolls we guarantee a legendary
LEGENDARY_PITY_CAP_MYTHICAL = 50
LEGENDARY_PITY_CAP_SILVER = 160
LEGENDARY_PITY_CAP_GOLD = 160

REFUND_GEMS_COST_PER_LVL = 5
ESSENCE_PER_COMMON_CHAR_RETIRE = 100

CHAPTER_REWARDS_PACK1 = 'com.salutationstudio.tinytitans.chapterrewards.pack1'
CHAPTER_REWARDS_PACK2 = 'com.salutationstudio.tinytitans.chapterrewards.pack2'
CHAPTER_REWARDS_PACK3 = 'com.salutationstudio.tinytitans.chapterrewards.pack3'

DEAL_DAILY_0 = 'com.salutationstudio.tinytitans.deal.daily0'
DEAL_DAILY_1 = 'com.salutationstudio.tinytitans.deal.daily1'
DEAL_DAILY_2 = 'com.salutationstudio.tinytitans.deal.daily2'

DEAL_WEEKLY_0 = 'com.salutationstudio.tinytitans.deal.weekly0'
DEAL_WEEKLY_1 = 'com.salutationstudio.tinytitans.deal.weekly1'
DEAL_WEEKLY_2 = 'com.salutationstudio.tinytitans.deal.weekly2'

DEAL_MONTHLY_0 = 'com.salutationstudio.tinytitans.deal.monthly0'
DEAL_MONTHLY_1 = 'com.salutationstudio.tinytitans.deal.monthly1'
DEAL_MONTHLY_2 = 'com.salutationstudio.tinytitans.deal.monthly2'

GEMS_499 = 'com.salutationstudio.tinytitans.gems.499'
GEMS_999 = 'com.salutationstudio.tinytitans.gems.999'
GEMS_1999 = 'com.salutationstudio.tinytitans.gems.1999'

GEMS_2999 = 'com.salutationstudio.tinytitans.gems.2999'
GEMS_4999 = 'com.salutationstudio.tinytitans.gems.4999'
GEMS_9999 = 'com.salutationstudio.tinytitans.gems.9999'

WORLD_PACK_999 = 'com.salutationstudio.tinytitans.worldpack.999'
WORLD_PACK_1999 = 'com.salutationstudio.tinytitans.worldpack.1999'

MONTHLY_PASS = 'com.salutationstudio.tinytitans.monthlypass1'

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

CHARATTRS = ["char_1", "char_2", "char_3", "char_4", "char_5"]
POSATTRS = ["pos_1", "pos_2", "pos_3", "pos_4", "pos_5"]

CHAR_RARITY_INDEX = [1, 2, 3, 4]
ITEM_RARITY_INDEX = [0, 1, 2, 3]

FRONTLINE_CHARS = [0, 4, 5, 6, 8, 11, 13, 19, 24, 30]
BACKLINE_CHARS = [7, 9, 10, 12, 16, 17, 18, 21, 22, 23, 26, 31, 32]

FRONTLINE_POS = range(1, 16)
BACKLINE_POS = range(16, 26)

LEVEL_BOOSTER_SLOTS = 20
SKIP_COOLDOWN_GEMS = 100

# Summon rarity constants
SUMMON_RARITY_BASE = [500, 350, 100, 50]
SUMMON_RARITY_TOURNAMENT = [300, 300, 300, 100]

# Matcher constants
MATCHER_DEFAULT_COUNT = 30
MATCHER_START_RANGE = 75
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


class ChapterRewardPackType(Enum):
    CHAPTER19 = 0
    CHAPTER25 = 1
    CHAPTER30 = 2


class Tiers(Enum):
    BRONZE_FIVE = auto()  # auto starts from 1
    BRONZE_FOUR = auto()
    BRONZE_THREE = auto()
    BRONZE_TWO = auto()
    BRONZE_ONE = auto()
    SILVER_FIVE = auto()
    SILVER_FOUR = auto()
    SILVER_THREE = auto()
    SILVER_TWO = auto()
    SILVER_ONE = auto()
    GOLD_FIVE = auto()
    GOLD_FOUR = auto()
    GOLD_THREE = auto()
    GOLD_TWO = auto()
    GOLD_ONE = auto()
    PLAT_FIVE = auto()
    PLAT_FOUR = auto()
    PLAT_THREE = auto()
    PLAT_TWO = auto()
    PLAT_ONE = auto()
    DIAMOND_FIVE = auto()
    DIAMOND_FOUR = auto()
    DIAMOND_THREE = auto()
    DIAMOND_TWO = auto()
    DIAMOND_ONE = auto()
    MASTER_FIVE = auto()
    MASTER_FOUR = auto()
    MASTER_THREE = auto()
    MASTER_TWO = auto()
    MASTER_ONE = auto()
    GRANDMASTER = auto()

TIER_ELO_INCREMENT = 100


# Chest Constants
class ChestType(Enum):
    SILVER = 1
    GOLD = 2
    MYTHICAL = 3
    EPIC = 4
    LEGENDARY = 5
    DAILY_DUNGEON = 6


CHEST_ODDS = [750, 250, 0, 0, 0, 0]
MIN_REWARDS_PER_CHEST = [3, 5, 10, 6, 1, 3]
MAX_REWARDS_PER_CHEST = [3, 5, 10, 7, 1, 3]

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
GUARANTEED_SUMMONS = [1, 3, 6, 0, 1, 1]


# The number of chars of each char_rarity guaranteed for a chest_rarity
# Ex: CHAR_RARITY_GUARANTEE[0][0] is number of guaranteed rarity=1 chars for a SILVER chest
GUARANTEED_CHARS_PER_RARITY_PER_CHEST = [
    [0, 0, 0, 0],  # SILVER
    [0, 0, 0, 0],  # GOLD
    [0, 0, 1, 0],  # MYTHICAL
    [0, 0, 5, 0],  # EPIC
    [0, 0, 0, 1],  # LEGENDARY
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
    [0, 0, 0, 0, 1000],  # LEGENDARY
    [400, 400, 200, 0, 0],  # DAILY_DUNGEON
]

DD_SHARD_DROP_RATE = [0, 0, 728, 257, 15]
DD_BASE_SHARD_REWARD = [0, 0, 120, 40, 3]

DD_ITEM_DROP_RATE_PER_TIER = [
    [1000, 0, 0, 0],  # tier 0
    [700, 300, 0, 0],  # tier 1
    [420, 460, 120, 0],  # tier 2
    [420, 350, 200, 30],  # tier 3
]

SKIP_GEM_COST = 2
MAX_DAILY_QUICKPLAY_WINS_FOR_GOLD = 25
MAX_ELO = 3500
