import json
import logging
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
from playerdata.creatorcode import award_supported_creator
from playerdata.models import Character
from playerdata.models import InvalidReceipt
from playerdata.models import Inventory
from playerdata.models import PurchasedTracker, Item, ActiveDeal, BaseDeal, get_expiration_date
from .tier_system import get_season_expiration_date
from . import constants, chests, rolls, chapter_rewards_pack, world_pack, server, formulas
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
            new_purchase_token = serializer.validated_data['new_purchase_token'] if 'new_purchase_token' in serializer.validated_data else ''
            return validate_apple(request, receipt, transaction_id, new_purchase_token)
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


def validate_apple(request, receipt_raw, transaction_id, new_purchase_token):
    payload = json.loads(receipt_raw)['Payload']

    bundle_id = 'com.salutationstudio.tinytitans'
    validator = AppStoreValidator(bundle_id, auto_retry_wrong_env_request=True)

    try:
        validation_result = validator.validate(payload, None, exclude_old_transactions=False)
        purchase_id = parse_apple_purchase_id(validation_result, transaction_id)
        if purchase_id == '':
            return Response({'status': False, 'reason': 'transaction_id not found'})

        if new_purchase_token != "UD5QKLWvv7fVbnfkCZ2dsUq4wZ":
            return Response({'status': True})

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

    if not user.userinfo.is_purchaser:
        user.userinfo.is_purchaser = True
        user.userinfo.save()

    if purchase_id.startswith('com.salutationstudio.tinytitans.gems.'):
        return handle_purchase_gems(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.'):
        return handle_purchase_deal(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.chapterrewards.'):
        return handle_purchase_chapterpack(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.worldpack'):
        return handle_purchase_world_pack(user, purchase_id, transaction_id)
    elif purchase_id.startswith('com.salutationstudio.tinytitans.monthlypass'):
        return handle_purchase_subscription(user, purchase_id, transaction_id)
    elif purchase_id == constants.REGAL_REWARDS_PASS:
        return handle_regal_rewards(user, purchase_id, transaction_id)
    else:
        return Response({'status': False, 'reason': 'invalid id ' + purchase_id})


def handle_purchase_subscription(user, purchase_id, transaction_id):
    if user.userinfo.is_monthly_sub:
        logging.error(f"userid: {user.id}, purchase_id: {purchase_id}, transaction_id: {transaction_id}, repurchased while already on premium")
        return Response({'status': False, 'reason': 'month card repurchased while already on premium'})

    user.userinfo.is_monthly_sub = True
    user.userinfo.save()

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)

    return Response({'status': True})


def handle_regal_rewards(user, purchase_id, transaction_id):
    if user.regalrewards.is_premium:
        logging.error(f"userid: {user.id}, purchase_id: {purchase_id}, transaction_id: {transaction_id}, repurchased while already on premium")
        return Response({'status': False, 'reason': 'premium repurchased while already on premium'})

    user.regalrewards.is_premium = True
    user.regalrewards.save()

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)

    return Response({'status': True})


def handle_purchase_world_pack(user, purchase_id, transaction_id):
    curr_time = datetime.now(timezone.utc)

    if user.worldpack.expiration_date == "" or curr_time > user.worldpack.expiration_date:
        return Response({'status': False, 'reason': 'this purchase offer has now expired'})

    world_pack_iap = world_pack.get_world_pack_by_id(user, purchase_id)
    if world_pack_iap.unique_worldpack_id() in user.worldpack.purchased_packs:
        return Response({'status': False, 'reason': 'already purchased this pack'})

    # these rewards are "wrapped", i.e. the rarity of the chest instead of the contents of the chest
    rewards_list = []

    for reward in world_pack_iap.rewards:
        # unwrap the chest rewards
        rewards = []
        if reward.reward_type == "chest":
            rewards.extend(chests.generate_chest_rewards(reward.value, user))
        else:
            rewards.append(reward)

        rewards_list.append(rewards)
        chests.award_chest_rewards(user, rewards)

    user.userinfo.vip_exp += formulas.cost_to_vip_exp(formulas.product_to_dollar_cost(purchase_id))
    user.userinfo.save()

    user.worldpack.purchased_packs.append(world_pack_iap.unique_worldpack_id())
    user.worldpack.save()

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)

    return Response({'status': True,
                     'rewards_list': chests.chestRewardsList_to_json(rewards_list)
                     })


