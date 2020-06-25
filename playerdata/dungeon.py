from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_marshmallow import Schema, fields

from playerdata.models import DungeonProgress
from playerdata.models import DungeonStage

from .matcher import PlacementSchema
from .questupdater import QuestUpdater

from .serializers import DungeonStageSerializer


class DungeonProgressSchema(Schema):
    stage_id = fields.Int()


class DungeonStageSchema(Schema):
    stage_id = fields.Int(attribute='id')
    exp = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    mob = fields.Nested(PlacementSchema)


class DungeonSetProgressView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Increment Dungeon progress
        progress = DungeonProgress.objects.get(user=request.user)
        progress.stage_id += 1
        progress.save()

        QuestUpdater.add_progress_by_type(request.user, QuestUpdater.REACH_DUNGEON_LEVEL, progress.stage_id - 1)
        QuestUpdater.add_progress_by_type(request.user, QuestUpdater.WIN_DUNGEON_GAMES, 1)

        return Response({'status': True})


class DungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        dungeon_stage = DungeonStage.objects.select_related('mob__char_1__weapon') \
            .select_related('mob__char_2__weapon') \
            .select_related('mob__char_3__weapon') \
            .select_related('mob__char_4__weapon') \
            .select_related('mob__char_5__weapon') \
            .get(id=dungeon_progress.stage_id)
        dungeon_stage_schema = DungeonStageSchema(dungeon_stage)
        return Response(dungeon_stage_schema.data)

    def post(self, request):
        serializer = DungeonStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stage_id = serializer.validated_data['stage_id']

        dungeon_stage = DungeonStage.objects.select_related('mob__char_1__weapon') \
            .select_related('mob__char_2__weapon') \
            .select_related('mob__char_3__weapon') \
            .select_related('mob__char_4__weapon') \
            .select_related('mob__char_5__weapon') \
            .get(id=stage_id)
        dungeon_stage_schema = DungeonStageSchema(dungeon_stage)
        return Response(dungeon_stage_schema.data)
