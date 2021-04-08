import random

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import DungeonProgress, Character, Placement
from playerdata.models import DungeonStage
from playerdata.models import ReferralTracker
from . import constants, formulas, server, dungeon_gen
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
    story_text = fields.Str()


def update_char(char: Character, new_char: Character):
    if new_char is None:
        char = None
        return char

    char.char_type = new_char.char_type
    char.level = new_char.level
    char.prestige = new_char.prestige
    char.save()
    return char


# Takes existing positions and picks two random positions to change
# Then assigns new random positions that have not been used yet
def shuffle_positions(len_chars, positions: []):
    new_positions = positions
    shuffle_pos = random.sample(range(0, len_chars), 2)
    possible_pos = list(range(1, 26))

    # remove from the set of possible_pos any positions that are taken by existing chars
    for i in range(0, len(positions)):
        if i not in shuffle_pos:
            if positions[i] != -1:
                possible_pos.remove(positions[i])

    # Get new random positions from unused positions
    random_positions = random.sample(possible_pos, 2)
    new_positions[shuffle_pos[0]] = random_positions[0]
    new_positions[shuffle_pos[1]] = random_positions[1]

    return new_positions


def make_char(user_id: int, char: Character, iteration: int, dungeon_type: int):
    if char is None:
        return None

    level_multiplier = constants.CHAR_LEVEL_DIFF_BETWEEN_STAGES[dungeon_type]

    if dungeon_type == constants.DungeonType.TOWER.value:
        prestige = constants.PRESTIGE_CAP_BY_RARITY[char.char_type.rarity]
    else:
        prestige = 0

    return Character(user_id=user_id,
                     char_type=char.char_type,
                     level=max(char.level - iteration * level_multiplier, 1),
                     prestige=prestige)


# creates or updates a placement for stage_num based on the boss_placement
def make_mob_from_boss(boss_placement: Placement, i: int, stage_num: int, dungeon_type: int):

    # `battlegame` user is the owner for all our dungeon mobs
    dungeon_user_id = 1
    char1 = make_char(dungeon_user_id, boss_placement.char_1, i, dungeon_type)
    char2 = make_char(dungeon_user_id, boss_placement.char_2, i, dungeon_type)
    char3 = make_char(dungeon_user_id, boss_placement.char_3, i, dungeon_type)
    char4 = make_char(dungeon_user_id, boss_placement.char_4, i, dungeon_type)
    char5 = make_char(dungeon_user_id, boss_placement.char_5, i, dungeon_type)

    pos1 = boss_placement.pos_1
    pos2 = boss_placement.pos_2
    pos3 = boss_placement.pos_3
    pos4 = boss_placement.pos_4
    pos5 = boss_placement.pos_5

    chars = [char1, char2, char3, char4, char5]
    len_chars = len(list(filter(None, chars)))
    positions = [pos1, pos2, pos3, pos4, pos5]

    # 1 random peasant from level 1 - 24
    if dungeon_type == constants.DungeonType.CAMPAIGN.value and stage_num <= 24:
        char_to_replace = random.randint(0, len_chars - 1)
        rand_peasant_type = random.randint(1, 3)
        chars[char_to_replace] = Character(user_id=dungeon_user_id, char_type_id=rand_peasant_type, level=chars[char_to_replace].level)

    positions = shuffle_positions(len_chars,  positions)

    # if placement already exists for this stage, we update
    dungeon_stage = DungeonStage.objects.filter(stage=stage_num, dungeon_type=dungeon_type).first()
    if dungeon_stage is not None:
        placement = dungeon_stage.mob

        placement.char_1 = update_char(placement.char_1, chars[0])
        placement.char_2 = update_char(placement.char_2, chars[1])
        placement.char_3 = update_char(placement.char_3, chars[2])
        placement.char_4 = update_char(placement.char_4, chars[3])
        placement.char_5 = update_char(placement.char_5, chars[4])

        placement.pos_1 = positions[0]
        placement.pos_2 = positions[1]
        placement.pos_3 = positions[2]
        placement.pos_4 = positions[3]
        placement.pos_5 = positions[4]

        placement.save()
        return placement

    # if placement doesn't exist for this stage_num yet, we create it!
    Character.objects.bulk_create(list(filter(None, chars)))
    placement = Placement.objects.create(user_id=dungeon_user_id,
                                         pos_1=positions[0], char_1=chars[0],
                                         pos_2=positions[1], char_2=chars[1],
                                         pos_3=positions[2], char_3=chars[2],
                                         pos_4=positions[3], char_4=chars[3],
                                         pos_5=positions[4], char_5=chars[4])
    return placement


