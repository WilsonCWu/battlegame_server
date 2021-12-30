import math
from bisect import bisect

from functools import lru_cache

from playerdata import constants, server, tier_system
from playerdata.models import UserInfo, DailyDungeonStatus

"""
Scaling Formulas
"""


#########################
## Coins


def coins_reward_quickplay(dungeon_level):
    return math.floor(dungeon_level + (dungeon_level - 1) ** 1.7 + 100)


def coins_reward_dungeon(dungeon_level, dungeon_type: int):
    adjusted_dungeon_level = dungeon_level * constants.CHAR_LEVEL_DIFF_BETWEEN_STAGES[dungeon_type]
    coins = math.floor((adjusted_dungeon_level + (adjusted_dungeon_level - 1) ** 1.7 + 100) / 2.4)
    # boss level bonus
    if dungeon_level % constants.NUM_DUNGEON_SUBSTAGES[dungeon_type] == 0:
        return coins * 4
    return coins


def afk_coins_per_min(dungeon_level):
    coins_per_min = (dungeon_level * 15 + (dungeon_level - 1) ** 1.45) / 45 + 15
    return coins_per_min / 2  # Halved for afk rewards


def char_level_to_coins(level):
    return math.floor((level - 1) * 50 + ((level - 1) ** 3.6) / 10)


def coins_chest_reward(user, rarity, chest_tier=None):
    if chest_tier is None:
        chest_tier = user.userinfo.tier_rank
    elo = tier_system.get_tier_reward_elo(chest_tier)

    base_mult = 1
    base_exp = 1

    if rarity == constants.ChestType.DAILY_DUNGEON.value:
        dd_status = DailyDungeonStatus.get_active_for_user(user)
        elo = (elo * 0.7) + (elo * 0.05) * (1.025 ** dd_status.stage)

    if rarity in [constants.ChestType.SILVER.value, constants.ChestType.DAILY_DUNGEON.value]:
        base_mult = 0.5
        base_exp = 1.35
    elif rarity == constants.ChestType.GOLD.value:
        base_mult = 1
        base_exp = 1.5
    elif rarity == constants.ChestType.MYTHICAL.value:
        base_mult = 1.5
        base_exp = 1.65

    coins = math.floor(elo * base_mult + 200 + (elo ** base_exp))

    # Bonus gold for subscribers
    if user.userinfo.is_monthly_sub:
        coins = coins * 1.15

    return coins


#########################
## EXP

# Level to exp: L(L-1)/8 + 800(2^(L-1)/7 - 1)
# simplified version of Runespace's exp formula [See the Scaling spreadsheet for details]
def level_to_exp(level):
    level = min(level, constants.MAX_PLAYER_LEVEL)
    return math.floor(level * (level - 1) / 8 + 800 * (2 ** ((level - 1) / 7) - 1))


@lru_cache()
def exp_to_level(exp):
    if exp >= level_to_exp(constants.MAX_PLAYER_LEVEL):
        return constants.MAX_PLAYER_LEVEL
    return bisect(ExpToLevel(), exp) - 1


def level_up_check(userinfo, exp):
    cur_level = exp_to_level(userinfo.player_exp)
    next_level = exp_to_level(userinfo.player_exp + exp)

    is_new_level = cur_level != next_level

    if is_new_level:
        userinfo.vip_exp += vip_exp_per_player_level(next_level)
        userinfo.save()


def product_to_dollar_cost(product_id: str):
    if product_id in [constants.DEAL_DAILY_0]:
        return 0
    elif product_id in [constants.DEAL_DAILY_1, constants.DEAL_WEEKLY_1]:
        return 1
    elif product_id in [constants.DEAL_MONTHLY_1]:
        return 2
    elif product_id in [constants.DEAL_DAILY_2, constants.DEAL_WEEKLY_2, constants.DEAL_MONTHLY_2, constants.GEMS_499, constants.MONTHLY_PASS]:
        return 5
    elif product_id in [constants.GEMS_999, constants.WORLD_PACK_999, constants.DEAL_MONTHLY_3, constants.DEAL_DAILY_3]:
        return 10
    elif product_id in [constants.GEMS_1999, constants.WORLD_PACK_1999, constants.CHAPTER_REWARDS_PACK0, constants.DEAL_MONTHLY_4, constants.DEAL_DAILY_4, constants.DEAL_WEEKLY_3]:
        return 20
    elif product_id in [constants.GEMS_2999]:
        return 30
    elif product_id in [constants.GEMS_4999, constants.DEAL_WEEKLY_4, constants.DEAL_MONTHLY_5, constants.DEAL_MONTHLY_6]:
        return 50
    elif product_id in [constants.GEMS_9999, constants.DEAL_MONTHLY_7]:
        return 100
    else:
        raise Exception("Invalid product_id: " + product_id)


# From these estimates https://afk.guide/afk-arena-vip-ranks/
# $5 for 300 vip exp
def cost_to_vip_exp(dollar_cost):
    return math.floor((dollar_cost / 5) * 300)


