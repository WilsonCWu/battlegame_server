# Constants
from enum import Enum, auto


class Game(Enum):
    QuickPlay = 0
    Dungeon = 1
    Tournament = 2
    DailyDungeon = 3
    Moevasion = 4
    Sandbox = 5
    Replay = 6
    ClanPVE = 7
    MoveTester = 8
    Roguelike = 9
    AFKBattle = 10
    TurkeyRoguelike = 11
    StoryRoguelike = 12


NUM_DAILY_QUESTS = 6
NUM_WEEKLY_QUESTS = 6
DAILY_QUEST_POOL_IDS = [9, 44, 150, 323, 415, 421, 422]
WEEKLY_QUEST_POOL_IDS = [13, 34, 45, 46, 151, 328, 413, 419, 423]

DUNGEON_REFERRAL_CONVERSION_STAGE = 200
LEVEL_BOOSTER_UNLOCK_STAGE = 100
WISHLIST_UNLOCK_STAGE = 80
FORTUNE_CHEST_UNLOCK_STAGE = 40*4
REFEREE_GEMS_REWARD = 2500
REFERER_GEMS_REWARD = 500


class DungeonType(Enum):
    CAMPAIGN = 0
    TOWER = 1
    TUNNELS = 2

MAX_DUNGEON_STAGE = [1680, 90]
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
COLLECT_ITEM = 25
UPGRADE_ITEM = 26
START_ET_RUN = 27
COLLECT_AFK_REWARD = 28
INSTAGRAM = 29
SEND_CHAT_MSG_GLOBAL = 30
SEND_CHAT_TO_CLAN = 31
ASCEND_X_HEROES = 32
WIN_X_TROPHIES = 33
UPGRADE_ITEM_POINTS = 34


# Namespace: everything in the 100s is a char_id + 100 for a quest 'Win X games' with that char
# so for Archer (id: 1), quest_type would be 101
WIN_X_GAMES_WITH_CHAR_NAMESPACE = 100


class NotificationType(Enum):
    DAILY_QUEST = 0
    WEEKLY_QUEST = 1
    CUMULATIVE_QUEST = 2
    GRASS_EVENT = 3
    CHRISTMAS_2021 = 4


# Tournament constants
TOURNEY_SIZE = 8

# Purchases constants
class PurchaseID(Enum):
    MYTHIC_CHEST = "MYTHIC_CHEST"
    FORTUNE_CHEST = "FORTUNE_CHEST"

SUMMON_GEM_COST = {
    "SUMMON1": 300,
    "SUMMON10": 2700,
    "MYTHIC_CHEST": 2700,
    "FORTUNE_CHEST": 9000,
}


# Pity caps guarantee in how many rolls we guarantee a legendary
LEGENDARY_PITY_CAP_MYTHICAL = 50
LEGENDARY_PITY_CAP_SILVER = 160
LEGENDARY_PITY_CAP_GOLD = 160

REFUND_GEMS_COST_PER_LVL = 5
REFUND_CHAR_GEMS = 50
ESSENCE_PER_COMMON_CHAR_RETIRE = 100

CHAPTER_REWARDS_PACK0 = 'com.salutationstudio.tinytitans.chapterrewards.pack0'
# DEPRECATED DONT USE  CHAPTER_REWARDS_PACK1 = 'com.salutationstudio.tinytitans.chapterrewards.pack1'
CHAPTER_REWARDS_PACK2 = 'com.salutationstudio.tinytitans.chapterrewards.pack2'
CHAPTER_REWARDS_PACK3 = 'com.salutationstudio.tinytitans.chapterrewards.pack3'

DEAL_DAILY_0 = 'com.salutationstudio.tinytitans.deal.daily0'
DEAL_DAILY_1 = 'com.salutationstudio.tinytitans.deal.daily1'
DEAL_DAILY_2 = 'com.salutationstudio.tinytitans.deal.daily2'
DEAL_DAILY_3 = 'com.salutationstudio.tinytitans.deal.daily3'
DEAL_DAILY_4 = 'com.salutationstudio.tinytitans.deal.daily4'

