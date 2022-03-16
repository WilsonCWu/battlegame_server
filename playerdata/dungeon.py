import time
import secrets
import random

from django.db import transaction
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import DungeonProgress, Character, DungeonStats, Placement
from playerdata.models import DungeonStage
from playerdata.models import UserMatchState
from playerdata.models import ReferralTracker
from . import constants, formulas, dungeon_gen, wishlist, chapter_rewards_pack, world_pack, chests, server, \
    level_booster
from .constants import DungeonType
from .matcher import PlacementSchema
from .questupdater import QuestUpdater
from .referral import award_referral
from .serializers import ValueSerializer, SetDungeonProgressSerializer


class DungeonProgressSchema(Schema):
    stage_id = fields.Int()


class DungeonStageSchema(Schema):
    stage_id = fields.Int(attribute='stage')
    player_exp = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    mob = fields.Nested(PlacementSchema)
    char_dialog = fields.Str()


def complete_referral_conversion(user):
    referral_tracker = ReferralTracker.objects.filter(user=user).first()
    if referral_tracker is None or referral_tracker.converted:
        return
    award_referral(referral_tracker.referral.user, constants.REFERER_GEMS_REWARD)
    QuestUpdater.add_progress_by_type(referral_tracker.referral.user, constants.REFERRAL, 1)
    referral_tracker.converted = True
    referral_tracker.save()


class DungeonSetProgressStageView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = SetDungeonProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_states, _ = UserMatchState.objects.get_or_create(user=request.user)
        dungeon_type = serializer.validated_data['dungeon_type']
        token = secrets.token_hex(16)

        state = {
            'win': serializer.validated_data['is_win'],
            'timestamp': int(time.time()),
            'token': token,
        }
        if dungeon_type == constants.DungeonType.CAMPAIGN.value:
            match_states.campaign_state = state
        else:
            match_states.tower_state = state

        match_states.save()
        return Response({'status': True, 'token': token})


def get_redis_dungeon_winrate_key(dungeon_type, stage):
    return f'dungeon_winrate_{dungeon_type}_{stage}'


def track_dungeon_stats(dungeon_type, is_win, stage):
    r = get_redis_connection('default')
    if not DungeonStats.objects.filter(dungeon_type=dungeon_type, stage=stage).exists():
        DungeonStats.objects.create(dungeon_type=dungeon_type, stage=stage)
    key = get_redis_dungeon_winrate_key(dungeon_type, stage)
    r.incr(f'{key}_games')
    if is_win:
        r.incr(f'{key}_wins')


