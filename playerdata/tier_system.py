from playerdata import constants


def elo_to_tier(elo: int):
    if elo < 250:
        return constants.Tiers.BRONZE_TWO
    elif elo < 500:
        return constants.Tiers.BRONZE_ONE
    elif elo < 750:
        return constants.Tiers.SILVER_TWO
    elif elo < 1000:
        return constants.Tiers.SILVER_ONE
    elif elo < 1300:
        return constants.Tiers.GOLD_TWO
    elif elo < 1600:
        return constants.Tiers.GOLD_ONE
    elif elo < 2000:
        return constants.Tiers.PLAT_TWO
    elif elo < 2300:
        return constants.Tiers.PLAT_ONE
    elif elo < 2600:
        return constants.Tiers.DIAMOND_TWO
    elif elo < 3000:
        return constants.Tiers.DIAMOND_ONE
    else:
        return constants.Tiers.MASTER