DEAL_WEEKLY_0 = 'com.salutationstudio.tinytitans.deal.weekly0'
DEAL_WEEKLY_1 = 'com.salutationstudio.tinytitans.deal.weekly1'
DEAL_WEEKLY_2 = 'com.salutationstudio.tinytitans.deal.weekly2'
DEAL_WEEKLY_3 = 'com.salutationstudio.tinytitans.deal.weekly3'
DEAL_WEEKLY_4 = 'com.salutationstudio.tinytitans.deal.weekly4'

DEAL_MONTHLY_0 = 'com.salutationstudio.tinytitans.deal.monthly0'
DEAL_MONTHLY_1 = 'com.salutationstudio.tinytitans.deal.monthly1'
DEAL_MONTHLY_2 = 'com.salutationstudio.tinytitans.deal.monthly2'
DEAL_MONTHLY_3 = 'com.salutationstudio.tinytitans.deal.monthly3'
DEAL_MONTHLY_4 = 'com.salutationstudio.tinytitans.deal.monthly4'
DEAL_MONTHLY_5 = 'com.salutationstudio.tinytitans.deal.monthly5'
DEAL_MONTHLY_6 = 'com.salutationstudio.tinytitans.deal.monthly6'
DEAL_MONTHLY_7 = 'com.salutationstudio.tinytitans.deal.monthly7'

GEMS_499 = 'com.salutationstudio.tinytitans.gems.499'
GEMS_999 = 'com.salutationstudio.tinytitans.gems.999'
GEMS_1999 = 'com.salutationstudio.tinytitans.gems.1999'

GEMS_2999 = 'com.salutationstudio.tinytitans.gems.2999'
GEMS_4999 = 'com.salutationstudio.tinytitans.gems.4999'
GEMS_9999 = 'com.salutationstudio.tinytitans.gems.9999'

WORLD_PACK_0 = 'com.salutationstudio.tinytitans.worldpack0'
WORLD_PACK_1 = 'com.salutationstudio.tinytitans.worldpack1'
WORLD_PACK_2 = 'com.salutationstudio.tinytitans.worldpack2'
WORLD_PACK_3 = 'com.salutationstudio.tinytitans.worldpack3'
WORLD_PACK_4 = 'com.salutationstudio.tinytitans.worldpack4'

MONTHLY_PASS = 'com.salutationstudio.tinytitans.monthlypass1'

REGAL_REWARDS_PASS = 'com.salutationstudio.tinytitans.imperialpremium'

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

FRONTLINE_CHARS = [0, 5, 6, 8, 11, 13, 19, 24, 30, 37]
BACKLINE_CHARS = [4, 7, 9, 10, 12, 16, 17, 18, 21, 22, 23, 26, 31, 32, 33, 34, 35, 38]

FRONTLINE_POS = range(1, 16)
BACKLINE_POS = range(16, 26)

MAX_LEVEL_BOOSTER_SLOTS = 25
MAX_ENHANCED_SLOTS = MAX_LEVEL_BOOSTER_SLOTS + 5  # 5 free slots for pentagram chars when enhancing crystal
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
MAX_PRESTIGE_LEVEL = 10   # TODO: deprecate after 1.0.8
PRESTIGE_COPIES_REQUIRED = [1, 2, 4, 10, 20, 50, 100, 200, 400, 800]  # TODO: deprecate after 1.0.8
PRESTIGE_CAP_BY_RARITY = {
    1: MAX_PRESTIGE_LEVEL,
    2: MAX_PRESTIGE_LEVEL - 1,
    3: MAX_PRESTIGE_LEVEL - 3,
    4: MAX_PRESTIGE_LEVEL - 5,
}

MAX_PRESTIGE_LEVEL_15 = 15
PRESTIGE_COPIES_REQUIRED_BY_RARITY = {
    1: [1, 2, 4, 10, 20, 50, 100, 200, 400, 800, 400, 400, 400, 400, 400],  # Commons aren't used
    2: [1, 2, 4, 10, 20, 50, 100, 200, 400, 300, 300, 300, 300, 300],  # Rare
    3: [1, 2, 4, 10, 20, 50, 100, 50, 50, 50, 50, 50],  # Epic
    4: [1, 2, 4, 10, 20, 10, 10, 10, 10, 10],  # Legendary
}

PRESTIGE_CAP_BY_RARITY_15 = {
    1: MAX_PRESTIGE_LEVEL_15,
    2: MAX_PRESTIGE_LEVEL_15 - 1,
    3: MAX_PRESTIGE_LEVEL_15 - 3,
    4: MAX_PRESTIGE_LEVEL_15 - 5,
}


