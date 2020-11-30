import random
import json
from datetime import datetime, date, time, timedelta
from collections import namedtuple

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Model
from google.oauth2 import service_account
from googleapiclient.discovery import build

from rest_marshmallow import Schema, fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from battlegame.settings import SERVICE_ACCOUNT_FILE
from playerdata.models import BaseCharacter, Deal, PurchasedTracker, Item
from playerdata.models import InvalidReceipt
from playerdata.models import Character
from playerdata.models import Inventory
from . import constants
from .constants import DealType
from .questupdater import QuestUpdater
from .serializers import PurchaseItemSerializer
from .serializers import PurchaseSerializer
from .serializers import ValidateReceiptSerializer
from .inventory import CharacterSchema, ItemSchema


class PurchaseView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data['purchase_id']

        inventory = Inventory.objects.get(user=request.user)

        if purchase_id == 'com.salutationstudio.tinytitans.gems400':
            inventory.gems += 400
        elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.'):
            return handle_purchase_deal(request.user, purchase_id)
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


def reward_deal(user, inventory, deal):
    inventory.coins += deal.coins
    inventory.gems += deal.gems
    inventory.dust += deal.dust
    inventory.essence += deal.essence

    inventory.save()

    if deal.char_type is not None:
        insert_character(user, deal.char_type)

    if deal.item is not None:
        for i in range(0, deal.item_quantity):
            Item.objects.create(user=user, item_type=deal.item.item_type)


def handle_purchase_deal(user, purchase_id):
    if purchase_id.startswith('com.salutationstudio.tinytitans.deal.daily'):
        deal_type = DealType.DAILY
    else:
        deal_type = DealType.WEEKLY

    order = int(purchase_id[-1])
    curr_time = datetime.now()

    try:
        deal = Deal.objects.get(deal_type=deal_type, order=order, expiration_date__gt=curr_time)
    except Model.DoesNotExist as e:
        return Response({'status': False, 'reason': 'invalid deal id'})

    try:
        PurchasedTracker.objects.create(user=user, deal=deal)
    except IntegrityError as e:
        return Response({'status': False, 'reason': 'already purchased this deal!'})

    reward_deal(user, user.inventory, deal)
    return Response({'status': True})


class DealSchema(Schema):
    id = fields.Int()
    gems = fields.Int()
    coins = fields.Int()
    dust = fields.Int()
    essence = fields.Int()
    item = fields.Nested(ItemSchema)
    item_quantity = fields.Int()
    char_type = fields.Nested(CharacterSchema)
    essence_cost = fields.Int()
    deal_type = fields.Int()
    order = fields.Int()
    expiration = fields.DateTime()

    is_available = fields.Method("get_availability")

    def get_availability(self, deal):
        return PurchasedTracker.objects.filter(user=self.context, deal=deal).first() is None


class GetDeals(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        deal_schema = DealSchema(many=True)
        deal_schema.context = request.user
        curr_time = datetime.now()

        daily_deals = deal_schema.dump(Deal.objects.filter(deal_type=DealType.DAILY.value,
                                                           expiration_date__gt=curr_time).order_by('order'))
        weekly_deals = deal_schema.dump(Deal.objects.filter(deal_type=DealType.WEEKLY.value,
                                                            expiration_date__gt=curr_time).order_by('order'))

        return Response({"daily_deals": daily_deals, 'weekly_deals': weekly_deals})


# returns a random BaseCharacter with weighted
def generate_character(rarity_odds=None):
    if rarity_odds is None:
        rarity_odds = constants.SUMMON_RARITY_BASE
    val = random.randrange(10000) / 100

    for i in range(0, len(rarity_odds)):
        if val <= rarity_odds[i]:
            rarity = len(rarity_odds) - i
            break

    base_chars = BaseCharacter.objects.filter(rarity=rarity, rollable=True)
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


def generate_and_insert_characters(user, char_count, rarity_odds=None):
    new_chars = {}
    # generate char_count random characters
    for i in range(char_count):
        base_char = generate_character(rarity_odds)

        # auto retire common heroes
        if base_char.rarity == 1 and user.inventory.is_auto_retire:
            user.inventory.essence += constants.ESSENCE_PER_COMMON_CHAR_RETIRE
            user.inventory.save()
            continue

        new_char = insert_character(user, base_char)
        if new_char.char_id in new_chars:
            old_char = new_chars[new_char.char_id]
            new_chars[new_char.char_id] = CharacterCount(character=new_char, count=old_char.count + 1)
        else:
            new_chars[new_char.char_id] = CharacterCount(character=new_char, count=1)
    return new_chars


def count_char_copies(chars):
    count = 0
    for char in chars:
        count += char.copies

    return count


class PurchaseItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = PurchaseItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_item_id = serializer.validated_data['purchase_item_id']
        user = request.user

        if purchase_item_id not in constants.SUMMON_GEM_COST:
            return Response({"status": False, "reason": "invalid purchase id " + purchase_item_id})

        # check enough gems
        inventory = Inventory.objects.get(user=user)
        if inventory.gems < constants.SUMMON_GEM_COST[purchase_item_id]:
            return Response({"status": False, "reason": "not enough gems"})

        # deduct gems, update quests
        inventory.gems -= constants.SUMMON_GEM_COST[purchase_item_id]
        inventory.save()
        # TODO: we need to replace this with a summon(.., 10) quest, otherwise
        # we're promoting buying 100 small items just for a quest
        QuestUpdater.add_progress_by_type(request.user, constants.PURCHASE_ITEM,
                                          constants.SUMMON_COUNT[purchase_item_id])

        # generate characters
        new_char_arr = []
        rarity = None
        char_copies = count_char_copies(Character.objects.filter(user=request.user))
        # rig the first two rolls
        if constants.SUMMON_COUNT[purchase_item_id] == 1:
            if char_copies == 3:
                # rarity 2
                rarity = [-1, -1, 100, 100]
            elif char_copies == 4:
                # rarity 3
                rarity = [-1, 100, 100, 100]

        new_chars = generate_and_insert_characters(user, constants.SUMMON_COUNT[purchase_item_id], rarity)

        # convert to a serialized form
        for char_id, char_count in new_chars.items():
            new_char_arr.append({"count": char_count.count, "character": CharacterSchema(char_count.character).data})

        return Response({"status": True, "characters": new_char_arr})