def handle_purchase_chapterpack(user, purchase_id, transaction_id):
    # We're not checking expiration time anymore
    # curr_time = datetime.now(timezone.utc)
    #
    # if curr_time > user.chapterrewardpack.expiration_date:
    #     return Response({'status': False, 'reason': 'this purchase offer has now expired'})

    if purchase_id == constants.CHAPTER_REWARDS_PACK0:
        world_completed = user.dungeonprogress.campaign_stage // 40
        chapter_rewards_pack.complete_chapter_rewards(world_completed, user.chapterrewardpack)
        user.chapterrewardpack.is_active = True
        user.chapterrewardpack.save()

        user.userinfo.vip_exp += formulas.cost_to_vip_exp(formulas.product_to_dollar_cost(purchase_id))
        user.userinfo.save()
    else:
        return Response({'status': False, 'reason': 'invalid purchase_id ' + purchase_id})

    PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id)
    return Response({'status': True})


def handle_purchase_gems(user, purchase_id, transaction_id):
    if purchase_id in constants.IAP_GEMS_AMOUNT:
        user.inventory.gems += constants.IAP_GEMS_AMOUNT[purchase_id]
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
        award_supported_creator(user, base_deal.gems_cost)

    inventory.coins += base_deal.coins
    inventory.gems += base_deal.gems
    inventory.dust += base_deal.dust
    inventory.rare_shards += base_deal.rare_shards
    inventory.epic_shards += base_deal.epic_shards
    inventory.legendary_shards += base_deal.legendary_shards
    inventory.dust_fast_reward_hours += base_deal.dust_fast_reward_hours
    inventory.coins_fast_reward_hours += base_deal.coins_fast_reward_hours

    inventory.save()

    if base_deal.purchase_id not in [constants.DEAL_DAILY_0, constants.DEAL_WEEKLY_0, constants.DEAL_MONTHLY_0, '']:
        user.userinfo.vip_exp += formulas.cost_to_vip_exp(formulas.product_to_dollar_cost(base_deal.purchase_id))
        user.userinfo.save()

    if base_deal.char_type is not None:
        rolls.insert_character(user, base_deal.char_type.char_type)

    if base_deal.item is not None:
        for i in range(0, base_deal.item_quantity):
            Item.objects.create(user=user, item_type=base_deal.item.item_type)


def get_deal_from_purchase_id(purchase_id):
    if purchase_id.startswith('com.salutationstudio.tinytitans.deal.daily'):
        deal_type = DealType.DAILY.value
    elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.weekly'):
        deal_type = DealType.WEEKLY.value
    elif purchase_id.startswith('com.salutationstudio.tinytitans.deal.monthly'):
        deal_type = DealType.MONTHLY.value
    else:
        deal_type = DealType.GEMS_COST.value

    order = int(purchase_id[-1])
    curr_time = datetime.now(timezone.utc)

    return ActiveDeal.objects.get(base_deal__deal_type=deal_type, base_deal__order=order,
                                  expiration_date__gt=curr_time)


def handle_purchase_deal(user, purchase_id, transaction_id):
    try:
        deal = get_deal_from_purchase_id(purchase_id)
        PurchasedTracker.objects.create(user=user, transaction_id=transaction_id, purchase_id=purchase_id, deal=deal)

    # This is for `get_deal_from_purchase_id`
    except ObjectDoesNotExist:
        return Response({'status': False, 'reason': 'invalid deal id'})

    # This is for the `PurchasedTracker.objects.create` case
    except IntegrityError as e:
        return Response({'status': False, 'reason': 'already purchased this deal!'})

    if user.inventory.gems < deal.base_deal.gems_cost and deal.base_deal.gems_cost != 0:
        return Response({'status': False, 'reason': 'not enough gems!'})

    reward_deal(user, user.inventory, deal.base_deal)
    return Response({'status': True})