# Fixed amounts of vip exp at Player Level thresholds for f2p
# Gets you up to VIP level 10
def vip_exp_per_player_level(player_level):
    exp = 0
    if player_level == 15:
        exp = 50
    if player_level == 30:
        exp = 50
    elif player_level == 35:
        exp = 100
    elif player_level == 40:
        exp = 100
    elif player_level == 45:
        exp = 350
    elif player_level == 50:
        exp = 350
    elif player_level == 55:
        exp = 500
    elif player_level == 60:
        exp = 500
    elif player_level == 65:
        exp = 1000
    elif player_level == 70:
        exp = 1000
    elif player_level == 75:
        exp = 1500
    elif player_level == 80:
        exp = 1500
    elif player_level == 85:
        exp = 1500
    elif player_level == 90:
        exp = 1500
    elif player_level == 95:
        exp = 2000
    elif player_level == 100:
        exp = 2000
    elif player_level == 105:
        exp = 3000
    elif player_level == 110:
        exp = 3000
    elif player_level == 115:
        exp = 5000
    elif player_level == 120:
        exp = 5000
    return exp


def vip_exp_to_level(exp):
    if exp < 100:
        return 0
    elif exp < 300:
        return 1
    elif exp < 1000:
        return 2
    elif exp < 2000:
        return 3
    elif exp < 4000:
        return 4
    elif exp < 7000:
        return 5
    elif exp < 10000:
        return 6
    elif exp < 14000:
        return 7
    elif exp < 20000:
        return 8
    elif exp < 30000:
        return 9
    elif exp < 50000:
        return 10
    elif exp < 80000:
        return 11
    elif exp < 150000:
        return 12
    elif exp < 300000:
        return 13
    elif exp < 500000:
        return 14
    elif exp < 1000000:
        return 15
    elif exp < 2000000:
        return 16
    elif exp < 5000000:
        return 17
    elif exp < 7500000:
        return 18
    elif exp < 10000000:
        return 19
    else:
        return 20


class ExpToLevel:
    def __len__(self):
        return constants.MAX_PLAYER_LEVEL

    def __getitem__(self, level):
        return level_to_exp(level)


def player_exp_reward_quickplay(dungeon_level):
    return min(math.floor((dungeon_level / 25) + (1.17 ** (dungeon_level / 40))), 12000)


def player_exp_reward_dungeon(dungeon_level):
    return min(math.floor((dungeon_level / 3) + (1.23 ** (dungeon_level / 40)) * 8), 350)


def afk_exp_per_min(dungeon_level):
    return 10


#########################
## Dust


# copied from https://afk-arena.fandom.com/wiki/Hero%27s_Essence
# ignoring the first level, since
def char_level_to_dust(level):
    if level < 21:
        return 10
    if level < 41:
        return 50
    if level < 61:
        return 150
    if level < 81:
        return 400
    if level < 101:
        return 900
    if level < 121:
        return 2100
    if level < 141:
        return 5100
    if level < 161:
        return 11100
    if level < 181:
        return 23100
    if level < 201:
        return 48100
    if level < 221:
        return 78100
    return 118100


def afk_dust_per_min(dungeon_level):
    # Dust is capped at world 30, similar to https://afk-arena.fandom.com/wiki/Hero%27s_Essence_AFK_Rewards
    dust_per_min = min(dungeon_level * 0.0016 + 0.01, 1.93)

    if server.is_server_version_higher('1.0.8'):
        # Dust is capped at world 35
        dust_per_min = min(dungeon_level * 0.0016 + 0.01, 2.25)

    return dust_per_min / 2  # Halved for afk rewards


def dust_chest_reward(user, rarity, chest_tier=None):
    if chest_tier is None:
        chest_tier = user.userinfo.tier_rank
    elo = tier_system.get_tier_reward_elo(chest_tier)

    base_mult = 1

    if rarity in [constants.ChestType.SILVER.value, constants.ChestType.DAILY_DUNGEON.value]:
        base_mult = 0.15
    elif rarity == constants.ChestType.GOLD.value:
        base_mult = 0.25
    elif rarity == constants.ChestType.MYTHICAL.value:
        base_mult = 0.3

    return math.floor(elo * base_mult + 10)

#########################
## Gems


def gems_reward_dungeon(dungeon_level, dungeon_type: int):
    if dungeon_type == constants.DungeonType.TOWER.value:
        return 750
    return 0


def gems_chest_reward(rarity):
    mult = 1
    if rarity == constants.ChestType.GOLD.value:
        mult = 3
    elif rarity == constants.ChestType.MYTHICAL.value:
        return 270
    return 20 * mult


#########################
## Prestige

def next_prestige_copies(curr_prestige_level, rarity):
    return constants.PRESTIGE_COPIES_REQUIRED_BY_RARITY[rarity][curr_prestige_level]
