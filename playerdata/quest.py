import random

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata.models import ActiveDailyQuest, get_expiration_date, ActiveWeeklyQuest, \
    BaseQuest, PlayerQuestCumulative2, CumulativeTracker, ActiveCumulativeQuest
from playerdata.models import PlayerQuestWeekly
from playerdata.models import PlayerQuestDaily
from playerdata.models import User
from . import constants, server
from .activity_points import ActivityPointsUpdater, ActivityPointsSchema
from .questupdater import QuestUpdater

from .serializers import ClaimQuestSerializer


class CumulativeQuestSchema2(Schema):
    id = fields.Int(attribute='base_quest.id')
    title = fields.Str(attribute='base_quest.title')
    type = fields.Str(attribute='base_quest.type')
    total = fields.Int(attribute='base_quest.total')
    gems = fields.Int(attribute='base_quest.gems')
    coins = fields.Int(attribute='base_quest.coins')
    dust = fields.Int(attribute='base_quest.dust')
    # TODO: something like fields.Function(lambda quest: quest.base_quest.item_type.id if quest.base_quest.item_type else '')
    # these fields won't be returned if item_type is None
    item_id = fields.Int(attribute='base_quest.item_type.id')
    item_description = fields.Str(attribute='base_quest.item_type.description')
    char_id = fields.Int(attribute='base_quest.char_type.id')
    char_description = fields.Str(attribute='base_quest.char_type.name')  # Replace with actual description

    progress = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()


class QuestSchema(Schema):
    id = fields.Int()
    title = fields.Str(attribute='base_quest.title')
    type = fields.Str(attribute='base_quest.type')
    total = fields.Int(attribute='base_quest.total')
    gems = fields.Int(attribute='base_quest.gems')
    coins = fields.Int(attribute='base_quest.coins')
    dust = fields.Int(attribute='base_quest.dust')
    item_id = fields.Int(attribute='base_quest.item_type.id')
    item_description = fields.Str(attribute='base_quest.item_type.description')
    char_id = fields.Int(attribute='base_quest.char_type.id')
    char_description = fields.Str(attribute='base_quest.char_type.name')  # Replace with actual description

    progress = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()
    expiration_date = fields.DateTime()


def award_quest(user_inventory, quest_base):
    user_inventory.coins += quest_base.coins
    user_inventory.gems += quest_base.gems
    user_inventory.dust += quest_base.dust
    # TODO: items and characters
    user_inventory.save()


class QuestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        player_cumulative = PlayerQuestCumulative2.objects.filter(user=request.user).first()
        active_quests = ActiveCumulativeQuest.objects.select_related("base_quest").exclude(base_quest_id__in=player_cumulative.claimed_quests)
        cumulative_basequests = [quest.base_quest for quest in active_quests]
        trackers = CumulativeTracker.objects.filter(user=request.user)
        trackers_dict = {}

        for tracker in trackers:
            trackers_dict[tracker.type] = tracker.progress

        cumulative_quests = []
        for basequest in cumulative_basequests:
            quest = {
                "base_quest": basequest,
                "progress": trackers_dict[basequest.type],
                "claimed": False,
                "completed": basequest.id in player_cumulative.completed_quests
            }
            cumulative_quests.append(quest)

        weekly_quests = PlayerQuestWeekly.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')\
            .order_by('claimed', '-completed')

        daily_quests = PlayerQuestDaily.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')\
            .order_by('claimed', '-completed')

        cumulative_schema = CumulativeQuestSchema2(cumulative_quests, many=True)
        weekly_schema = QuestSchema(weekly_quests, many=True)
        daily_schema = QuestSchema(daily_quests, many=True)

        # TODO: remove check once active / backfilled
        if hasattr(request.user, 'activitypoints'):
            activity_data = ActivityPointsSchema(request.user.activitypoints).data
        else:
            activity_data = None

        return Response({'cumulative_quests': cumulative_schema.data,
                         'weekly_quests': weekly_schema.data,
                         'daily_quests': daily_schema.data,
                         'activity_points': activity_data
                         })


def handle_claim_quest(request, quest_class):
    serializer = ClaimQuestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    quest_id = serializer.validated_data['quest_id']
    user = request.user

    try:
        quest = quest_class.objects.get(user=request.user, id=quest_id)
    except ObjectDoesNotExist:
        return Response({'status': False, 'reason': 'invalid quest_id: %d' % quest_id})

    progress = quest.progress

    if quest.completed and not quest.claimed and progress >= quest.base_quest.total:
        award_quest(user.inventory, quest.base_quest)
        quest.claimed = True
        quest.save()

        if quest_class is PlayerQuestDaily:
            ActivityPointsUpdater.try_complete_daily_activity_points(quest.base_quest.points)
        else:
            ActivityPointsUpdater.try_complete_weekly_activity_points(quest.base_quest.points)

        return Response({'status': True})

    return Response({'status': False, 'reason': 'quest is still in progress'})