class DealSchema(Schema):
    id = fields.Int(attribute='base_deal.id')
    gems = fields.Int(attribute='base_deal.gems')
    coins = fields.Int(attribute='base_deal.coins')
    dust = fields.Int(attribute='base_deal.dust')
    rare_shards = fields.Int(attribute='base_deal.rare_shards')
    epic_shards = fields.Int(attribute='base_deal.epic_shards')
    legendary_shards = fields.Int(attribute='base_deal.legendary_shards')
    dust_fast_reward_hours = fields.Int(attribute='base_deal.dust_fast_reward_hours')
    coins_fast_reward_hours = fields.Int(attribute='base_deal.coins_fast_reward_hours')
    item = fields.Nested(BaseItemSchema, attribute='base_deal.item')
    item_quantity = fields.Int(attribute='base_deal.item_quantity')
    char_type = fields.Nested(BaseCharacterSchema, attribute='base_deal.char_type')
    deal_type = fields.Int(attribute='base_deal.deal_type')
    order = fields.Int(attribute='base_deal.order')
    gems_cost = fields.Int(attribute='base_deal.gems_cost')
    purchase_id = fields.Str(attribute='base_deal.purchase_id')
    expiration_date = fields.DateTime()
    is_available = fields.Bool()


def get_purchase_deal_ids(user, prev_expiration_date, deal_type: int):
    return set(PurchasedTracker.objects.filter(user=user,
                                               purchase_time__gt=prev_expiration_date,
                                               deal__base_deal__deal_type=deal_type).values_list('purchase_id', flat=True))


def get_last_deal_expiration_date(deal_type: DealType):
    if deal_type == DealType.DAILY:
        return get_expiration_date(1) - timedelta(days=1)
    elif deal_type == DealType.WEEKLY:
        return get_expiration_date(7) - timedelta(days=7)
    elif deal_type == DealType.MONTHLY:
        curr_time = datetime.now(timezone.utc)
        return datetime(curr_time.year, curr_time.month, 1, 0)
    else:
        raise Exception("Invalid DealType: " + deal_type.value)


def get_active_deals(user, cur_time, deal_type):
    active_deals = ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
            base_deal__deal_type=deal_type,
            expiration_date__gt=cur_time)

    if not user.userinfo.is_purchaser:
        active_deals = active_deals.exclude(base_deal__is_premium=True)

    active_deals = active_deals.order_by('base_deal__order')

    return active_deals


