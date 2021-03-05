import random

from django.db import transaction
from django_common.auth_backends import User

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from . import rolls
from .serializers import DailyDungeonStartSerializer, DailyDungeonResultSerializer
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
        char_id = rolls.get_weighted_odds_character(rarity_odds, available_chars).char_type
        char_list.append(DDCharModel(char_id, positions[i]))

    return char_list


# Creates a fresh set of 8 bosses that will be used to generate
# the individual Daily Dungeon stages for the day
def daily_dungeon_team_gen_cron():
    teams_list = []

    available_positions_front = range(1, 16)
    available_positions_back = range(16, 26)

    available_chars_front = [0, 4, 5, 6, 8, 11, 13, 19, 24]
    available_chars_back = [7, 9, 10, 12, 16, 17, 18, 21, 22, 23]

    num_frontline = random.randint(2, 3)
    num_backline = 5 - num_frontline

    for n in range(0, 8):
        char_list = []

        # Pick frontliners and set their positions
        char_list.extend(pick_line(available_positions_front, available_chars_front, num_frontline))

        # Pick backliners and set their positions
        char_list.extend(pick_line(available_positions_back, available_chars_back, num_backline))

        stage = DailyDungeonStage(stage=n + 1, team_comp=DDCharSchema(many=True).dump(char_list))
        teams_list.append(stage)

    # refresh the stages on db
    DailyDungeonStage.objects.all().delete()
    DailyDungeonStage.objects.bulk_create(teams_list)


# returns a list of 5 levels based on the stage in Daily Dungeons
def get_levels_for_stage(starting_level, stage_num, boss_stage):
    boss_level = starting_level + (boss_stage * 10)
    position_in_stage = stage_num % 10

    # TODO: this is hardcoded level progression for the 10 filler stages
    # makes it much easier to tune and change for now
    if position_in_stage == 0:
        return [boss_level] * 5
    elif position_in_stage == 1:
        return [boss_level - 13] * 5
    elif position_in_stage == 2:
        return [(boss_level - 10)] * 3 + [(boss_level - 9)] * 2
    elif position_in_stage == 3:
        return [(boss_level - 9)] * 3 + [(boss_level - 8)] * 2
    elif position_in_stage == 4:
        return [(boss_level - 8)] * 3 + [(boss_level - 6)] * 2
    elif position_in_stage == 5:
        return [boss_level - 5] * 5
    elif position_in_stage == 6:
        return [(boss_level - 8)] * 3 + [(boss_level - 6)] * 2
    elif position_in_stage == 7:
        return [(boss_level - 7)] * 3 + [(boss_level - 5)] * 2
    elif position_in_stage == 8:
        return [(boss_level - 6)] * 3 + [(boss_level - 3)] * 2
    else:
        return [(boss_level - 3)] * 3 + [(boss_level - 1)] * 2


# converts a JSON team_comp (see models DailyDungeonStage for more details)
# into a fully functional Placement
def convert_teamp_comp_to_stage(team_comp, stage_num, boss_stage):
    placement = Placement()
    levels = get_levels_for_stage(160, stage_num, boss_stage)

    for i, char in enumerate(team_comp):
        leveled_char = Character(user_id=1, char_type_id=char['char_id'], level=levels[i], char_id=i + 1)

        if i == 0:
            placement.char_1 = leveled_char
            placement.pos_1 = char['position']
        elif i == 1:
            placement.char_2 = leveled_char
            placement.pos_2 = char['position']
        elif i == 2:
            placement.char_3 = leveled_char
            placement.pos_3 = char['position']
        elif i == 3:
            placement.char_4 = leveled_char
            placement.pos_4 = char['position']
        else:
            placement.char_5 = leveled_char
            placement.pos_5 = char['position']

    return placement


# Pulls the corresponding
def daily_dungeon_stage_generator(stage_num):
    boss_stage = (stage_num // 10) + (0 if (stage_num % 10 == 0) else 1)
    team_comp = DailyDungeonStage.objects.get(stage=boss_stage).team_comp
    placement = convert_teamp_comp_to_stage(team_comp, stage_num, boss_stage)

    return PlacementSchema(placement).data


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
                return Response({'status': False, 'reason': 'Not enough golden tickets.'})

            inventory.daily_dungeon_ticket -= 1
            inventory.save()

        # Create dungeon status.
        if dd_status:
            dd_status.stage = 1
            dd_status.is_golden = serializer.validated_data['is_golden']
            dd_status.character_state = serializer.validated_data['characters']
            dd_status.save()
        else:
            DailyDungeonStatus.objects.create(user=request.user,
                                              stage=1,
                                              is_golden=serializer.validated_data['is_golden'],
                                              character_state=serializer.validated_data['characters'])

        return Response({'status': True})


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
            return Response({'status': DailyDungeonStatusSchema(dd_status).data})

        # It is possible that we have uncollected rewards for the user.
        expired_dd_status = DailyDungeonStatus.get_expired_for_user(request.user)
        if expired_dd_status:
            resp = {
                'status': None,
                'previous_end': expired_dd_status.stage,
                'rewards': daily_dungeon_reward(expired_dd_status.is_golden,
                                                expired_dd_status.stage)
            }
            # Mark it as collected by resetting it.
            expired_dd_status.stage = 0
            expired_dd_status.save()
            return Response(resp)

        return Response({'status': None})


class DailyDungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if not dd_status:
            return Response({'status': False, 'reason': 'No active dungeon!'})

        return Response({'status': True, 'stage_id': dd_status.stage, 'mob': daily_dungeon_stage_generator(dd_status.stage)})


def daily_dungeon_reward(is_golden, stage):
    # TODO: update user inventory!
    return {'coins': 100}


class DailyDungeonResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = DailyDungeonResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dd_status = DailyDungeonStatus.objects.get(user=request.user)
        if serializer.validated_data['is_loss']:
            last_stage = dd_status.stage
            dd_status.stage = 0
            dd_status.save()
            return Response({'status': True, 'rewards': daily_dungeon_reward(dd_status.is_golden, last_stage)})

        dd_status.stage += 1
        dd_status.save()
        return Response({'status': True})
