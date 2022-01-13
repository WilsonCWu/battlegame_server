import random
from datetime import date, datetime, timezone, time, timedelta

from django.db import transaction
from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import chests, constants
from playerdata.models import BaseResourceShopItem, ResourceShop, BaseItem
from playerdata.serializers import IntSerializer


class ResourceShopItemSchema(Schema):
    id = fields.Int()
    cost_type = fields.Str()
    cost_value = fields.Int()
    reward_type = fields.Str()
    reward_value = fields.Int()


def reset_resource_shop():
    with atomic():
        ResourceShop.objects.update(purchased_items=[])

    # Update new items
    BaseResourceShopItem.objects.filter(reward_type=constants.RewardType.ITEM_ID.value).delete()
    epic_items = BaseItem.objects.filter(rarity=2, rollable=True)
    sample_items = random.sample(epic_items, 4)

    item_cost = 2150000
    for item in sample_items:
        BaseResourceShopItem.objects.create(reward_type=constants.RewardType.ITEM_ID.value,
                                            reward_value=item.item_id,
                                            cost_type=constants.ResourceShopCostType.GOLD.value,
                                            cost_value=item_cost)
        item_cost += 50000  # slight variation in price so they aren't totally equally comparable


# daily reset
def resource_shop_reset():
    return datetime.combine(date.today(), time(tzinfo=timezone.utc)) + timedelta(days=1)


class GetResourceShopView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        resource_shop, _ = ResourceShop.objects.get_or_create(user=request.user)
        shop_items = BaseResourceShopItem.objects.exclude(id__in=resource_shop.purchased_items)
        return Response({'status': True,
                         'shop_items': ResourceShopItemSchema(shop_items, many=True).data,
                         'reset_time': resource_shop_reset()
                         })


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

        if base_shop_item.cost_type == constants.ResourceShopCostType.GOLD.value:
            attr_name = "coins"
        else:
            attr_name = "gems"

        existing_amount = getattr(request.user.inventory, attr_name)
        if existing_amount < base_shop_item.cost_value:
            return Response({'status': False, 'reason': f'not enough ${attr_name} to purchase'})

        existing_amount -= base_shop_item.cost_value
        setattr(request.user.inventory, attr_name, existing_amount)
        request.user.inventory.save()

        chests.award_chest_rewards(request.user, [chests.ChestReward(reward_type=base_shop_item.reward_type, value=base_shop_item.reward_value)])

        resource_shop.purchased_items.append(shop_item_id)
        resource_shop.save()

        return Response({'status': True})
