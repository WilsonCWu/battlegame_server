from datetime import datetime, timedelta, timezone

from playerdata import chests, constants
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata.models import WorldPack
from rest_marshmallow import Schema, fields


def get_world_expiration():
    curr_time = datetime.now()
    return curr_time + timedelta(days=3)


class WorldPackIAP:
    def __init__(self, purchase_id, rewards, bonus_value):
        self.purchase_id = purchase_id
        self.bonus_value = bonus_value
        self.rewards = rewards


class WorldPackIAPSchema(Schema):
    purchase_id = fields.Str()
    bonus_value = fields.Int()
    rewards = fields.Nested(chests.ChestRewardSchema, many=True)


# TODO: tune rewards
# these rewards are "wrapped", i.e. the rarity of the chest instead of the contents of the chest
def active_world_packs(user):
    world = user.worldpack.world

    if world <= 1:
        pack_1 = WorldPackIAP(constants.WORLD_PACK_0,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=24),
                       chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=18),
                       chests.ChestReward(reward_type=constants.RewardType.COINS.value, value=35000)],
                              300)
        pack_2 = WorldPackIAP(constants.WORLD_PACK_1,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=6),
                       chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=4),
                       chests.ChestReward(reward_type=constants.RewardType.COINS.value, value=50000)],
                              510)
        pack_3 = WorldPackIAP(constants.WORLD_PACK_2,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=9),
                       chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value),
                       chests.ChestReward(reward_type=constants.RewardType.COINS_FAST_REWARDS.value, value=24)],
                              600)

    elif world < 10:
        gems = (world * 300) + 1500
        coin_hours = 42
        dust_hours = 42

        pack_1 = WorldPackIAP(constants.WORLD_PACK_1,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value),
                       chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems),
                       chests.ChestReward(reward_type=constants.RewardType.COINS_FAST_REWARDS.value, value=coin_hours)],
                              510)
        pack_2 = WorldPackIAP(constants.WORLD_PACK_2,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value),
                       chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems),
                       chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value, value=dust_hours)],
                              510)
        pack_3 = WorldPackIAP(constants.WORLD_PACK_3,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=6),
                       chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=4),
                       chests.ChestReward(reward_type=constants.RewardType.COINS.value, value=25000)],
                              510)

    else:
        dust_hours = 12 + (world // 2) * 2  # starts at 22, +2 every two worlds

        pack_1 = WorldPackIAP(constants.WORLD_PACK_1,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=6),
                       chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value),
                       chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value, value=dust_hours/2)],
                              510)
        pack_2 = WorldPackIAP(constants.WORLD_PACK_2,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.LEGENDARY.value),
                       chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value),
                       chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value, value=dust_hours)],
                              510)
        pack_3 = WorldPackIAP(constants.WORLD_PACK_3,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.LEGENDARY.value),
                       chests.ChestReward(reward_type=constants.RewardType.CHEST.value, value=constants.ChestType.MYTHICAL.value),
                       chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value, value=dust_hours)],
                              470)

    return [pack_1, pack_2, pack_3]


def activate_new_pack(user, world: int):
    user.worldpack.world = world
    user.worldpack.expiration_date = get_world_expiration()
    user.worldpack.save()


def get_purchase_id(world_pack: WorldPack):
    if world_pack.world == 0:
        return constants.WORLD_PACK_1
    elif world_pack.world < 10:
        return constants.WORLD_PACK_2
    else:
        return constants.WORLD_PACK_3


def has_active_world_pack(user):
    cur_time = datetime.now(timezone.utc)
    return cur_time < user.worldpack.expiration_date


class GetWorldPack(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        active_packs = active_world_packs(request.user)

        return Response({'status': True,
                         'world_packs': WorldPackIAPSchema(active_packs, many=True).data,
                         'expiration_time': request.user.worldpack.expiration_date,
                         })
