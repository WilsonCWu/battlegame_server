import math

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


#########################
## EXP

# Level to exp: L(L-1)/8 + 800(2^(L-1)/7 - 1)
# simplified version of Runespace's exp formula [See the Scaling spreadsheet for details]
def level_to_exp(level):
    level = min(level, constants.MAX_PLAYER_LEVEL)
    return math.floor(level * (level - 1) / 8 + 800 * (2 ** ((level - 1) / 7) - 1))


@lru_cache()
def exp_to_level(exp):
    return bisect_func(level_to_exp, exp)


# Daniel's better bisect that takes a function instead of a list
# https://github.com/python/cpython/blob/3.9/Lib/bisect.py
def bisect_func(func, x, lo=1, hi=None):
    """
    func(x) => y
    Given y, returns x where f(x) <= y
    """

    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = constants.MAX_PLAYER_LEVEL  # max level
    if x >= func(hi):
        return hi

    while lo < hi - 1:
        mid = (lo + hi) // 2
        if x < func(mid):
            hi = mid
        else:
            lo = mid
    return lo


def player_exp_reward_quickplay(dungeon_level):
    return math.floor((dungeon_level / 5) * 6) + 6
