from datetime import datetime, timedelta

from playerdata import chests, constants


def get_world_expiration():
    curr_time = datetime.now()
    return curr_time + timedelta(days=2)


# TODO: Tuning & costs
def get_world_pack_rewards(user, world: int, purchase_id):
    rewards = []
    if world < 6 and purchase_id == constants.WORLD_PACK_999:
        rewards.extend(chests.generate_chest_rewards(constants.ChestType.MYTHICAL.value, user))
        rewards.append(chests.ChestReward(reward_type="gems", value="1200"))
        rewards.append(chests.ChestReward(reward_type="coins", value="50000"))
    elif purchase_id == constants.WORLD_PACK_1999:
        rewards.extend(chests.generate_chest_rewards(constants.ChestType.LEGENDARY.value, user))
        rewards.extend(chests.generate_chest_rewards(constants.ChestType.MYTHICAL.value, user))
    else:
        raise Exception("Invalid purchase id for world pack: " + purchase_id)

    return rewards


def active_new_pack(user, world: int):
    # only have world packs for world > 3 and even number
    if world <= 3 or world % 2 == 1:
        return

    user.worldpack.world = world
    user.worldpack.expiration_date = get_world_expiration()
    user.worldpack.is_claimed = False
    user.worldpack.save()
