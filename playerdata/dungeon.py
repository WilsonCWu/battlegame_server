from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_marshmallow import Schema, fields

from playerdata.models import Dungeon
from playerdata.models import DungeonProgress
from playerdata.models import DungeonStage

from .serializers import GetDungeonProgressSerializer
from .serializers import GetDungeonStageSerializer


class DungeonStageSchema(Schema):
    stage_id = fields.Int()
    dungeon_id = fields.Int()
    enemy_id = fields.Int()
    exp = fields.Int()
    coins = fields.Int()
    gems = fields.Int()


class DungeonSchema(Schema):
    dungeon_id = fields.Int()
    name = fields.Str()
    stages = fields.Nested(DungeonStageSchema, many=True)


class DungeonProgressSchema(Schema):
    user_id = fields.Int()
    dungeon_id = fields.Int()
    stage_id = fields.Int()


class DungeonView(APIView):

    def get(self, request):
        # For each dungeon, get all the stages
        dungeons = []
        dungeon_query = Dungeon.objects.prefetch_related('dungeonstage_set').all()
        for dungeon in dungeon_query:
            new_dungeon = {"dungeon_id": dungeon.id, "name": dungeon.name, 'stages': dungeon.dungeonstage_set.all()}
            dungeons.append(new_dungeon)
        dungeon_schema = DungeonSchema(dungeons, many=True)
        return Response(dungeon_schema.data)


class DungeonProgressView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetDungeonProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data['target_user']
        dungeon_progress = DungeonProgress.objects.get(user_id=target_user)
        dungeon_progress_schema = DungeonProgressSchema(dungeon_progress)
        return Response(dungeon_progress_schema.data)


class DungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetDungeonStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stage_id = serializer.validated_data['stage_id']
        dungeon_stage = DungeonStage.objects.get(dungeonstage_id=stage_id)
        dungeon_stage_schema = DungeonStageSchema(dungeon_stage)
        return Response(dungeon_stage_schema.data)
