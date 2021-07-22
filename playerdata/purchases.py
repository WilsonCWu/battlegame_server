import json
import random
from collections import namedtuple
from datetime import datetime, timezone, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from google.oauth2 import service_account
from googleapiclient.discovery import build
from inapppy import AppStoreValidator, InAppPyValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from battlegame.settings import SERVICE_ACCOUNT_FILE
from playerdata.models import Character
from playerdata.models import InvalidReceipt
from playerdata.models import Inventory
from playerdata.models import PurchasedTracker, Item, ActiveDeal, BaseDeal, get_expiration_date
from . import constants, chests, rolls, chapter_rewards_pack, world_pack, server
from .base import BaseItemSchema, BaseCharacterSchema
from .constants import DealType
from .questupdater import QuestUpdater
from .serializers import PurchaseItemSerializer
from .serializers import PurchaseSerializer
from .serializers import ValidateReceiptSerializer


# TODO: Deprecated, this is only used for the free 100gems daily
#  we don't do a separate call for purchases anymore
#  it's directly in the Validate call we fulfill the purchase
class PurchaseView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data['purchase_id']
        transaction_id = serializer.validated_data['transaction_id']

        if purchase_id.startswith('com.salutationstudio.tinytitans.deal.'):
            return handle_purchase_deal(request.user, purchase_id, transaction_id)
        else:
            return Response({'status': False, 'reason': 'invalid id ' + purchase_id})


class ValidateView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = ValidateReceiptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = serializer.validated_data['store']
        receipt = serializer.validated_data['receipt']
        transaction_id = serializer.validated_data['transaction_id']

        if store == 0:  # Apple
            return validate_apple(request, receipt, transaction_id)
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
        purchase_id = receipt['productId']
        transaction_id = receipt['orderId']
        is_subscription = purchase_id.startswith('com.salutationstudio.tinytitans.monthlypass')

        if is_subscription:
            response = service.purchases().subscriptions().get(packageName=receipt['packageName'],
                                                               subscriptionId=purchase_id,
                                                               token=receipt['purchaseToken']).execute()
        else:
            response = service.purchases().products().get(packageName=receipt['packageName'],
                                                          productId=purchase_id,
                                                          token=receipt['purchaseToken']).execute()

        return reward_purchase(request.user, transaction_id, purchase_id)

    except Exception:
        InvalidReceipt.objects.create(user=request.user, order_number=str(receipt['orderId']),
                                      date=receipt['purchaseTime'], product_id=receipt['productId'], receipt=receipt_raw)
        return Response({'status': False, 'reason': 'receipt validation failed'})


def validate_apple(request, receipt_raw, transaction_id):
    payload = json.loads(receipt_raw)['Payload']

    bundle_id = 'com.salutationstudio.tinytitans'
    validator = AppStoreValidator(bundle_id, auto_retry_wrong_env_request=True)

    try:
        validation_result = validator.validate(payload, None, exclude_old_transactions=False)
        purchase_id = parse_apple_purchase_id(validation_result, transaction_id)
        if purchase_id == '':
            return Response({'status': False, 'reason': 'transaction_id not found'})

        return reward_purchase(request.user, transaction_id, purchase_id)

    except InAppPyValidationError as ex:
        response_from_apple = ex.raw_response  # contains actual response from AppStore service.
        return Response({'status': False, 'reason': 'receipt validation failed'})


# https://developer.apple.com/documentation/appstorereceipts/responsebody/receipt/in_app
# Docs say the list of IAPs aren't in chronological order, so we need to iterate to check the transaction_id
def parse_apple_purchase_id(validation_result, transaction_id):
    iaps = validation_result["receipt"]["in_app"]

    for iap in iaps:
        if iap["transaction_id"] == transaction_id:
            return iap["product_id"]

    return ''


