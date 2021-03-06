import math
import random
from datetime import date

from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from . import rolls, constants, chests
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

    num_frontline = random.randint(2, 3)
    num_backline = 5 - num_frontline

    for n in range(0, 8):
        char_list = []

        # Pick frontliners and set their positions
        char_list.extend(pick_line(constants.FRONTLINE_POS, constants.FRONTLINE_CHARS, num_frontline))

        # Pick backliners and set their positions
        char_list.extend(pick_line(constants.BACKLINE_POS, constants.BACKLINE_CHARS, num_backline))

        stage = DailyDungeonStage(stage=n + 1, team_comp=DDCharSchema(many=True).dump(char_list))
        teams_list.append(stage)

    # refresh the stages on db
    DailyDungeonStage.objects.all().delete()
    DailyDungeonStage.objects.bulk_create(teams_list)


# returns a list of 5 levels based on which filler level it is or a boss stage
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
    seed_int = date.today().month + date.today().day + stage_num
    rng = random.Random(seed_int)

    placement = Placement()
    levels = get_levels_for_stage(160, stage_num, boss_stage)
    available_pos_frontline = [*constants.FRONTLINE_POS]
    available_pos_backline = [*constants.BACKLINE_POS]

    # if not a boss or mini boss, shuffle positions
    if stage_num % 5 != 0:
        for char in team_comp:
            if char['char_id'] in constants.FRONTLINE_CHARS:
                char['position'] = rng.choice(available_pos_frontline)
                available_pos_frontline.remove(char['position'])
            else:
                char['position'] = rng.choice(available_pos_backline)
                available_pos_backline.remove(char['position'])

    for i, char in enumerate(team_comp):
        leveled_char = Character(user_id=1, char_type_id=char['char_id'], level=levels[i], char_id=i + 1)

        if i == 0:
            # if warmup level replace with any peasant
            if stage_num % 10 in [1, 2, 6, 7]:
                    leveled_char.char_type_id = rng.randint(1, 3)
            placement.char_1 = leveled_char
            placement.pos_1 = char['position']
        elif i == 1:
            # if warmup level replace with any peasant
            if stage_num % 10 in [1, 6]:
                    leveled_char.char_type_id = rng.randint(1, 3)
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


# Pulls the corresponding boss stage and generates either a filler or boss level
def daily_dungeon_stage_generator(stage_num):
    boss_stage = math.ceil(stage_num/10)
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


def daily_dungeon_reward(is_golden, stage, user):
    rewards = []
    if stage == 30:
        rewards.append(chests.ChestReward('gems', 100))
    elif stage % 10 == 0:
        rewards = chests.generate_chest_rewards(constants.ChestType.DAILY_DUNGEON.value, user)
    elif stage % 5 == 0:
        rewards.append(chests.pick_resource_reward(user, 'coins', constants.ChestType.DAILY_DUNGEON.value))

    # 3x rewards for golden ticket
    if is_golden and stage % 5 == 0:
        char_guarantees = [0, 0, 0, 0]

        # TODO: tune how much we give in terms of heroes for golden ticket
        if stage >= 50:
            # guarantee 2 rares, 2 epics
            char_guarantees[1] = 2
            char_guarantees[2] = 1
        else:
            # guarantee 4 rares
            char_guarantees[1] = 4
        rewards.extend(chests.roll_guaranteed_char_rewards(char_guarantees))

        # 3x resource rewards
        for reward in rewards:
            if reward.reward_type in ['coins', 'gems', 'essence']:
                reward.value = reward.value * 3

    chests.award_chest_rewards(user, rewards)
    reward_schema = chests.ChestRewardSchema(rewards, many=True)
    return reward_schema.data


class DailyDungeonResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = DailyDungeonResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dd_status = DailyDungeonStatus.objects.get(user=request.user)
        rewards = daily_dungeon_reward(dd_status.is_golden, dd_status.stage, request.user)

        if serializer.validated_data['is_loss']:
            dd_status.stage = 0
            dd_status.save()

        dd_status.stage += 1
        dd_status.save()
        return Response({'status': True, 'rewards': rewards})