class GetDeals(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        deal_schema = DealSchema(many=True)
        deal_schema.context = request.user

        prev_daily_expiration_date = get_last_deal_expiration_date(DealType.DAILY)
        prev_weekly_expiration_date = get_last_deal_expiration_date(DealType.WEEKLY)
        prev_monthly_expiration_date = get_last_deal_expiration_date(DealType.MONTHLY)

        daily_purchased_deals_ids = get_purchase_deal_ids(request.user, prev_daily_expiration_date,
                                                          DealType.DAILY.value)
        weekly_purchased_deals_ids = get_purchase_deal_ids(request.user, prev_weekly_expiration_date,
                                                           DealType.WEEKLY.value)
        monthly_purchased_deals_ids = get_purchase_deal_ids(request.user, prev_monthly_expiration_date,
                                                            DealType.MONTHLY.value)

        cur_time = datetime.now(timezone.utc)
        daily_deals = deal_schema.dump(get_active_deals(request.user, cur_time, DealType.DAILY.value))
        weekly_deals = deal_schema.dump(get_active_deals(request.user, cur_time, DealType.WEEKLY.value))
        monthly_deals = deal_schema.dump(get_active_deals(request.user, cur_time, DealType.MONTHLY.value))

        # gemscost_deals = deal_schema.dump(
        #     ActiveDeal.objects.select_related('base_deal__item').select_related('base_deal__char_type').filter(
        #         base_deal__deal_type=DealType.GEMS_COST.value,
        #         expiration_date__gt=cur_time).order_by('base_deal__order'))

        for deal in daily_deals:
            deal["is_available"] = deal["purchase_id"] not in daily_purchased_deals_ids

        for deal in weekly_deals:
            deal["is_available"] = deal["purchase_id"] not in weekly_purchased_deals_ids

        for deal in monthly_deals:
            deal["is_available"] = deal["purchase_id"] not in monthly_purchased_deals_ids

        # for deal in gemscost_deals:
        #     deal["is_available"] = deal["purchase_id"] not in daily_purchased_deals_ids

        return Response({'status': True,
                         "daily_deals": daily_deals,
                         'weekly_deals': weekly_deals,
                         'monthly_deals': monthly_deals,
                         'gemcost_deals': [],
                         })


def make_deals(deal_type: int, expiration_date):
    deals = BaseDeal.objects.filter(deal_type=deal_type)

    bulk_deals = []
    for pick in deals:
        active_deal = ActiveDeal(base_deal=pick, expiration_date=expiration_date)
        bulk_deals.append(active_deal)

    ActiveDeal.objects.bulk_create(bulk_deals)


# Runs everyday and randomly picks from the pool of BaseDeals for each of the orders and updates it
@transaction.atomic()
def refresh_daily_deals_cronjob():
    ActiveDeal.objects.filter(base_deal__deal_type=constants.DealType.DAILY.value).delete()
    PurchasedTracker.objects.filter(purchase_id=constants.DEAL_DAILY_0).delete()
    expiration_date = get_expiration_date(1)
    make_deals(constants.DealType.DAILY.value, expiration_date)


# Runs every week and randomly picks from the pool of BaseDeals for each of the orders and updates it
@transaction.atomic()
def refresh_weekly_deals_cronjob():
    ActiveDeal.objects.filter(base_deal__deal_type=constants.DealType.WEEKLY.value).delete()
    PurchasedTracker.objects.filter(purchase_id=constants.DEAL_WEEKLY_0).delete()
    expiration_date = get_expiration_date(7)
    make_deals(constants.DealType.WEEKLY.value, expiration_date)


@transaction.atomic()
def refresh_monthly_deals_cronjob():
    ActiveDeal.objects.filter(base_deal__deal_type=constants.DealType.MONTHLY.value).delete()
    PurchasedTracker.objects.filter(purchase_id=constants.DEAL_MONTHLY_0).delete()
    expiration_date = get_season_expiration_date()
    make_deals(constants.DealType.MONTHLY.value, expiration_date)


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
        user.userstats.mythical_chests_purchased += 1
        rewards = chests.generate_chest_rewards(constants.ChestType.MYTHICAL.value, user)
    elif purchase_id == constants.PurchaseID.FORTUNE_CHEST.value:
        user.userstats.fortune_chests_purchased += 1
        rewards = chests.generate_fortune_chest_rewards(user)

    user.userstats.save()
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
        award_supported_creator(user, constants.SUMMON_GEM_COST[purchase_item_id])
        inventory.save()

        QuestUpdater.add_progress_by_type(request.user, constants.PURCHASE_ITEM, 1)
        rewards = []

        # can support more types of purchases as we add more
        if purchase_item_id.endswith("CHEST"):
            rewards = handle_purchase_chest(request.user, purchase_item_id)
            QuestUpdater.add_progress_by_type(user, constants.CHESTS_OPENED, 1)

        reward_schema = chests.ChestRewardSchema(rewards, many=True)
        return Response({'status': True, 'rewards': reward_schema.data})


class CancelSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        request.user.userinfo.is_monthly_sub = False
        request.user.userinfo.save()

        return Response({'status': True})


class CollectBonusGems(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        rewards = [chests.ChestReward('gems', request.user.inventory.gems_bought)]

        request.user.inventory.gems += request.user.inventory.gems_bought
        request.user.inventory.gems_bought = 0
        request.user.inventory.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
