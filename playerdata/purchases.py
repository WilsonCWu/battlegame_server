import random

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata.models import BaseCharacter
from playerdata.models import Character
from playerdata.models import Inventory
from . import constants
from .questupdater import QuestUpdater
from .serializers import PurchaseItemSerializer
from .serializers import PurchaseSerializer


# TODO: verify these purchases serverside
class PurchaseView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data['purchase_id']

        inventory = Inventory.objects.get(user=request.user)

        if purchase_id == 'com.battlegame.gems300':
            inventory.gems += 300
        else:
            return Response({'status': False, 'reason': 'invalid id ' + purchase_id})

        inventory.save()
        return Response({'status': True})


# returns a random BaseCharacter with weighted rarity
def generate_character(rarity_odds=None):
    if rarity_odds is None:
        rarity_odds = [5, 15, 30, 100]
    val = random.randrange(10000) / 100

    for i in range(0, len(rarity_odds)):
        if val <= rarity_odds[i]:
            rarity = len(rarity_odds) - i
            break

    base_chars = BaseCharacter.objects.filter(rarity=rarity)
    num_chars = base_chars.count()
    chosen_char = base_chars[random.randrange(num_chars)]
    return chosen_char


def insert_character(user, chosen_char):
    old_char = Character.objects.filter(user=user, char_type=chosen_char).first()

    if old_char:
        old_char.copies += 1
        old_char.save()
        return

    Character.objects.create(user=user, char_type=chosen_char)
    QuestUpdater.add_progress_by_type(user, constants.OWN_HEROES, 1)


class PurchaseItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = PurchaseItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_item_id = serializer.validated_data['purchase_item_id']

        if purchase_item_id == "chars10":
            user = request.user

            # check enough gems
            inventory = Inventory.objects.get(user=user)
            if inventory.gems < 1000:
                return Response({"status": 1, "reason": "not enough gems"})

            inventory.gems -= 1000
            inventory.save()
            QuestUpdater.add_progress_by_type(request.user, constants.PURCHASE_ITEM, 1)

            newCharTypes = []

            for i in range(0, 10):
                newChar = generate_character()
                insert_character(user, newChar)
                newCharTypes.append(newChar.char_type)

            return Response({"status": 0, "characters": newCharTypes})
