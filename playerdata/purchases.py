import random
import json
from datetime import datetime, timezone
from collections import namedtuple

from django.db import IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
from google.oauth2 import service_account
from googleapiclient.discovery import build

from rest_marshmallow import Schema, fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from battlegame.settings import SERVICE_ACCOUNT_FILE
from playerdata.models import BaseCharacter, PurchasedTracker, Item, ActiveDeal, BaseItem, BaseDeal, get_expiration_date
from playerdata.models import InvalidReceipt
from playerdata.models import Character
from playerdata.models import Inventory
from . import constants
from .base import BaseItemSchema, BaseCharacterSchema
from .constants import DealType
from .questupdater import QuestUpdater
from .serializers import PurchaseItemSerializer
from .serializers import PurchaseSerializer
from .serializers import ValidateReceiptSerializer
from .inventory import CharacterSchema


class PurchaseView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data['purchase_id']
        transaction_id = serializer.validated_data['transaction_id']

        if purchase_id.startswith('com.salutationstudio.tinytitans.gems.'):
            return handle_purchase_gems(request.user, purchase_id, transaction_id)
        elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.'):
            return handle_purchase_deal(request.user, purchase_id, transaction_id)
        else:
            return Response({'status': False, 'reason': 'invalid id ' + purchase_id})


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

        PurchasedTracker.objects.create(user=request.user,
                                        transaction_id=receipt['orderId'])
        return Response({'status': True})
    except Exception:
        InvalidReceipt.objects.create(user=request.user, order_number=receipt['orderId'],
                                      date=receipt['purchaseTime'], product_id=receipt['productId'])
        return Response({'status': False})


def validate_apple(request, receipt_raw):
    return Response({'status': True})


def handle_purchase_gems(user, purchase_id, transaction_id):
    purchase_tracker = PurchasedTracker.objects.filter(user=user, transaction_id=transaction_id).first()
    if purchase_tracker is None:
        return Response({'status': False, 'reason': 'purchase not found in our records'})

    if purchase_id in constants.IAP_GEMS_AMOUNT:
        user.inventory.gems += constants.IAP_GEMS_AMOUNT[purchase_id]
    else:
        return Response({'status': False, 'reason': 'invalid purchase_id ' + purchase_id})

    user.inventory.save()

    purchase_tracker.purchase_id = purchase_id
    purchase_tracker.save()
    return Response({'status': True})


def reward_deal(user, inventory, base_deal):
    if base_deal.deal_type == constants.DealType.GEMS_COST.value:
        inventory.gems -= base_deal.gems_cost

    inventory.coins += base_deal.coins
    inventory.gems += base_deal.gems
    inventory.dust += base_deal.dust

    inventory.save()

    if base_deal.char_type is not None:
        insert_character(user, base_deal.char_type.char_type)

    if base_deal.item is not None:
        for i in range(0, base_deal.item_quantity):
            Item.objects.create(user=user, item_type=base_deal.item.item_type)


def handle_purchase_deal(user, purchase_id, transaction_id):
    if purchase_id.startswith('com.salutationstudio.tinytitans.deal.daily'):
        deal_type = DealType.DAILY.value
    elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.weekly'):
        deal_type = DealType.WEEKLY.value
    else:
        deal_type = DealType.GEMS_COST.value

    order = int(purchase_id[-1])
    curr_time = datetime.now(timezone.utc)

    try:
        deal = ActiveDeal.objects.get(base_deal__deal_type=deal_type, base_deal__order=order,
                                      expiration_date__gt=curr_time)
    except ObjectDoesNotExist:
        return Response({'status': False, 'reason': 'invalid deal id'})

    # check if Purchase was recorded from validate/ (don't check if it was the free daily deal)
    purchase_tracker = PurchasedTracker.objects.filter(user=user, transaction_id=transaction_id).first()
    if purchase_id == constants.DEAL_DAILY_0:
        purchase_tracker = PurchasedTracker.objects.create(user=user)
    elif purchase_tracker is None:
        return Response({'status': False, 'reason': 'purchase not found in our records'})

    try:
        purchase_tracker.deal = deal
        purchase_tracker.purchase_id = purchase_id
        purchase_tracker.save()
    except IntegrityError as e:
        return Response({'status': False, 'reason': 'already purchased this deal!'})

    if user.inventory.gems < deal.base_deal.gems_cost:
        return Response({'status': False, 'reason': 'not enough gems!'})

    reward_deal(user, user.inventory, deal.base_deal)
    return Response({'status': True})


class DealSchema(Schema):
    id = fields.Int(attribute='base_deal.id')
    gems = fields.Int(attribute='base_deal.gems')
    coins = fields.Int(attribute='base_deal.coins')
    dust = fields.Int(attribute='base_deal.dust')
    item = fields.Nested(BaseItemSchema, attribute='base_deal.item')
    item_quantity = fields.Int(attribute='base_deal.item_quantity')
    char_type = fields.Nested(BaseCharacterSchema, attribute='base_deal.char_type')
    deal_type = fields.Int(attribute='base_deal.deal_type')
    order = fields.Int(attribute='base_deal.order')
    gems_cost = fields.Int(attribute='base_deal.gems_cost')
    expiration_date = fields.DateTime()

    is_available = fields.Method("get_availability")

    def get_availability(self, deal):
        return PurchasedTracker.objects.filter(user=self.context, deal=deal).first() is None