class ClaimQuestCumulativeView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ClaimQuestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quest_id = serializer.validated_data['quest_id']

        player_quest = PlayerQuestCumulative2.objects.filter(user=request.user).first()
        base_quest = BaseQuest.objects.get(id=quest_id)
        if (base_quest.id in player_quest.completed_quests) and not (base_quest.id in player_quest.claimed_quests):
            award_quest(request.user.inventory, base_quest)
            player_quest.claimed_quests.append(quest_id)
            player_quest.save()
            return Response({'status': True})

        return Response({'status': False, 'reason': 'quest is still in progress'})


class ClaimQuestWeeklyView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        return handle_claim_quest(request, PlayerQuestWeekly)


class ClaimQuestDailyView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        return handle_claim_quest(request, PlayerQuestDaily)


class CompleteDiscordView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        QuestUpdater.add_progress_by_type(request.user, constants.DISCORD, 1)
        return Response({'status': True})


class LinkAccountView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        QuestUpdater.add_progress_by_type(request.user, constants.ACCOUNT_LINK, 1)
        return Response({'status': True})


# https://stackoverflow.com/questions/57167237/how-to-delete-first-n-items-from-queryset-in-django
def _delete_first_n_rows(quest_class, n):
    quest_class.objects.filter(
        id__in=list(quest_class.objects.values_list('pk', flat=True)[:n])).delete()


def refresh_quests(PlayerQuestModel, ActiveQuestModel, num_quests, days_interval):
    PlayerQuestModel.objects.all().delete()

    # pull new ones and make them for every user
    all_queued_quests = ActiveQuestModel.objects.all()
    if all_queued_quests.count() < num_quests:
        if ActiveQuestModel is ActiveDailyQuest:
            queue_active_daily_quests()
        else:
            queue_active_weekly_quests()
        all_queued_quests = ActiveQuestModel.objects.all()

    active_quests = all_queued_quests[:num_quests]
    expiry_date = get_expiration_date(days_interval)
    users = User.objects.all()
    bulk_quests = []
    for quest in active_quests:
        for user in users:
            player_quest = PlayerQuestModel(base_quest=quest.base_quest, user=user, expiration_date=expiry_date)
            bulk_quests.append(player_quest)

    PlayerQuestModel.objects.bulk_create(bulk_quests)
    _delete_first_n_rows(ActiveQuestModel, num_quests)


# refresh quests: deletes the previous ActiveQuests and uses new ones to propagate to users
def refresh_daily_quests():
    refresh_quests(PlayerQuestDaily, ActiveDailyQuest, constants.NUM_DAILY_QUESTS, 1)
    queue_active_daily_quests()


def refresh_weekly_quests():
    refresh_quests(PlayerQuestWeekly, ActiveWeeklyQuest, constants.NUM_WEEKLY_QUESTS, 7)
    queue_active_weekly_quests()


# randomly sample from pool of quest ids to populate ActiveQuest
def add_quests_to_activequests(ActiveQuestModel, pool_ids, num_quests):
    quest_pool = BaseQuest.objects.filter(pk__in=pool_ids)
    base_quests = random.sample(list(quest_pool), num_quests)

    bulk_quests = []
    for base_quest in base_quests:
        active_quest = ActiveQuestModel(base_quest=base_quest)
        bulk_quests.append(active_quest)

    ActiveQuestModel.objects.bulk_create(bulk_quests)


# only queues up more active quests for the future, doesn't propagate to users
def queue_active_daily_quests():
    add_quests_to_activequests(ActiveDailyQuest, constants.DAILY_QUEST_POOL_IDS, constants.NUM_DAILY_QUESTS)


def queue_active_weekly_quests():
    # hardcoded for two weekly quests we always want to see
    ActiveWeeklyQuest.objects.create(base_quest_id=33)  # Attempt 20 Dungeon games
    ActiveWeeklyQuest.objects.create(base_quest_id=11)  # Win 20 QuickPlay games
    add_quests_to_activequests(ActiveWeeklyQuest, constants.WEEKLY_QUEST_POOL_IDS, constants.NUM_WEEKLY_QUESTS - 2)

