import random
from datetime import datetime, timedelta, timezone

from playerdata import chests, constants, server
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata.models import WorldPack, BaseCharacter
from rest_marshmallow import Schema, fields


def get_world_expiration():
    curr_time = datetime.now()
    return curr_time + timedelta(days=3)


class WorldPackIAP:
    def __init__(self, world: int, purchase_id: str, rewards, bonus_value):
        self.world = world
        self.purchase_id = purchase_id
        self.bonus_value = bonus_value
        self.rewards = rewards

    def unique_worldpack_id(self) -> str:
        return str(self.world) + "," + self.purchase_id


class WorldPackIAPSchema(Schema):
    purchase_id = fields.Str()
    bonus_value = fields.Int()
    rewards = fields.Nested(chests.ChestRewardSchema, many=True)


def get_world_pack_by_id(user, purchase_id):
    packs = get_world_packs(user)

    for pack in packs:
        if pack.purchase_id == purchase_id:
            return pack

    return None


# these rewards are "wrapped", i.e. the rarity of the chest instead of the contents of the chest
def get_world_packs(user):
    world = user.worldpack.world
    rng = random.Random(world)
    legendary_list = list(BaseCharacter.objects.filter(rarity=4, rollable=True).values_list('char_type', flat=True))
    leg_char_id = rng.choice(legendary_list)

    if world <= 1:
        pack_1 = WorldPackIAP(world, constants.WORLD_PACK_0,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=24),
                               chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=18),
                               chests.ChestReward(reward_type=constants.RewardType.COINS.value, value=35000)],
                              422)
        pack_2 = WorldPackIAP(world, constants.WORLD_PACK_1,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=6),
                               chests.ChestReward(reward_type=constants.RewardType.CHEST.value,
                                                  value=constants.ChestType.MYTHICAL.value),
                               chests.ChestReward(reward_type=constants.RewardType.COINS.value, value=60000)],
                              809)
        pack_3 = WorldPackIAP(world, constants.WORLD_PACK_2,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=9),
                               chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=4),
                               chests.ChestReward(reward_type=constants.RewardType.COINS_FAST_REWARDS.value, value=24)],
                              436)

    elif world < 10:
        gems1 = (world * 40) + 500
        coin_hours = 24
        dust_hours = 24

        pack_1 = WorldPackIAP(world, constants.WORLD_PACK_1,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value,
                                                  value=constants.ChestType.MYTHICAL.value),
                               chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems1),
                               chests.ChestReward(reward_type=constants.RewardType.COINS_FAST_REWARDS.value,
                                                  value=coin_hours)],
                              213)
        pack_2 = WorldPackIAP(world, constants.WORLD_PACK_2,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value,
                                                  value=constants.ChestType.MYTHICAL.value),
                               chests.ChestReward(reward_type=constants.RewardType.EPIC_SHARDS.value, value=320),
                               chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value,
                                                  value=dust_hours // 2)],
                              300)
        pack_3 = WorldPackIAP(world, constants.WORLD_PACK_3,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=leg_char_id),
                               chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value,
                                                  value=dust_hours),
                               chests.ChestReward(reward_type=constants.RewardType.CHEST.value,
                                                  value=constants.ChestType.MYTHICAL.value)],
                              459)

    else:
        dust_hours = 12 + (world // 2) * 2  # starts at 22, +2 every two worlds
        gems1 = (world * 30) + 2300
        gems2 = (world * 40) + 7500
        gems3 = (world * 40) + 15000

        pack_1 = WorldPackIAP(world, constants.WORLD_PACK_2,
                              [chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems1),
                               chests.ChestReward(reward_type=constants.RewardType.CHEST.value,
                                                  value=constants.ChestType.MYTHICAL.value),
                               chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value,
                                                  value=dust_hours // 2)],
                              175)
        pack_2 = WorldPackIAP(world, constants.WORLD_PACK_3,
                              [chests.ChestReward(reward_type=constants.RewardType.CHEST.value,
                                                  value=constants.ChestType.LEGENDARY.value),
                               chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems2),
                               chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value,
                                                  value=dust_hours)],
                              246)
        pack_3 = WorldPackIAP(world, constants.WORLD_PACK_4,
                              [chests.ChestReward(reward_type=constants.RewardType.CHAR_ID.value, value=leg_char_id),
                               chests.ChestReward(reward_type=constants.RewardType.GEMS.value, value=gems3),
                               chests.ChestReward(reward_type=constants.RewardType.DUST_FAST_REWARDS.value,
                                                  value=dust_hours)],
                              315)

    return [pack_1, pack_2, pack_3]


def get_active_unpurchased_packs(user):
    cur_time = datetime.now(timezone.utc)
    if cur_time >= user.worldpack.expiration_date:
        return []

    active_packs = get_world_packs(user)
    unpurchased_packs = [pack for pack in active_packs if
                         pack.unique_worldpack_id() not in user.worldpack.purchased_packs]

    return unpurchased_packs


def activate_new_pack(user, world: int):
    if world > 1 and not server.is_server_version_higher('1.1.1'):
        return

    user.worldpack.world = world
    user.worldpack.expiration_date = get_world_expiration()
    user.worldpack.save()


def show_world_pack_popup(user):
    unpurchased_packs = get_active_unpurchased_packs(user)
    return len(unpurchased_packs) == 3  # show only when no pack has been purchased


class GetWorldPack(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        unpurchased_packs = get_active_unpurchased_packs(request.user)

        return Response({'status': True,
                         'world_packs': WorldPackIAPSchema(unpurchased_packs, many=True).data,
                         'expiration_time': request.user.worldpack.expiration_date,
                         })