def PRESTIGE_TO_STAR_LEVEL(prestige, rarity):
    return prestige + (MAX_PRESTIGE_LEVEL_15 - PRESTIGE_CAP_BY_RARITY_15[rarity])


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
    LOGIN_GEMS = 7
    FORTUNE = 8


class RewardType(Enum):
    COINS = "coins"
    GEMS = "gems"
    DUST = "essence"
    RELIC_STONES = "relic_stone"
    RARE_SHARDS = "rare_shards"
    EPIC_SHARDS = "epic_shards"
    LEGENDARY_SHARDS = "legendary_shards"
    DUST_FAST_REWARDS = "dust_fast_reward_hours"
    COINS_FAST_REWARDS = "coins_fast_reward_hours"
    CHAMP_BADGE = "champ_badge"
    REGAL_POINTS = "regal_points"
    CHAR_ID = "char_id"
    ITEM_ID = "item_id"
    PROFILE_PIC = "profile_pic"
    PET_ID = "pet_id"
    CHEST = "chest"
    EMBER = "ember"


REGAL_REWARD_INTERVAL = 800

RESOURCE_SHOP_DEFAULT_REFRESHES = 2

CHEST_ODDS = [750, 250, 0, 0, 0, 0]

MIN_REWARDS_PER_CHEST = {
    ChestType.SILVER.value: 3,
    ChestType.GOLD.value: 5,
    ChestType.MYTHICAL.value: 10,
    ChestType.EPIC.value: 6,
    ChestType.LEGENDARY.value: 1,
    ChestType.DAILY_DUNGEON.value: 3,
}
MAX_REWARDS_PER_CHEST = {
    ChestType.SILVER.value: 3,
    ChestType.GOLD.value: 5,
    ChestType.MYTHICAL.value: 10,
    ChestType.EPIC.value: 7,
    ChestType.LEGENDARY.value: 1,
    ChestType.DAILY_DUNGEON.value: 3,
}
FORTUNE_CHEST_CHANCE = [700, 300]  # 70% chance to get fortune cards in fortune chest
FORTUNE_CHEST_LEGENDARY_CHANCE = [100, 900]

# Index for chest reward types corresponding to the values in the RESOURCE_TYPE_ODDS_PER_CHEST buckets
REWARD_TYPE_INDEX = ['coins', 'gems', 'essence', 'char_id', 'item_id']

# The odds for getting each type of reward for respective chest rarity
# Each column represents: ['coins', 'gems', 'essence', 'char_id', 'item_id']
# Ex: RESOURCE_TYPE_ODDS[0][0] are the odds to get a 'coins' reward for a SILVER chest
# NOTE: each row should total to 1000
RESOURCE_TYPE_ODDS_PER_CHEST = {
    ChestType.SILVER.value: [200, 600, 200, 0, 0],  # SILVER
    ChestType.GOLD.value: [200, 600, 200, 0, 0],  # GOLD
    ChestType.MYTHICAL.value: [100, 400, 100, 200, 200],  # MYTHICAL
    ChestType.EPIC.value: [200, 200, 100, 300, 200],  # EPIC
    ChestType.LEGENDARY.value: [200, 200, 100, 300, 200],  # LEGENDARY
    ChestType.DAILY_DUNGEON.value: [350, 0, 350, 150, 150],  # DAILY_DUNGEON
    ChestType.LOGIN_GEMS.value: [200, 600, 200, 0, 0],  # LOGIN_GEMS
    ChestType.FORTUNE.value: [200, 600, 200, 0, 0],  # FORTUNE
}

CHEST_GEMS_PER_HOUR = 120

# Number of guaranteed summons per chest rarity
GUARANTEED_SUMMONS = [1, 3, 8, 0, 1, 1, 0, 8]