def reward_purchase(user, transaction_id, purchase_id):
    # check if a duplicate purchase with the same transaction_id exists
    if PurchasedTracker.objects.filter(user=user, transaction_id=transaction_id).exists():
        # Already fulfilled purchase
        return Response({'status': True})

    if purchase_id.startswith('com.salutationstudio.tinytitans.gems.'):
        return handle_purchase_gems(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.'):
        return handle_purchase_deal(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.chapterrewards.'):
        return handle_purchase_chapterpack(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.worldpack.'):
        return handle_purchase_world_pack(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.monthlypass'):
        return handle_purchase_subscription(user, purchase_id, transaction_id)
    else:
        return Response({'status': False, 'reason': 'invalid id ' + purchase_id})


def handle_purchase_subscription(user, purchase_id, transaction_id):
    if not user.userinfo.is_monthly_sub:
        user.userinfo.is_monthly_sub = True
        user.userinfo.save()

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)

    return Response({'status': True})


def handle_purchase_world_pack(user, purchase_id, transaction_id):
    curr_time = datetime.now(timezone.utc)

    if user.worldpack.expiration_date == "" or curr_time > user.worldpack.expiration_date:
        return Response({'status': False, 'reason': 'this purchase offer has now expired'})

    if user.worldpack.is_claimed:
        return Response({'status': False, 'reason': 'this can only be purchased once'})

    # these rewards are "wrapped", i.e. the rarity of the chest instead of the contents of the chest
    wrapped_rewards = world_pack.get_world_pack_rewards(user)
    chest_rewards = []
    misc_rewards = []

    for reward in wrapped_rewards:
        # unwrap the chest rewards
        if reward.reward_type == "chest":
            generated_rewards = chests.generate_chest_rewards(reward.value, user)
            chest_rewards.append({'chest_type': reward.value, 'rewards': chests.ChestRewardSchema(generated_rewards, many=True).data})
            chests.award_chest_rewards(user, generated_rewards)
        else:
            misc_rewards.append(reward)

    chests.award_chest_rewards(user, misc_rewards)

    user.worldpack.is_claimed = True
    user.worldpack.save()

    user.userinfo.vip_exp += 5000
    user.userinfo.save()

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)

    return Response({'status': True,
                     'chest_rewards': chest_rewards,
                     'rewards': chests.ChestRewardSchema(misc_rewards, many=True).data})


def handle_purchase_chapterpack(user, purchase_id, transaction_id):
    curr_time = datetime.now(timezone.utc)
    
    if curr_time > user.chapterrewardpack.expiration_date:
        return Response({'status': False, 'reason': 'this purchase offer has now expired'})

    if purchase_id == constants.CHAPTER_REWARDS_PACK1:
        world_completed = user.dungeonprogress.campaign_stage // 40
        chapter_rewards_pack.complete_chapter_rewards(world_completed, user.chapterrewardpack)
        user.chapterrewardpack.is_active = True
        user.chapterrewardpack.save()

        user.userinfo.vip_exp += 5000
        user.userinfo.save()
    else:
        return Response({'status': False, 'reason': 'invalid purchase_id ' + purchase_id})

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)
    return Response({'status': True})


def handle_purchase_gems(user, purchase_id, transaction_id):
    if purchase_id in constants.IAP_GEMS_AMOUNT:
        user.inventory.gems += constants.IAP_GEMS_AMOUNT[purchase_id]
        user.inventory.gems_bought += constants.IAP_GEMS_AMOUNT[purchase_id]
        user.userinfo.vip_exp += constants.IAP_GEMS_AMOUNT[purchase_id]
    else:
        return Response({'status': False, 'reason': 'invalid purchase_id ' + purchase_id})

    user.inventory.save()
    user.userinfo.save()

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)
    return Response({'status': True})


def reward_deal(user, inventory, base_deal):
    if base_deal.deal_type == constants.DealType.GEMS_COST.value:
        inventory.gems -= base_deal.gems_cost

    inventory.coins += base_deal.coins
    inventory.gems += base_deal.gems
    inventory.gems_bought += base_deal.gems
    inventory.dust += base_deal.dust

    inventory.save()

    if base_deal.purchase_id != constants.DEAL_DAILY_0:
        user.userinfo.vip_exp += base_deal.gems
        user.userinfo.save()

    if base_deal.char_type is not None:
        rolls.insert_character(user, base_deal.char_type.char_type)

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
        PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id, deal=deal)

    # This is for the `ActiveDeal.objects.get` case
    except ObjectDoesNotExist:
        return Response({'status': False, 'reason': 'invalid deal id'})

    # This is for the `PurchasedTracker.objects.create` case
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
    purchase_id = fields.Str(attribute='base_deal.purchase_id')
    expiration_date = fields.DateTime()
    is_available = fields.Bool()