class GetDeals(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        deal_schema = DealSchema(many=True)
        deal_schema.context = request.user
        curr_time = datetime.now()

        daily_deals = deal_schema.dump(
            ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
                base_deal__deal_type=DealType.DAILY.value,
                expiration_date__gt=curr_time).order_by('base_deal__order'))
        weekly_deals = deal_schema.dump(
            ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
                base_deal__deal_type=DealType.WEEKLY.value,
                expiration_date__gt=curr_time).order_by('base_deal__order'))

        gemscost_deals = deal_schema.dump(
            ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
                base_deal__deal_type=DealType.GEMS_COST.value,
                expiration_date__gt=curr_time).order_by('base_deal__order'))

        return Response({"daily_deals": daily_deals, 'weekly_deals': weekly_deals, 'gemcost_deals': gemscost_deals})


def make_deals(deal_type: int):
    if deal_type == constants.DealType.DAILY.value:
        interval = 1
    elif deal_type == constants.DealType.WEEKLY.value:
        interval = 7
    else:
        raise Exception("invalid deal_type, sorry friendo")

    # pick random
    deals0 = BaseDeal.objects.filter(order=0, deal_type=deal_type)
    deals1 = BaseDeal.objects.filter(order=1, deal_type=deal_type)
    deals2 = BaseDeal.objects.filter(order=2, deal_type=deal_type)

    pick0 = deals0[random.randrange(len(deals0))]
    pick1 = deals1[random.randrange(len(deals1))]
    pick2 = deals2[random.randrange(len(deals2))]

    bulk_deals = []
    expiration_date = get_expiration_date(interval)
    for pick in [pick0, pick1, pick2]:
        active_deal = ActiveDeal(base_deal=pick, expiration_date=expiration_date)
        bulk_deals.append(active_deal)

    ActiveDeal.objects.bulk_create(bulk_deals)


# Runs everyday and randomly picks from the pool of BaseDeals for each of the orders and updates it
@transaction.atomic()
def refresh_daily_deals_cronjob():
    ActiveDeal.objects.filter(base_deal__deal_type=constants.DealType.DAILY.value).delete()
    make_deals(constants.DealType.DAILY.value)


# Runs every week and randomly picks from the pool of BaseDeals for each of the orders and updates it
@transaction.atomic()
def refresh_weekly_deals_cronjob():
    ActiveDeal.objects.filter(base_deal__deal_type=constants.DealType.WEEKLY.value).delete()
    make_deals(constants.DealType.WEEKLY.value)


# General function that rolls a bucket based on weighted odds
# Expects: buckets to be a list of odds that sum to 1000
# Returns: index of the bucket that was picked
def weighted_pick_from_buckets(buckets):
    rand = random.randint(1, 1000)
    total = 0
    for i, bucket in enumerate(buckets):
        total += bucket
        if rand <= total:
            return i

    raise Exception('Invalid bucket total')


# returns a random BaseItem with weighted odds
def get_weighted_odds_item(rarity_odds=None):
    if rarity_odds is None:
        rarity_odds = constants.REGULAR_ITEM_ODDS_PER_CHEST[0]  # default SILVER chest rarity odds

    rarity = constants.RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_rand_base_item_from_rarity(rarity)


def get_rand_base_item_from_rarity(rarity):
    base_items = BaseItem.objects.filter(rarity=rarity,
                                         item_type__in=constants.COIN_SHOP_ITEMS)
    num_items = base_items.count()
    chosen_item = base_items[random.randrange(num_items)]
    return chosen_item


# returns a random BaseCharacter with weighted odds
def get_weighted_odds_character(rarity_odds=None):
    if rarity_odds is None:
        rarity_odds = constants.SUMMON_RARITY_BASE

    rarity = constants.RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_rand_base_char_from_rarity(rarity)


def get_rand_base_char_from_rarity(rarity):
    base_chars = BaseCharacter.objects.filter(rarity=rarity, rollable=True)
    num_chars = base_chars.count()
    chosen_char = base_chars[random.randrange(num_chars)]
    return chosen_char


def insert_character(user, chosen_char_id):
    old_char = Character.objects.filter(user=user, char_type_id=chosen_char_id).first()

    if old_char:
        old_char.copies += 1
        old_char.save()
        return old_char

    new_char = Character.objects.create(user=user, char_type_id=chosen_char_id)
    QuestUpdater.add_progress_by_type(user, constants.OWN_HEROES, 1)
    return new_char


CharacterCount = namedtuple("CharacterCount", "character count")


def generate_and_insert_characters(user, char_count, rarity_odds=None):
    new_chars = {}
    # generate char_count random characters
    for i in range(char_count):
        base_char = get_weighted_odds_character(rarity_odds)

        # auto retire common heroes
        if base_char.rarity == 1 and user.inventory.is_auto_retire:
            user.inventory.essence += constants.ESSENCE_PER_COMMON_CHAR_RETIRE
            user.inventory.save()
            continue

        new_char = insert_character(user, base_char.char_type)
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

    @transaction.atomic()
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
                rarity = [0, 1000, 0, 0]
            elif char_copies == 4:
                # rarity 3
                rarity = [0, 0, 1000, 0]

        new_chars = generate_and_insert_characters(user, constants.SUMMON_COUNT[purchase_item_id], rarity)

        # convert to a serialized form
        for char_id, char_count in new_chars.items():
            new_char_arr.append({"count": char_count.count, "character": CharacterSchema(char_count.character).data})

        return Response({"status": True, "characters": new_char_arr})
