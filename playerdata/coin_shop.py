from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import constants
from playerdata.models import Item, BaseItem
from .inventory import ItemSchema
from .serializers import BuyItemSerializer


# TODO: test cases!
class TryBuyItemView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = BuyItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_item_type = serializer.validated_data['target_item_type']
        base_item = BaseItem.objects.get(item_type=target_item_type)

        # check for unique items
        if base_item.is_unique:
            dup_copies = Item.objects.filter(user=request.user, item_type=base_item)

            if dup_copies:
                return Response({
                    'status': False,
                    'reason': 'already own this item!',
                })

        inventory = request.user.inventory
        if base_item.cost > inventory.coins:
            return Response({'status': False, 'reason': 'not enough coins!'})

        inventory.coins -= base_item.cost
        inventory.save()
        item = Item.objects.create(user=request.user, item_type=base_item)

        return Response({'status': True, 'item': ItemSchema(item).data})

class GetItemsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'item_types': constants.COIN_SHOP_ITEMS})
