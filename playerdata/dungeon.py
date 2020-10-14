from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_marshmallow import Schema, fields

from playerdata.models import DungeonProgress
from playerdata.models import DungeonStage
from playerdata.models import ReferralTracker
from . import constants
from .inventory import get_reward_exp_for_dungeon_level

from .matcher import PlacementSchema
from .questupdater import QuestUpdater
from .referral import award_referral


class DungeonProgressSchema(Schema):
    stage_id = fields.Int()


class DungeonStageSchema(Schema):
    stage_id = fields.Int(attribute='id')
    exp = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    mob = fields.Nested(PlacementSchema)


def complete_referral_conversion(user):
    referral_tracker = ReferralTracker.objects.filter(user=user).first()
    if referral_tracker is None or referral_tracker.converted:
        return
    award_referral(referral_tracker.referral.user)
    QuestUpdater.add_progress_by_type(referral_tracker.referral.user, constants.REFERRAL, 1)
    referral_tracker.converted = True
    referral_tracker.save()


class DungeonSetProgressView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Increment Dungeon progress
        progress = DungeonProgress.objects.get(user=request.user)

        if progress.stage_id == constants.DUNGEON_REFERRAL_CONVERSION_STAGE:
            complete_referral_conversion(request.user)

        inventory = request.user.inventory
        player_exp = get_reward_exp_for_dungeon_level(progress.stage_id)
        inventory.player_exp += player_exp
        inventory.save()

        progress.stage_id += 1
        progress.save()

        QuestUpdater.add_progress_by_type(request.user, constants.REACH_DUNGEON_LEVEL, 1)
        QuestUpdater.add_progress_by_type(request.user, constants.WIN_DUNGEON_GAMES, 1)

        dungeon_rewards = {
            'gold': 100,
            'hero_exp': 100,
            'player_exp': player_exp
        }

        return Response({'status': True, 'rewards': dungeon_rewards})


class DungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        dungeon_stage = DungeonStage.objects.select_related('mob__char_1__weapon') \
            .select_related('mob__char_2__weapon') \
            .select_related('mob__char_3__weapon') \
            .select_related('mob__char_4__weapon') \
            .select_related('mob__char_5__weapon') \
            .filter(id=dungeon_progress.stage_id).first()

        if dungeon_stage is None:
            return Response({'status': False, 'reason': 'unknown stage id', 'stage_id': dungeon_progress.stage_id})
        dungeon_stage_schema = DungeonStageSchema(dungeon_stage)
        return Response(dungeon_stage_schema.data)