class GetDeals(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        deal_schema = DealSchema(many=True)
        deal_schema.context = request.user
        curr_time = datetime.now(timezone.utc)

        daily_expiration_date = get_expiration_date(1) - timedelta(days=1)
        weekly_expiration_date = get_expiration_date(7) - timedelta(days=7)

        daily_purchased_deals_ids = set(PurchasedTracker.objects.filter(user=request.user, purchase_time__gt=daily_expiration_date).values_list('purchase_id', flat=True))
        weekly_purchased_deals_ids = set(PurchasedTracker.objects.filter(user=request.user, purchase_time__gt=weekly_expiration_date).values_list('purchase_id', flat=True))

        daily_deals = deal_schema.dump(
            ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
                base_deal__deal_type=DealType.DAILY.value,
                expiration_date__gt=curr_time).order_by('base_deal__order'))

        weekly_deals = deal_schema.dump(
            ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
                base_deal__deal_type=DealType.WEEKLY.value,
                expiration_date__gt=curr_time).order_by('base_deal__order'))

        # gemscost_deals = deal_schema.dump(
        #     ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
        #         base_deal__deal_type=DealType.GEMS_COST.value,
        #         expiration_date__gt=curr_time).order_by('base_deal__order'))

        for deal in daily_deals:
            deal["is_available"] = deal["purchase_id"] not in daily_purchased_deals_ids

        for deal in weekly_deals:
            deal["is_available"] = deal["purchase_id"] not in weekly_purchased_deals_ids

        # for deal in gemscost_deals:
        #     deal["is_available"] = deal["purchase_id"] not in daily_purchased_deals_ids

        world_pack_rewards = world_pack.get_world_pack_rewards(request.user)

        return Response({"daily_deals": daily_deals,
                         'weekly_deals': weekly_deals,
                         'gemcost_deals': [],
                         'world_deal_expiration': world_pack.get_world_expiration(),
                         'world_pack': chests.ChestRewardSchema(world_pack_rewards, many=True).data
                         })


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
    PurchasedTracker.objects.filter(purchase_id=constants.DEAL_DAILY_0).delete()
    make_deals(constants.DealType.DAILY.value)


# Runs every week and randomly picks from the pool of BaseDeals for each of the orders and updates it
@transaction.atomic()
def refresh_weekly_deals_cronjob():
    ActiveDeal.objects.filter(base_deal__deal_type=constants.DealType.WEEKLY.value).delete()
    make_deals(constants.DealType.WEEKLY.value)


CharacterCount = namedtuple("CharacterCount", "character count")


def generate_and_insert_characters(user, char_count, rarity_odds=None):
    new_chars = {}
    # generate char_count random characters
    for i in range(char_count):
        base_char = rolls.get_weighted_odds_character(rarity_odds)

        # auto retire common heroes
        if base_char.rarity == 1 and user.inventory.is_auto_retire:
            user.inventory.essence += constants.ESSENCE_PER_COMMON_CHAR_RETIRE
            user.inventory.save()
            continue

        new_char = rolls.insert_character(user, base_char.char_type)
        if new_char.char_id in new_chars:
            old_char = new_chars[new_char.char_id]
            new_chars[new_char.char_id] = CharacterCount(character=new_char, count=old_char.count + 1)
        else:
            new_chars[new_char.char_id] = CharacterCount(character=new_char, count=1)
    return new_chars


def count_char_copies(chars):
    count = 0
    for char in chars:
        count += char.copies + 1  # for first copy (which isn't counted now)
    return count


def handle_purchase_chest(user, purchase_id):
    rewards = []
    if purchase_id == constants.PurchaseID.MYTHIC_CHEST.value:
        char_copies = count_char_copies(Character.objects.filter(user=user))

        # This is to rig the first roll for tutorial
        if char_copies == 3:
            char_id_1 = rolls.get_rand_base_char_from_rarity(2).char_type
            char_id_2 = rolls.get_rand_base_char_from_rarity(3).char_type

            rewards.append(chests.ChestReward(reward_type='char_id', value=char_id_1))
            rewards.append(chests.ChestReward(reward_type='char_id', value=char_id_2))
            rewards.append(chests.pick_resource_reward(user, 'coins', constants.ChestType.MYTHICAL.value))
            rewards.append(chests.pick_resource_reward(user, 'gems', constants.ChestType.MYTHICAL.value))
            rewards.append(chests.pick_resource_reward(user, 'essence', constants.ChestType.MYTHICAL.value))
        else:
            rewards = chests.generate_chest_rewards(constants.ChestType.MYTHICAL.value, user)

    chests.award_chest_rewards(user, rewards)
    return rewards


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

        QuestUpdater.add_progress_by_type(request.user, constants.PURCHASE_ITEM, 1)
        rewards = []

        # can support more types of purchases as we add more
        if purchase_item_id.endswith("CHEST"):
            rewards = handle_purchase_chest(request.user, purchase_item_id)

        reward_schema = chests.ChestRewardSchema(rewards, many=True)
        return Response({'status': True, 'rewards': reward_schema.data})


class CancelSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        request.user.userinfo.is_monthly_sub = False
        request.user.userinfo.save()

        return Response({'status': True})
