from datetime import datetime, timedelta

from playerdata import chests, constants


def get_world_expiration():
    curr_time = datetime.now()
    return curr_time + timedelta(days=2)


# TODO: Tuning & costs
# these rewards are "wrapped", i.e. the rarity of the chest instead of the contents of the chest
def get_world_pack_rewards(user):
    rewards = []
    world = user.worldpack.world
    if world < 6:
        rewards.append(chests.ChestReward(reward_type="chest", value=constants.ChestType.MYTHICAL.value))
        rewards.append(chests.ChestReward(reward_type="gems", value="1200"))
        rewards.append(chests.ChestReward(reward_type="coins", value="50000"))
    else:
        rewards.append(chests.ChestReward(reward_type="chest", value=constants.ChestType.LEGENDARY.value))
        rewards.append(chests.ChestReward(reward_type="chest", value=constants.ChestType.MYTHICAL.value))

    return rewards


def active_new_pack(user, world: int):
    # only have world packs for world > 3 and even number
    if world <= 3 or world % 2 == 1:
        return

    user.worldpack.world = world
    user.worldpack.expiration_date = get_world_expiration()
    user.worldpack.is_claimed = False
    user.worldpack.save()
