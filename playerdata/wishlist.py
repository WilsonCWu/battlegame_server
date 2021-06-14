from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import base
from .models import Character
from .serializers import SlotSerializer

NUM_SLOTS_PER_RARITY = [0, 0, 2, 2, 1]


class WishlistSchema(Schema):
    legendaries = fields.List(fields.Int())
    epics = fields.List(fields.Int())
    rares = fields.List(fields.Int())


def init_wishlist(user):
    user_chars = Character.objects.filter(user=user).select_related('char_type')
    user_legendaries = [char.char_type.char_type for char in user_chars if char.char_type.rarity == 4]
    user_epics = [char.char_type.char_type for char in user_chars if char.char_type.rarity == 3]
    user_rares = [char.char_type.char_type for char in user_chars if char.char_type.rarity == 2]

    user.wishlist.legendaries = user_legendaries[:1]
    user.wishlist.epics = user_epics[:2]
    user.wishlist.rares = user_rares[:2]

    user.wishlist.is_active = True
    user.wishlist.save()


class GetWishlistView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        wishlist = WishlistSchema(request.user.wishlist)
        return Response(wishlist.data)


class SetWishlistSlotView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = SlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['slot_id']
        char_type = serializer.validated_data['char_id']  # In this case it's char_type not char_id

        rarity = base.get_char_rarity(char_type)

        if slot_id < 0 or slot_id >= NUM_SLOTS_PER_RARITY[rarity]:
            return Response({'status': False, 'reason': 'invalid slot_id'})

        if rarity == 2:
            wishlist = request.user.wishlist.rares
        elif rarity == 3:
            wishlist = request.user.wishlist.epics
        elif rarity == 4:
            wishlist = request.user.wishlist.legendaries
        else:
            return Response({'status': False, 'reason': 'invalid char_type rarity'})

        if char_type in wishlist:
            return Response({'status': False, 'reason': 'char already in wishlist'})

        wishlist[slot_id] = char_type
        request.user.wishlist.save()

        return Response({'status': True})
