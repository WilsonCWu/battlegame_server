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
    return math.floor(dungeon_level / 3 * 50 + (dungeon_level - 1) ** 2 + 500)


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
