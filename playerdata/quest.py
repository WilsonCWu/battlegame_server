from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata.models import PlayerQuestCumulative
from playerdata.models import PlayerQuestWeekly
from playerdata.models import PlayerQuestDaily


class QuestSchema(Schema):
    title = fields.Str(attribute='base_quest.title')
    total = fields.Int(attribute='base_quest.total')
    gems = fields.Int(attribute='base_quest.gems')
    coins = fields.Int(attribute='base_quest.coins')
    item_id = fields.Int(attribute='base_quest.item_type.id')
    item_description = fields.Str(attribute='base_quest.item_type.name')  # Replace with actual description
    char_id = fields.Int(attribute='base_quest.char_type.id')
    char_description = fields.Str(attribute='base_quest.char_type.name')  # Replace with actual description

    progress = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()
    expiration_date = fields.DateTime()


class QuestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cumulative_quests = PlayerQuestCumulative.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')

        weekly_quests = PlayerQuestWeekly.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')

        daily_quests = PlayerQuestDaily.objects.filter(user=request.user)\
            .select_related('base_quest__item_type').select_related('base_quest__char_type')

        cumulative_schema = QuestSchema(cumulative_quests, many=True)
        weekly_schema = QuestSchema(weekly_quests, many=True)
        daily_schema = QuestSchema(daily_quests, many=True)

        return Response({'cumulative_quests': cumulative_schema.data,
                         'weekly_quests': weekly_schema.data,
                         'daily_quests': daily_schema.data})
