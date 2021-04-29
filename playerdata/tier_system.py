import math

from playerdata import constants


def elo_to_tier(elo: int):
    division_increment = 100
    if elo < constants.Tiers.MASTER.value * 100:
        return constants.Tiers(math.floor(elo / division_increment) + 1)
    else:
        return constants.Tiers.MASTER
