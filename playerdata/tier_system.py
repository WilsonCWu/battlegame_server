import math

from playerdata import constants


def elo_to_tier(elo: int):
    if elo < constants.Tiers.MASTER.value * constants.TIER_ELO_INCREMENT:
        return constants.Tiers(math.floor(elo / constants.TIER_ELO_INCREMENT) + 1)
    else:
        return constants.Tiers.MASTER


#  we peg the rewards to the middle elo of each tier
#  Ex: If you're at Bronze 4 (100-199 elo), the rewards are pegged at 150 elo
def get_tier_reward_elo(tier: constants.Tiers):
    return (tier.value * constants.TIER_ELO_INCREMENT) - constants.TIER_ELO_INCREMENT / 2
