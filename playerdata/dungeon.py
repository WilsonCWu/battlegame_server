from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_marshmallow import Schema, fields

from playerdata.models import DungeonProgress, Character, Placement
from playerdata.models import DungeonStage
from playerdata.models import ReferralTracker
from . import constants, formulas

from .matcher import PlacementSchema
from .questupdater import QuestUpdater
from .referral import award_referral


class DungeonProgressSchema(Schema):
    stage_id = fields.Int()


class DungeonStageSchema(Schema):
    stage_id = fields.Int(attribute='stage')
    player_exp = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    mob = fields.Nested(PlacementSchema)


def update_char(char: Character, new_char: Character):
    char.char_type = new_char.char_type
    char.level = new_char.level
    char.save()
    return char


# creates or updates a placement for stage_num based on the boss_placement
def make_mob_from_boss(boss_placement: Placement, i: int, stage_num: int):
    char_levels = [max(boss_placement.char_1.level - i, 1), max(boss_placement.char_2.level - i, 1),
                   max(boss_placement.char_3.level - i, 1), max(boss_placement.char_4.level - i, 1),
                   max(boss_placement.char_5.level - i, 1)]

    dungeon_user_id = 1
    char1 = Character(user_id=dungeon_user_id, char_type=boss_placement.char_1.char_type, level=char_levels[0])
    char2 = Character(user_id=dungeon_user_id, char_type=boss_placement.char_2.char_type, level=char_levels[1])
    char3 = Character(user_id=dungeon_user_id, char_type=boss_placement.char_3.char_type, level=char_levels[2])
    char4 = Character(user_id=dungeon_user_id, char_type=boss_placement.char_4.char_type, level=char_levels[3])
    char5 = Character(user_id=dungeon_user_id, char_type=boss_placement.char_5.char_type, level=char_levels[4])

    dungeon_stage = DungeonStage.objects.filter(stage=stage_num).first()
    if dungeon_stage is not None:
        placement = dungeon_stage.mob

        update_char(placement.char_1, char1)
        update_char(placement.char_2, char2)
        update_char(placement.char_3, char3)
        update_char(placement.char_4, char4)
        update_char(placement.char_5, char5)

        placement.pos_1 = boss_placement.pos_1
        placement.pos_2 = boss_placement.pos_2
        placement.pos_3 = boss_placement.pos_3
        placement.pos_4 = boss_placement.pos_4
        placement.pos_5 = boss_placement.pos_5

        placement.save()
        return placement

    # if placement doesn't exist for this stage_num yet, we create it!
    Character.objects.bulk_create([char1, char2, char3, char4, char5])
    placement = Placement.objects.create(user_id=dungeon_user_id,
                                         pos_1=boss_placement.pos_1, char_1=char1,
                                         pos_2=boss_placement.pos_2, char_2=char2,
                                         pos_3=boss_placement.pos_3, char_3=char3,
                                         pos_4=boss_placement.pos_4, char_4=char4,
                                         pos_5=boss_placement.pos_5, char_5=char5,
                                         )
    return placement


# creates 19 weaker versions of each boss_placement in the queryset
def generate_dungeon_stages(dungeon_bosses_queryset):

    bulk_stages = []
    for boss in dungeon_bosses_queryset:
        for i in range(1, 20):
            stage_num = boss.stage - i
            exp = formulas.player_exp_reward_dungeon(stage_num)
            coins = formulas.coins_reward_dungeon(stage_num)
            gems = 1
            placement = make_mob_from_boss(boss.placement, i, stage_num)

            stage = DungeonStage(stage=stage_num, mob=placement,
                                 coins=coins, gems=gems, player_exp=exp)
            bulk_stages.append(stage)

        # create the actual boss stage
        boss_stage = DungeonStage(stage=boss.stage, mob=boss.placement,
                                  coins=formulas.coins_reward_dungeon(boss.stage), gems=100,
                                  player_exp=formulas.player_exp_reward_dungeon(boss.stage))
        bulk_stages.append(boss_stage)

    DungeonStage.objects.bulk_update_or_create(bulk_stages, ['mob', 'coins', 'gems', 'player_exp'], match_field='stage')


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

        # dungeon rewards
        dungeon = DungeonStage.objects.get(stage=progress.stage_id)
        inventory = request.user.inventory
        inventory.coins += dungeon.coins
        inventory.gems += dungeon.gems
        inventory.save()

        userinfo = request.user.userinfo
        userinfo.player_exp += dungeon.player_exp
        userinfo.save()

        progress.stage_id += 1
        progress.save()

        QuestUpdater.add_progress_by_type(request.user, constants.REACH_DUNGEON_LEVEL, 1)
        QuestUpdater.add_progress_by_type(request.user, constants.WIN_DUNGEON_GAMES, 1)

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
            .filter(stage=dungeon_progress.stage_id).first()

        if dungeon_stage is None:
            return Response({'status': False, 'reason': 'unknown stage id', 'stage_id': dungeon_progress.stage_id})
        dungeon_stage_schema = DungeonStageSchema(dungeon_stage)
        return Response(dungeon_stage_schema.data)
