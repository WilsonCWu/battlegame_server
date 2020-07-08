from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from django.utils import timezone

from playerdata.models import Item
from playerdata.models import BaseCode
from playerdata.models import ClaimedCode

from .purchases import insert_character

from .serializers import RedeemCodeSerializer


class RedeemCodeSchema(Schema):
    id = fields.Int()
    code = fields.Str()
    gems = fields.Int()
    coins = fields.Int()
    items = fields.List(fields.Int())
    item_amount = fields.List(fields.Int())
    char_id = fields.Int(attribute='char_type.char_type')
    char_description = fields.Str(attribute='char_type.name')  # Replace with actual description


def award_code(user, base_code):
    user.inventory.coins += base_code.coins
    user.inventory.gems += base_code.gems

    items_list = []
    if base_code.items:
        for item, quantity in zip(base_code.items, base_code.item_amount):
            # if item is not owned already
            existing_item = Item.objects.filter(user=user, item_type_id=item).first()
            if existing_item is None:
                items_list.append(Item(user=user, item_type_id=item, copies=quantity))
            else:
                existing_item.copies += quantity
                existing_item.save()

    Item.objects.bulk_create(items_list)

    if base_code.char_type:
        insert_character(user, base_code.char_type)

    if base_code.num_left is not -1:
        base_code.num_left -= 1
        base_code.save()

    user.inventory.save()


def is_valid_code(base_code):
    curr_time = timezone.now()
    # check expiration and amount left
    return base_code.start_time < curr_time < base_code.end_time and (base_code.num_left > 0 or base_code.num_left is -1)


class RedeemCodeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = RedeemCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']

        if ClaimedCode.objects.filter(user=request.user, code__code=code).exists():
            return Response({'status': False, 'reason': 'code has been redeemed already'})

        base_code = BaseCode.objects.filter(code=code).first()
        if base_code is None:
            return Response({'status': False, 'reason': 'invalid redemption code'})

        if not is_valid_code(base_code):
            return Response({'status': False, 'reason': 'code has expired'})

        award_code(request.user, base_code)
        ClaimedCode.objects.create(user=request.user, code=base_code)
        redeem_code_schema = RedeemCodeSchema(base_code)
        return Response(redeem_code_schema.data)
