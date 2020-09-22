# Constants
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
