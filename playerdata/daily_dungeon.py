import math
import random
from datetime import date, datetime, timedelta

from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from . import rolls, constants, chests, dungeon_gen
from .questupdater import QuestUpdater
from .serializers import DailyDungeonStartSerializer, CharStateResultSerializer
from .matcher import PlacementSchema
from .models import DailyDungeonStatus, DailyDungeonStage, Placement, Character


class DDCharModel:
    def __init__(self, char_id, position):
        self.char_id = char_id
        self.position = position


class DDCharSchema(Schema):
    char_id = fields.Int()
    position = fields.Int()


# Picks a set of chars based on available chars and positions to choose from
# For picking backline / frontline
def pick_line(available_positions, available_chars, num_chars):
    char_list = []
    positions = random.sample(available_positions, num_chars)
    for i in range(0, num_chars):
        # TODO: rarity should be commoner on lower stages, more rare on higher stages
        rarity_odds = [0, 350, 400, 250]
        base_char = rolls.get_weighted_odds_character(rarity_odds, available_chars)
        if base_char is None:
            char_id = random.choice(available_chars)
        else:
            char_id = base_char.char_type

        # prevent duplicates
        available_chars.remove(char_id)
        char_list.append(DDCharModel(char_id, positions[i]))

    return char_list


# Creates a fresh set of 8 bosses that will be used to generate
# the individual Daily Dungeon stages for the day
def daily_dungeon_team_gen_cron():
    teams_list = []

    num_frontline = random.randint(2, 3)
    num_backline = 5 - num_frontline

    for n in range(0, 8):
        char_list = []
        available_char_frontline = list(constants.FRONTLINE_CHARS)
        available_char_backline = list(constants.BACKLINE_CHARS)

        # Pick frontliners and set their positions
        char_list.extend(pick_line(constants.FRONTLINE_POS, available_char_frontline, num_frontline))

        # Pick backliners and set their positions
        char_list.extend(pick_line(constants.BACKLINE_POS, available_char_backline, num_backline))

        stage = DailyDungeonStage(stage=n + 1, team_comp=DDCharSchema(many=True).dump(char_list))
        teams_list.append(stage)

    # refresh the stages on db
    DailyDungeonStage.objects.all().delete()
    DailyDungeonStage.objects.bulk_create(teams_list)


# Pulls the corresponding boss stage and generates either a filler or boss level
def daily_dungeon_stage_generator(stage_num):
    return dungeon_gen.stage_generator(stage_num, constants.DungeonType.TUNNELS.value)


class DailyDungeonStartView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = DailyDungeonStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ensure that we don't currently have a daily dungeon run going on.
        # The user needs to end their current run first.
        dd_status_query = DailyDungeonStatus.objects.filter(user=request.user)
        dd_status = dd_status_query[0] if dd_status_query else None

        if dd_status and dd_status.is_active():
            return Response({'status': False, 'reason': 'Existing daily dungeon run.'})

        # Charge the user for their dungeon run.
        inventory = request.user.inventory
        if serializer.validated_data['is_golden']:
            if inventory.daily_dungeon_golden_ticket <= 0:
                return Response({'status': False, 'reason': 'Not enough golden tickets.'})

            inventory.daily_dungeon_golden_ticket -= 1
            inventory.save()
        else:
            if request.user.inventory.daily_dungeon_ticket <= 0:
                return Response({'status': False, 'reason': 'Not enough regular tickets.'})

            inventory.daily_dungeon_ticket -= 1
            inventory.save()

        # Create dungeon status.
        if dd_status:
            dd_status.stage = 1
            dd_status.is_golden = serializer.validated_data['is_golden']
            dd_status.character_state = "" 
            dd_status.save()
        else:
            DailyDungeonStatus.objects.create(user=request.user,
                                              stage=1,
                                              is_golden=serializer.validated_data['is_golden'],
                                              character_state="")

        return Response({'status': True})


