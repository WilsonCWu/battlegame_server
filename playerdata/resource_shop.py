from datetime import date, datetime, timezone, time, timedelta

from django.db import transaction
from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import chests, constants, formulas
from playerdata.models import BaseResourceShopItem, ResourceShop, BaseItem
from playerdata.questupdater import QuestUpdater
from playerdata.serializers import IntSerializer


class ResourceShopItemSchema(Schema):
    id = fields.Int()
    cost_type = fields.Str()
    cost_value = fields.Int()
    reward_type = fields.Str()
    reward_value = fields.Int()


def reset_resource_shop():
    with atomic():
        ResourceShop.objects.update(purchased_items=[], refreshes_left=constants.RESOURCE_SHOP_DEFAULT_REFRESHES)

    # Update new items
    BaseResourceShopItem.objects.filter(reward_type=constants.RewardType.ITEM_ID.value).delete()
    rare_items = BaseItem.objects.filter(rarity=1, rollable=True, is_unique=False).order_by('?')
    epic_items = BaseItem.objects.filter(rarity=2, rollable=True, is_unique=False).order_by('?')

    # Pick 3 rare and 4 epic items
    sample_rare_items = rare_items[:3]
    sample_epic_items = epic_items[:4]

    shop_items = (sample_rare_items | sample_epic_items).order_by('rarity')  # union doesn't necessarily keep order

    rare_cost = 250000
    epic_cost = 2100000
    for item in shop_items:
        item_cost = rare_cost if item.rarity == 1 else epic_cost
        BaseResourceShopItem.objects.create(reward_type=constants.RewardType.ITEM_ID.value,
                                            reward_value=item.item_type,
                                            cost_type=constants.RewardType.COINS.value,
                                            cost_value=item_cost)


# daily reset
def resource_shop_reset():
    return datetime.combine(date.today(), time()) + timedelta(days=1)


class GetResourceShopView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        resource_shop, _ = ResourceShop.objects.get_or_create(user=request.user)
        shop_items = BaseResourceShopItem.objects.all().order_by('reward_type', 'id')

        # dynamically change the dust and gold costs based on dungeon progress
        for item in shop_items:
            if item.cost_type == constants.RewardType.COINS.value and item.reward_type == constants.RewardType.DUST.value:
                item.cost_value = resource_shop_coins_cost_for_dust(request.user.dungeonprogress.campaign_stage)

            if item.reward_type == constants.RewardType.DUST.value:
                item.reward_value = resource_shop_dust_reward(request.user.dungeonprogress.campaign_stage)

        return Response({'status': True,
                         'shop_items': ResourceShopItemSchema(shop_items, many=True).data,
                         'reset_time': resource_shop_reset(),
                         'purchased_items': resource_shop.purchased_items,
                         'refreshes_left': resource_shop.refreshes_left
                         })


# increase by 50 dust every 60 stages, capped at 500
def resource_shop_dust_reward(dungeon_stage: int):
    MAX_SHOP_DUST = 500
    dust_multiple = 50
    return min((dungeon_stage // 60) * dust_multiple, MAX_SHOP_DUST)


def resource_shop_coins_cost_for_dust(dungeon_stage: int):
    afk_gold = formulas.afk_coins_per_min(dungeon_stage) * 60 * 24
    gold_multiple = 1.2
    return min(afk_gold * gold_multiple, 2250000)  # cap at 2.25M


class BuyResourceShopItemView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop_item_id = serializer.validated_data['value']

        resource_shop, _ = ResourceShop.objects.get_or_create(user=request.user)

        if shop_item_id in resource_shop.purchased_items:
            return Response({'status': False, 'reason': 'already purchased!'})

        base_shop_item = BaseResourceShopItem.objects.filter(id=shop_item_id).first()
        if base_shop_item is None:
            return Response({'status': False, 'reason': f'shop_item_id does not exist: ${shop_item_id}'})

        if base_shop_item.cost_type == constants.RewardType.COINS.value and base_shop_item.reward_type == constants.RewardType.DUST.value:
            base_shop_item.cost_value = resource_shop_coins_cost_for_dust(request.user.dungeonprogress.campaign_stage)

        if base_shop_item.reward_type == constants.RewardType.DUST.value:
            base_shop_item.reward_value = resource_shop_dust_reward(request.user.dungeonprogress.campaign_stage)

        existing_amount = getattr(request.user.inventory, base_shop_item.cost_type)
        if existing_amount < base_shop_item.cost_value:
            return Response({'status': False, 'reason': f'not enough ${base_shop_item.cost_type} to purchase'})

        existing_amount -= base_shop_item.cost_value
        setattr(request.user.inventory, base_shop_item.cost_type, existing_amount)
        request.user.inventory.save()

        chests.award_chest_rewards(request.user, [chests.ChestReward(reward_type=base_shop_item.reward_type, value=base_shop_item.reward_value)])

        resource_shop.purchased_items.append(shop_item_id)
        resource_shop.save()

        QuestUpdater.add_progress_by_type(request.user, constants.PURCHASE_ITEM, 1)

        return Response({'status': True})


def refresh_resource_shop_cost():
    return 100  # Gems


class RefreshResourceShopView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        resource_shop, _ = ResourceShop.objects.get_or_create(user=request.user)
        if resource_shop.refreshes_left == 0:
            return Response({'status': False, 'reason': 'no more shop refreshes for today'})

        if request.user.inventory.gems < refresh_resource_shop_cost():
            return Response({'status': False, 'reason': 'not enough gems to refresh shop'})

        request.user.inventory.gems -= refresh_resource_shop_cost()
        request.user.inventory.save()

        resource_shop.purchased_items = []
        resource_shop.refreshes_left -= 1
        resource_shop.save()

        return Response({'status': True})
