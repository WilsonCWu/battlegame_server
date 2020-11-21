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
    return math.floor((dungeon_level - 1) * 2 + ((dungeon_level - 1) ** 1.8) / 10)


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


def char_level_to_exp(level):
    return math.floor((level - 1) * 50 + ((level - 1) ** 3.6) / 10)


def player_exp_reward_quickplay(dungeon_level):
    return math.floor((dungeon_level / 5) * 6) + 6


def player_exp_reward_dungeon(dungeon_level):
    return math.floor((dungeon_level / 5) * 9) + 10


def afk_exp_per_min(dungeon_level):
    return 10


#########################
## Dust


# copied from https://afk-arena.fandom.com/wiki/Hero%27s_Essence
def char_level_to_dust(level):
    if level == 1:
        return 10
    if level < 20:
        return 50
    if level < 40:
        return 150
    if level < 60:
        return 350
    if level < 80:
        return 850
    if level < 100:
        return 2050
    if level < 120:
        return 5050
    if level < 140:
        return 11050
    if level < 160:
        return 23050
    return 0


#########################
## Gems

def gems_reward_dungeon(dungeon_level):
    if dungeon_level % 5 == 0:
        return 2000
    return 100


def afk_gems_per_min(dungeon_level):
    return (dungeon_level - 1) * 0.0015 + ((dungeon_level - 1) ** 0.2) / 10