def get_next_refresh_time():
    today = datetime.today()
    if today.weekday() < 2:
        return datetime(today.year, today.month, today.day, 0) + timedelta(days=(2 - today.weekday()))
    elif today.weekday() < 4:
        return datetime(today.year, today.month, today.day, 0) + timedelta(days=(4 - today.weekday()))
    elif today.weekday() < 6:
        return datetime(today.year, today.month, today.day, 0) + timedelta(days=1)
    else:
        return datetime(today.year, today.month, today.day, 0) + timedelta(days=3)


class DailyDungeonStatusSchema(Schema):
    is_golden = fields.Bool()
    stage = fields.Int()
    character_state = fields.Str()
 

class DailyDungeonStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # Return status of active dungeon run.
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if dd_status:
            return Response({'status': DailyDungeonStatusSchema(dd_status).data,
                             'next_refresh_time': get_next_refresh_time()})

        return Response({'status': None, 'next_refresh_time': get_next_refresh_time()})


class DailyDungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if not dd_status:
            return Response({'status': False, 'reason': 'No active dungeon!'})

        return Response({'status': True, 'stage_id': dd_status.stage, 'mob': daily_dungeon_stage_generator(dd_status.stage)})


def daily_dungeon_reward(is_golden, stage, user):
    rewards = []
    if stage == 30:
        rewards.append(chests.ChestReward('gems', 100))
    elif stage % 10 == 0:
        rewards = chests.generate_chest_rewards(constants.ChestType.DAILY_DUNGEON.value, user)
    elif stage % 5 == 0:
        rewards.append(chests.pick_resource_reward(user, 'coins', constants.ChestType.DAILY_DUNGEON.value))

    # 2x rewards for golden ticket
    if is_golden and stage % 5 == 0:
        char_guarantees = [0, 0, 0, 0]

        # TODO: tune how much we give in terms of heroes for golden ticket
        if stage >= 60:
            # +1 rare, +1 epic
            char_guarantees[1] = 1
            char_guarantees[2] = 1
        else:
            # +1 rare
            char_guarantees[1] = 1
        rewards.extend(chests.roll_guaranteed_char_rewards(char_guarantees))

        # 2x resource rewards
        for reward in rewards:
            if reward.reward_type in ['coins', 'gems', 'essence']:
                reward.value = reward.value * 2

    chests.award_chest_rewards(user, rewards)
    reward_schema = chests.ChestRewardSchema(rewards, many=True)
    return reward_schema.data


class DailyDungeonResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = CharStateResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dd_status = DailyDungeonStatus.objects.get(user=request.user)
        rewards = daily_dungeon_reward(dd_status.is_golden, dd_status.stage, request.user)

        if serializer.validated_data['is_loss']:
            dd_status.stage = 0
        else:
            # Check if this is the best that the user has ever done in DD.
            # TODO: refactor this as an auxiliary, non-critical path (e.g.
            # for quests / stat updates).
            userinfo = request.user.userinfo
            if userinfo.best_daily_dungeon_stage < dd_status.stage:
                userinfo.best_daily_dungeon_stage = dd_status.stage
                userinfo.save()

            if dd_status.stage == 80:
                dd_status.stage = 0
            else:
                dd_status.stage += 1

        # always save state, since we might have retries in the future
        dd_status.character_state = serializer.validated_data['characters']
        dd_status.save()
        return Response({'status': True, 'rewards': rewards})


class DailyDungeonSkipView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if not dd_status:
            return Response({'status': False, 'reason': 'No active dungeon!'})

        if dd_status.stage % 5 == 0:
            return Response({'status': False, 'reason': 'cannot skip boss level'})
        
        # Allow the user to skip to bosses until the best level - 10.
        best_stage = request.user.userinfo.best_daily_dungeon_stage
        skip_until = max(0, (best_stage // 5) * 5 - 10)

        skip_target = ((dd_status.stage // 5) + 1) * 5 
        if skip_target > skip_until:
            return Response({'status': False, 'reason': 'cannot skip past threshold'})
        
        dd_status.stage = skip_target
        dd_status.save()

        return Response({'status': True})


class DailyDungeonForfeitView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if not dd_status:
            return Response({'status': False, 'reason': 'No active dungeon!'})

        dd_status.stage = 0
        dd_status.save()

        return Response({'status': True})
