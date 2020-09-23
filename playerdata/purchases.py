import random
import json
from collections import namedtuple
from google.oauth2 import service_account
from googleapiclient.discovery import build

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from battlegame.settings import SERVICE_ACCOUNT_FILE
from playerdata.models import BaseCharacter
from playerdata.models import InvalidReceipt
from playerdata.models import Character
from playerdata.models import Inventory
from . import constants
from .questupdater import QuestUpdater
from .serializers import PurchaseItemSerializer
from .serializers import PurchaseSerializer
from .serializers import ValidateReceiptSerializer
from .inventory import CharacterSchema


class PurchaseView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data['purchase_id']

        inventory = Inventory.objects.get(user=request.user)

        if purchase_id == 'com.salutationstudio.tinyheroes.gems400':
            inventory.gems += 400
        else:
            return Response({'status': False, 'reason': 'invalid id ' + purchase_id})

        inventory.save()
        return Response({'status': True})


class ValidateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValidateReceiptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = serializer.validated_data['store']
        receipt = serializer.validated_data['receipt']

        if store == 0:  # Apple
            return validate_apple(request, receipt)
        elif store == 1:
            return validate_google(request, receipt)


def validate_google(request, receipt_raw):
    SCOPES = ['https://www.googleapis.com/auth/androidpublisher']

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    payload = json.loads(receipt_raw)['Payload']
    json_payload = json.loads(payload)['json']
    receipt = json.loads(json_payload)

    service = build('androidpublisher', 'v3', credentials=credentials)

    try:
        response = service.purchases().products().get(packageName=receipt['packageName'],
                                                      productId=receipt['productId'],
                                                      token=receipt['purchaseToken']).execute()

        return Response({'status': True})
    except Exception:
        InvalidReceipt.objects.create(user=request.user, order_number=receipt['orderId'],
                                      date=receipt['purchaseTime'], product_id=receipt['productId'])
        return Response({'status': False})


def validate_apple(request, receipt_raw):
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
        return old_char

    new_char = Character.objects.create(user=user, char_type=chosen_char)
    QuestUpdater.add_progress_by_type(user, constants.OWN_HEROES, 1)
    return new_char

CharacterCount = namedtuple("CharacterCount", "character count")

def generate_and_insert_characters(user, char_count):
    new_chars = {}
    # generate char_count random characters
    for i in range(char_count):
        base_char = generate_character()
        new_char = insert_character(user, base_char)
        if new_char.char_id in new_chars:
            old_char = new_chars[new_char.char_id]
            new_chars[new_char.char_id] = CharacterCount(character = new_char, count = old_char.count+1)
        else:
            new_chars[new_char.char_id] = CharacterCount(character = new_char, count = 1)
    return new_chars

class PurchaseItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = PurchaseItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_item_id = serializer.validated_data['purchase_item_id']
        user = request.user

        if purchase_item_id not in constants.SUMMON_GEM_COST:
            return Response({"status": 1, "reason": "invalid purchase id " + purchase_item_id})

        # check enough gems
        inventory = Inventory.objects.get(user=user)
        if inventory.gems < constants.SUMMON_GEM_COST[purchase_item_id]:
            return Response({"status": 1, "reason": "not enough gems"})

        #deduct gems, update quests
        inventory.gems -= constants.SUMMON_GEM_COST[purchase_item_id]
        inventory.save()
        # TODO: we need to replace this with a summon(.., 10) quest, otherwise
        # we're promoting buying 100 small items just for a quest
        QuestUpdater.add_progress_by_type(request.user, constants.PURCHASE_ITEM, constants.SUMMON_COUNT[purchase_item_id])

        #generate characters
        new_char_arr = []
        new_chars = generate_and_insert_characters(user, constants.SUMMON_COUNT[purchase_item_id])

        # convert to a serialized form
        for char_id, char_count in new_chars.items():
            new_char_arr.append({"count":char_count.count, "character":CharacterSchema(char_count.character).data})

        return Response({"status": 0, "characters": new_char_arr})