class DungeonSetProgressCommitView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        # Increment Dungeon progress
        serializer = SetDungeonProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_states, _ = UserMatchState.objects.get_or_create(user=request.user)

        is_win = serializer.validated_data['is_win']
        dungeon_type = serializer.validated_data['dungeon_type']

        # Validate the the state's been staged.
        if dungeon_type == constants.DungeonType.CAMPAIGN.value:
            state = match_states.campaign_state
        else:
            state = match_states.tower_state

        if not state or time.time() - state['timestamp'] > (5 * 60):
            return Response({'status': False,
                             'reason': 'Expired / missing staging status.'})

        token = serializer.validated_data['token'] if 'token' in serializer.validated_data else ''
        if state['token'] != token:
            return Response({'status': False,
                             'reason': 'Invalid / missing match token.'})

        # NOTE: we should commit the result EVEN if it's a loss for the sake
        # of quest tracking.
        if not state['win'] and is_win:
            return Response({'status': False,
                             'reason': 'Cannot transition from loss to win.'})

        progress = DungeonProgress.objects.get(user=request.user)
        if dungeon_type == constants.DungeonType.CAMPAIGN.value:
            QuestUpdater.add_progress_by_type(request.user, constants.ATTEMPT_DUNGEON_GAMES, 1)
            track_dungeon_stats(dungeon_type, is_win, progress.campaign_stage)
        else:
            QuestUpdater.add_progress_by_type(request.user, constants.ATTEMPT_TOWER_GAMES, 1)
            track_dungeon_stats(dungeon_type, is_win, progress.tower_stage)

        if not is_win:
            return Response({'status': True})

        if dungeon_type == constants.DungeonType.CAMPAIGN.value:
            stage = progress.campaign_stage
            if constants.DUNGEON_REFERRAL_CONVERSION_STAGE <= stage <= constants.DUNGEON_REFERRAL_CONVERSION_STAGE + 5:
                complete_referral_conversion(request.user)
                wishlist.init_wishlist(request.user)

            if stage % 40 == 0 and request.user.chapterrewardpack.is_active:
                world_completed = progress.campaign_stage // 40
                chapter_rewards_pack.complete_chapter_rewards(world_completed, request.user.chapterrewardpack)

            if stage == 20 or stage % 40 == 0:
                world_pack.activate_new_pack(request.user, stage // 40)

            if stage == constants.LEVEL_BOOSTER_UNLOCK_STAGE:
                level_booster.activate_levelbooster(request.user)

            rewards = campaign_tutorial_rewards(stage)
            chests.award_chest_rewards(request.user, rewards)

            QuestUpdater.set_progress_by_type(request.user, constants.COMPLETE_DUNGEON_LEVEL, progress.campaign_stage)
            QuestUpdater.add_progress_by_type(request.user, constants.WIN_DUNGEON_GAMES, 1)
            progress.campaign_stage += 1
        else:
            stage = progress.tower_stage

            QuestUpdater.set_progress_by_type(request.user, constants.COMPLETE_TOWER_LEVEL, progress.tower_stage)
            QuestUpdater.add_progress_by_type(request.user, constants.WIN_TOWER_GAMES, 1)
            progress.tower_stage += 1

        progress.save()

        # dungeon rewards
        inventory = request.user.inventory
        inventory.coins += formulas.coins_reward_dungeon(stage, dungeon_type)
        inventory.gems += formulas.gems_reward_dungeon(stage, dungeon_type)
        inventory.save()

        userinfo = request.user.userinfo
        player_exp = formulas.player_exp_reward_dungeon(stage)
        formulas.level_up_check(request.user.userinfo, player_exp)
        userinfo.player_exp += player_exp
        userinfo.save()

        return Response({'status': True})


def campaign_tutorial_rewards(stage):
    if stage == 1:
        return [chests.ChestReward('char_id', 5)]
    elif stage == 2:
        return [chests.ChestReward('char_id', 17)]
    else:
        return []


class DungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dungeon_type = int(serializer.validated_data['value'])

        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        if dungeon_type == DungeonType.CAMPAIGN.value:
            stage = dungeon_progress.campaign_stage
        elif dungeon_type == DungeonType.TOWER.value:
            stage = dungeon_progress.tower_stage
        else:
            return Response({'status': False, 'reason': 'unknown dungeon type'})

        if stage > constants.MAX_DUNGEON_STAGE[dungeon_type]:
            return Response({'status': True, 'stage_id': stage})

        # TODO: DungeonStage should be repurposed for just stage metadata, like dialog, rewards/mob already dynamically generated
        dungeon_stage = DungeonStage.objects.filter(stage=stage, dungeon_type=dungeon_type).exclude(char_dialog__isnull=True).first()
        char_dialog = str(dungeon_stage.char_dialog) if dungeon_stage else ''

        if dungeon_type == DungeonType.CAMPAIGN.value:
            rewards = campaign_tutorial_rewards(stage)
        else:
            rewards = []

        return Response({'status': True,
                         'stage_id': stage,
                         'player_exp': formulas.player_exp_reward_dungeon(stage),
                         'coins': formulas.coins_reward_dungeon(stage, dungeon_type),
                         'gems': formulas.gems_reward_dungeon(stage, dungeon_type),
                         'mob': dungeon_gen.stage_generator(stage, dungeon_type),
                         'story_text': "",  # TODO: Remove me after 1.0.10
                         'char_dialog': char_dialog,
                         'rewards': chests.ChestRewardSchema(rewards, many=True).data
                         })