# The number of chars of each char_rarity guaranteed for a chest_rarity
# Ex: CHAR_RARITY_GUARANTEE[0][0] is number of guaranteed rarity=1 chars for a SILVER chest
GUARANTEED_CHARS_PER_RARITY_PER_CHEST = {
    ChestType.SILVER.value: [0, 0, 0, 0, 0],  # SILVER
    ChestType.GOLD.value: [0, 0, 0, 0, 0],  # GOLD
    ChestType.MYTHICAL.value: [0, 0, 0, 1, 0],  # MYTHICAL
    ChestType.EPIC.value: [0, 0, 0, 5, 0],  # EPIC
    ChestType.LEGENDARY.value: [0, 0, 0, 0, 1],  # LEGENDARY
    ChestType.DAILY_DUNGEON.value: [0, 0, 0, 0, 0],  # DAILY_DUNGEON
    ChestType.LOGIN_GEMS.value: [0, 0, 0, 0, 0],  # LOGIN_GEMS
    ChestType.FORTUNE.value: [0, 0, 5, 3, 0]  # FORTUNE
}

# Odds of getting each rarity char on non-guaranteed roll
# NOTE: each row should total to 1000
REGULAR_CHAR_ODDS_PER_CHEST = {
    ChestType.SILVER.value: [0, 890, 100, 10],  # SILVER
    ChestType.GOLD.value: [0, 890, 100, 10],  # GOLD
    ChestType.MYTHICAL.value: [0, 770, 200, 30],  # MYTHICAL
    ChestType.EPIC.value: [0, 0, 1000, 0],  # EPIC
    ChestType.LEGENDARY.value: [0, 100, 550, 350],  # LEGENDARY
    ChestType.DAILY_DUNGEON.value: [0, 890, 100, 10],  # DAILY_DUNGEON
    ChestType.LOGIN_GEMS.value: [0, 890, 100, 10],  # LOGIN_GEMS
    ChestType.FORTUNE.value: [0, 890, 100, 10],  # FORTUNE
}

# Odds of getting each rarity item on non-guaranteed roll
# NOTE: each row should total to 1000
REGULAR_ITEM_ODDS_PER_CHEST = {
    ChestType.SILVER.value: [400, 400, 200, 0, 0],  # SILVER
    ChestType.GOLD.value: [300, 400, 300, 0, 0],  # GOLD
    ChestType.MYTHICAL.value: [420, 350, 200, 30, 0],  # MYTHICAL
    ChestType.EPIC.value: [0, 0, 0, 1000, 0],  # EPIC
    ChestType.LEGENDARY.value: [0, 0, 0, 0, 1000],  # LEGENDARY
    ChestType.DAILY_DUNGEON.value: [400, 400, 200, 0, 0],  # DAILY_DUNGEON
    ChestType.LOGIN_GEMS.value: [400, 400, 200, 0, 0],  # LOGIN_GEMS
    ChestType.FORTUNE.value: [300, 400, 300, 0, 0],  # FORTUNE
}

AFK_SHARD_DROP_RATE = [0, 0, 890, 100, 10]
AFK_BASE_SHARD_REWARD = [0, 0, 8, 10, 4]

DD_BASE_SHARD_REWARD = [0, 0, 328, 106, 7]

DD_SILVER_ITEM_DROP_RATE_PER_TIER = [
    [1000, 0, 0, 0],  # tier 0
    [700, 300, 0, 0],  # tier 1
    [400, 500, 100, 0],  # tier 2
    [100, 740, 150, 10],  # tier 3
]

DD_GOLDEN_ITEM_DROP_RATE_PER_TIER = [
    [500, 500, 0, 0],  # tier 0
    [300, 700, 0, 0],  # tier 1
    [220, 430, 350, 0],  # tier 2
    [70, 400, 500, 30],  # tier 3
]

SKIP_GEM_COST = 2
MAX_DAILY_QUICKPLAY_WINS_FOR_GOLD = 25
MAX_DAILY_QUICKPLAY_GAMES = 300
MAX_ELO = 3500

CREATOR_CODE_SHARED_PERCENT = 0.05

NUMBER_OF_USAGE_BUCKETS = 50
USAGE_BUCKET_ELO_SIZE = 500


class GrassRewardType(Enum):
    DECENT = 0
    GOOD = 1
    GREAT = 2
    JACKPOT = 3


GRASS_REWARDS_PER_TIER = {
    GrassRewardType.DECENT.value: 16,
    GrassRewardType.GOOD.value: 5,
    GrassRewardType.GREAT.value: 3,
    GrassRewardType.JACKPOT.value: 1,
}


class EventType(Enum):
    GRASS = 'grass_event'
    CHRISTMAS_2021 = 'christmas_2021'
