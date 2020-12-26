import math
from bisect import bisect

from functools import lru_cache

from playerdata import constants

"""
Scaling Formulas
"""


#########################
## Coins


# FLOOR((level / 3) * 50 + ((level-1)^2))+ 500
def coins_reward_quickplay(dungeon_level):
    return math.floor(dungeon_level / 3 * 50 + (dungeon_level - 1) ** 2 + 500)


# FLOOR((level / 3) * 50 + ((level-1)^2))+ 500
def coins_reward_dungeon(dungeon_level):
    # more on a boss level
    if dungeon_level % 20 == 0:
        return dungeon_level * 1000
    return math.floor(dungeon_level / 3 * 50 + (dungeon_level - 1) ** 2 + 500)


def afk_coins_per_min(dungeon_level):
    return (dungeon_level - 1) / 120 + ((dungeon_level - 1) ** 1.8) / 10


def char_level_to_coins(level):
    return math.floor((level - 1) * 50 + ((level - 1) ** 3.6) / 10)


def coins_chest_reward(elo, rarity):
    elo += 20  # light pad on elo for 0 elo case
    base_mult = 50 + (rarity * 5)
    base_exp = 1.9 + (rarity * 0.1)
    return math.floor(elo / 3 * base_mult + (elo ** base_exp) / 10)


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


class ExpToLevel:
    def __len__(self):
        return constants.MAX_PLAYER_LEVEL

    def __getitem__(self, level):
        return level_to_exp(level)


def player_exp_reward_quickplay(dungeon_level):
    return math.floor((dungeon_level / 5) * 6) + 6


def player_exp_reward_dungeon(dungeon_level):
    return math.floor((dungeon_level / 5) * 9) + 10


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
    return (dungeon_level - 1) * 0.001 + ((dungeon_level - 1) ** 0.45) / 10


def dust_chest_reward(elo, rarity):
    elo += 20  # light pad on elo for 0 elo case
    base_mult = 0.5 + (rarity * 0.5)
    return math.floor(elo * base_mult + (elo ** 1.15) / 10)

#########################
## Gems


def gems_reward_dungeon(dungeon_level):
    if dungeon_level % 5 == 0:
        return 100
    return 0


def gems_chest_reward(rarity):
    mult = 1
    if rarity == constants.ChestType.GOLD.value:
        mult = 3
    return 20 * mult


#########################
## Prestige

def next_prestige_copies(curr_prestige_level):
    return constants.PRESTIGE_COPIES_REQUIRED[curr_prestige_level]
