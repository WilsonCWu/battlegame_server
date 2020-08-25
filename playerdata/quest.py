from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata.models import PlayerQuestCumulative
from playerdata.models import PlayerQuestWeekly
from playerdata.models import PlayerQuestDaily

from .serializers import ClaimQuestSerializer


class CumulativeQuestSchema(Schema):
    id = fields.Int()
    title = fields.Str(attribute='base_quest.title')
    type = fields.Str(attribute='base_quest.type')
    total = fields.Int(attribute='base_quest.total')
    gems = fields.Int(attribute='base_quest.gems')
    coins = fields.Int(attribute='base_quest.coins')
    item_id = fields.Int(attribute='base_quest.item_type.id')
    item_description = fields.Str(attribute='base_quest.item_type.description')
    char_id = fields.Int(attribute='base_quest.char_type.id')
    char_description = fields.Str(attribute='base_quest.char_type.name')  # Replace with actual description

    progress = fields.Int(attribute='progress.progress')
    completed = fields.Bool()
    claimed = fields.Bool()


class QuestSchema(Schema):
    id = fields.Int()
    title = fields.Str(attribute='base_quest.title')
    type = fields.Str(attribute='base_quest.type')
    total = fields.Int(attribute='base_quest.total')
    gems = fields.Int(attribute='base_quest.gems')
    coins = fields.Int(attribute='base_quest.coins')
    item_id = fields.Int(attribute='base_quest.item_type.id')
    item_description = fields.Str(attribute='base_quest.item_type.description')
    char_id = fields.Int(attribute='base_quest.char_type.id')
    char_description = fields.Str(attribute='base_quest.char_type.name')  # Replace with actual description

    progress = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()
    expiration_date = fields.DateTime()


def award_quest(user_inventory, quest_base, quest):
    user_inventory.coins += quest_base.coins
    user_inventory.gems += quest_base.gems
    # TODO: items and characters
    user_inventory.save()

    quest.claimed = True
    quest.save()


class QuestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cumulative_quests = PlayerQuestCumulative.objects.filter(user=request.user, claimed=False)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')\
            .order_by('-completed')

        weekly_quests = PlayerQuestWeekly.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')\
            .order_by('claimed', '-completed')

        daily_quests = PlayerQuestDaily.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')\
            .order_by('claimed', '-completed')

        cumulative_schema = CumulativeQuestSchema(cumulative_quests, many=True)
        weekly_schema = QuestSchema(weekly_quests, many=True)
        daily_schema = QuestSchema(daily_quests, many=True)

        return Response({'cumulative_quests': cumulative_schema.data,
                         'weekly_quests': weekly_schema.data,
                         'daily_quests': daily_schema.data})


def handle_claim_quest(request, quest_class):
    serializer = ClaimQuestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    quest_id = serializer.validated_data['quest_id']
    user = request.user

    try:
        quest = quest_class.objects.get(user=request.user, id=quest_id)
    except ObjectDoesNotExist:
        return Response({'status': False, 'reason': 'invalid quest_id: ' + quest_id})

    if quest_class is PlayerQuestCumulative:
        progress = quest.progress.progress
    else:
        progress = quest.progress

    if quest.completed and not quest.claimed and progress >= quest.base_quest.total:
        award_quest(user.inventory, quest.base_quest, quest)
        return Response({'status': True})

    return Response({'status': False, 'reason': 'quest is still in progress'})


class ClaimQuestCumulativeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return handle_claim_quest(request, PlayerQuestCumulative)


class ClaimQuestWeeklyView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return handle_claim_quest(request, PlayerQuestWeekly)


class ClaimQuestDailyView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return handle_claim_quest(request, PlayerQuestDaily)