# design doc: https://docs.google.com/document/d/1TMjO8-8GfMhp4aN8OEGQeBT-a6VRRgbCEe3S4aAWHSM/edit?usp=sharing
# creates 19 weaker versions of each boss_placement in the queryset
@transaction.atomic
def generate_dungeon_stages(dungeon_bosses_queryset):

    bulk_stages = []
    for boss in dungeon_bosses_queryset:
        num_substages = constants.NUM_DUNGEON_SUBSTAGES[boss.dungeon_type]
        for i in range(1, num_substages):
            stage_num = boss.stage - i
            exp = formulas.player_exp_reward_dungeon(stage_num)
            coins = formulas.coins_reward_dungeon(stage_num, boss.dungeon_type)
            gems = formulas.gems_reward_dungeon(stage_num, boss.dungeon_type)
            placement = make_mob_from_boss(boss.placement, i, stage_num, boss.dungeon_type)

            stage = DungeonStage(stage=stage_num, mob=placement, dungeon_type=boss.dungeon_type,
                                 coins=coins, gems=gems, player_exp=exp)
            bulk_stages.append(stage)

        # create the actual boss stage
        boss_stage = DungeonStage(stage=boss.stage, mob=boss.placement, dungeon_type=boss.dungeon_type,
                                  coins=formulas.coins_reward_dungeon(boss.stage, boss.dungeon_type),
                                  gems=formulas.gems_reward_dungeon(boss.stage, boss.dungeon_type),
                                  player_exp=formulas.player_exp_reward_dungeon(boss.stage))
        bulk_stages.append(boss_stage)

    DungeonStage.objects.bulk_update_or_create(bulk_stages, ['mob', 'coins', 'gems', 'player_exp', 'story_text'], match_field=['stage', 'dungeon_type'])


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
        serializer = SetDungeonProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_win = serializer.validated_data['is_win']
        dungeon_type = serializer.validated_data['dungeon_type']

        if dungeon_type == constants.DungeonType.CAMPAIGN.value:
            QuestUpdater.add_progress_by_type(request.user, constants.ATTEMPT_DUNGEON_GAMES, 1)
        else:
            QuestUpdater.add_progress_by_type(request.user, constants.ATTEMPT_TOWER_GAMES, 1)

        if not is_win:
            return Response({'status': True})

        progress = DungeonProgress.objects.get(user=request.user)

        if dungeon_type == constants.DungeonType.CAMPAIGN.value:
            stage = progress.campaign_stage
            if progress.campaign_stage == constants.DUNGEON_REFERRAL_CONVERSION_STAGE:
                complete_referral_conversion(request.user)

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
        userinfo.player_exp += formulas.player_exp_reward_dungeon(stage)
        userinfo.save()

        return Response({'status': True})


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

        if server.is_server_version_higher("0.2.1") or request.user.id in (21, 2832, 2833, 2024):
            story_text = ""
            dungeon_stage = DungeonStage.objects.filter(stage=stage, dungeon_type=dungeon_type).first()
            if dungeon_stage is not None:
                story_text = dungeon_stage.story_text

            return Response({'status': True,
                             'stage_id': stage,
                             'player_exp': formulas.player_exp_reward_dungeon(stage),
                             'coins': formulas.coins_reward_dungeon(stage, dungeon_type),
                             'gems': formulas.gems_reward_dungeon(stage, dungeon_type),
                             'mob': dungeon_gen.stage_generator(stage, dungeon_type),
                             'story_text': story_text})

        # TODO: remove after dungeons revamp
        dungeon_stage = DungeonStage.objects.select_related('mob__char_1__weapon') \
            .select_related('mob__char_2__weapon') \
            .select_related('mob__char_3__weapon') \
            .select_related('mob__char_4__weapon') \
            .select_related('mob__char_5__weapon') \
            .filter(stage=stage, dungeon_type=dungeon_type).first()

        if dungeon_stage is None:
            return Response({'status': False, 'reason': 'unknown stage id'})

        dungeon_stage_schema = DungeonStageSchema(dungeon_stage)
        return Response(dungeon_stage_schema.data)
