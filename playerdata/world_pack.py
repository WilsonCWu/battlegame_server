from datetime import datetime, timedelta

from playerdata import chests, constants
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata.models import WorldPack


def get_world_expiration():
    curr_time = datetime.now()
    return curr_time + timedelta(days=3)


# these rewards are "wrapped", i.e. the rarity of the chest instead of the contents of the chest
def get_world_pack_rewards(user):
    rewards = []
    world = user.worldpack.world
    if world < 10:
        gems = (world * 300) + 1500
        coins = (world * 30000) + 25000

        rewards.append(chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value))
        rewards.append(chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems))
        rewards.append(chests.ChestReward(reward_type=constants.RewardType.COINS.value, value=coins))
    else:
        dust_hours = 12 + (world // 2) * 2  # starts at 22, +2 every two worlds
        rewards.append(chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.LEGENDARY.value))
        rewards.append(chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value))
        rewards.append(chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value, value=dust_hours))

    return rewards


def active_new_pack(user, world: int):
    user.worldpack.world = world
    user.worldpack.expiration_date = get_world_expiration()
    user.worldpack.is_claimed = False
    user.worldpack.save()


def get_purchase_id(world_pack: WorldPack):
    if world_pack.world == 0:
        return constants.WORLD_PACK_1
    elif world_pack.world < 10:
        return constants.WORLD_PACK_2
    else:
        return constants.WORLD_PACK_3


class GetWorldPack(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        active_pack = get_world_pack_rewards(request.user)

        return Response({'status': True,
                         'world_pack': chests.ChestRewardSchema(active_pack, many=True).data,
                         'expiration_time': request.user.worldpack.expiration_date,
                         'purchase_id': get_purchase_id(request.user.worldpack)
                         })
