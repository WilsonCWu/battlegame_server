from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import base, server
from .models import Character
from .serializers import SlotSerializer

NUM_SLOTS_PER_RARITY = [0, 0, 1, 2, 1]


class WishlistSchema(Schema):
    legendaries = fields.List(fields.Int())
    epics = fields.List(fields.Int())
    rares = fields.List(fields.Int())
    is_active = fields.Bool()


def init_wishlist(user):
    if user.wishlist.is_active:
        return

    user.wishlist.legendaries = NUM_SLOTS_PER_RARITY[4] * [-1]
    user.wishlist.epics = NUM_SLOTS_PER_RARITY[3] * [-1]
    user.wishlist.rares = NUM_SLOTS_PER_RARITY[2] * [-1]

    user.wishlist.is_active = True
    user.wishlist.save()


class GetWishlistView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        wishlist = WishlistSchema(request.user.wishlist)
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'wishlist': wishlist.data})
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
