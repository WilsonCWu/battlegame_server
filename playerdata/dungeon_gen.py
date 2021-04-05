import json
import math
import random
from datetime import date

from playerdata import constants, base
from playerdata.matcher import PlacementSchema
from playerdata.models import Placement, Character, DungeonBoss, DailyDungeonStage, Item


# Adjust the prestige based on prestige rarity cap
def prestige_for_rarity(rarity, prestige):
    prestige -= constants.MAX_PRESTIGE_LEVEL - constants.PRESTIGE_CAP_BY_RARITY[rarity]
    return max(prestige, 0)


def new_item(item_type_id):
    if item_type_id is None:
        return None
    return Item(user_id=1, item_type_id=item_type_id, item_id=item_type_id)  # item_id can be anything / not used


"""
We expect team_comp to be in format of
[ {'char_id': <char_id>, 'position': <position>}, {...}, ... ]
"""


# converts a JSON team_comp
# into a fully functional Placement
def convert_teamp_comp_to_stage(team_comp, stage_num, levels, prestiges, seed_int):
    rng = random.Random(seed_int)

    placement = Placement()
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
        char_rarity = base.get_char_rarity(char['char_id'])
        leveled_char = Character(user_id=1,
                                 char_type_id=char['char_id'],
                                 level=max(levels[i], 1),
                                 prestige=prestige_for_rarity(char_rarity, prestiges[i]),
                                 char_id=i + 1,
                                 hat=new_item(char.get('hat_id', None)),
                                 armor=new_item(char.get('armor_id', None)),
                                 boots=new_item(char.get('boots_id', None)),
                                 weapon=new_item(char.get('weapon_id', None)),
                                 trinket_1=new_item(char.get('trinket_1_id', None)),
                                 trinket_2=new_item(char.get('trinket_2_id', None))
                                 )

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


# returns a list of 5 levels based on which filler level it is or a boss stage
def get_campaign_levels_for_stage(starting_level, stage_num, boss_stage):
    if stage_num <= 840:
        boss_level = boss_stage / 4

    # Here we slow down the level increments as we approach the end
    # Prestige here is around 9/10 stars and we expect this ramp to be just as difficult
    # Items also ramp up here to compensate for the smaller stat increases
    elif 940 < stage_num <= 960:
        boss_level = 228
    elif stage_num < 940:
        boss_level = (boss_stage - 860) / 10 + 212
    elif stage_num < 1060:
        boss_level = (boss_stage - 980) / 10 + 212
    else:
        boss_level = constants.MAX_CHARACTER_LEVEL

    # Here we treat each stage of 20 levels as two halves, with a mini boss at the 10th stage
    position_in_stage = stage_num % 20
    if 1 <= position_in_stage <= 10:
        # A mini boss that's half as strong as the final one
        boss_level = max(boss_level - 3, 3)
    else:
        position_in_stage -= 10

    # TODO: this is hardcoded level progression for the 10 filler stages
    # makes it much easier to tune and change for now
    if position_in_stage == 1:
        return [boss_level - 5] * 5
    elif position_in_stage == 2:
        return [(boss_level - 4)] * 3 + [(boss_level - 5)] * 2
    elif position_in_stage == 3:
        return [(boss_level - 4)] * 4 + [(boss_level - 3)]
    elif position_in_stage == 4:
        return [(boss_level - 3)] * 3 + [(boss_level - 4)] * 2
    elif position_in_stage == 5:
        return [boss_level - 3] * 5
    elif position_in_stage == 6:
        return [(boss_level - 2)] * 4 + [(boss_level - 3)]
    elif position_in_stage == 7:
        return [(boss_level - 1)] * 3 + [(boss_level - 2)] * 2
    elif position_in_stage == 8:
        return [(boss_level - 1)] * 4 + [(boss_level - 2)]
    elif position_in_stage == 9:
        return [(boss_level - 1)] * 4 + [boss_level]
    else:
        return [boss_level] * 5


# returns a list of 5 levels based on which filler level it is or a boss stage
def get_tower_levels_for_stage(starting_level, stage_num, boss_stage):
    level_increment = constants.CHAR_LEVEL_DIFF_BETWEEN_STAGES[constants.DungeonType.TOWER.value]
    return [starting_level + (stage_num * level_increment)] * 5


# returns a list of 5 levels based on which filler level it is or a boss stage
def get_tunnels_levels_for_stage(starting_level, stage_num, boss_stage):
    boss_level = starting_level + (boss_stage * 25)
    position_in_stage = stage_num % 10

    # TODO: this is hardcoded level progression for the 10 filler stages
    # makes it much easier to tune and change for now
    if position_in_stage == 1:
        return [boss_level - 27] * 5
    elif position_in_stage == 2:
        return [(boss_level - 24)] * 3 + [(boss_level - 23)] * 2
    elif position_in_stage == 3:
        return [(boss_level - 21)] * 3 + [(boss_level - 19)] * 2
    elif position_in_stage == 4:
        return [(boss_level - 18)] * 3 + [(boss_level - 15)] * 2
    elif position_in_stage == 5:
        return [boss_level - 12] * 5
    elif position_in_stage == 6:
        return [(boss_level - 14)] * 3 + [(boss_level - 11)] * 2
    elif position_in_stage == 7:
        return [(boss_level - 11)] * 3 + [(boss_level - 7)] * 2
    elif position_in_stage == 8:
        return [(boss_level - 8)] * 3 + [(boss_level - 4)] * 2
    elif position_in_stage == 9:
        return [(boss_level - 5)] * 3 + [(boss_level - 1)] * 2
    else:
        return [boss_level] * 5


# Returns a list of 5 prestige levels based on the boss stage
# Increases a whole prestige every 3 worlds, slowly introducing it
# Every 3rd world is a "wall" and that's when the full mob is prestiged fully
def get_campaign_prestige(boss_stage):
    world = math.ceil(boss_stage / 40)
    prestige = math.ceil(world / 3)

    if world <= 6:
        return [0] * 5
    elif world % 3 == 0:
        return [prestige] * 5
    elif world % 3 == 1:
        # Introduce higher prestige one half of the team first
        return [prestige] * 2 + [prestige - 1] * 3
    elif world % 3 == 2:
        # Introduce higher prestige on other half
        return [prestige - 1] * 2 + [prestige] * 3


# adds in some warm up peasants for the first couple levels after a boss
def swap_in_peasants(stage_num, placement, prestiges, seed_int):
    rng = random.Random(seed_int)

    # if warmup level replace with any peasant
    if stage_num % 10 in [1, 2, 3]:
        placement.char_1.char_type_id = rng.randint(1, 3)
        placement.char_1.prestige = prestiges[0]

    # if warmup level replace with any peasant
    if stage_num % 10 in [1, 2]:
        placement.char_2.char_type_id = rng.randint(1, 3)
        placement.char_2.prestige = prestiges[1]

    return placement


def overlevel_carry(placement, carry_id):
    for attr in constants.CHARATTRS:
        char = getattr(placement, attr)
        if char.char_type_id == carry_id:
            char.level = min(char.level + 10, constants.MAX_CHARACTER_LEVEL)
            setattr(placement, attr, char)

    return placement


def convert_placement_to_json(dungeon_bosses):
    for boss in dungeon_bosses:
        char_list = []
        placement = boss.placement

        for charattr, posattr in zip(constants.CHARATTRS, constants.POSATTRS):
            pos = getattr(placement, posattr)
            if pos == -1:
                continue
            char = getattr(placement, charattr)

            char_json = {
                'char_id': char.char_type_id,
                'position': pos
            }
            char_list.append(char_json)

        boss.team_comp = char_list
        boss.save()


# Although there's some duplicate code
# keeping it separate to accommodate easier future changes
def stage_generator(stage_num, dungeon_type):
    if dungeon_type == constants.DungeonType.CAMPAIGN.value:
        boss_stage = math.ceil(stage_num / constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]) * constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]
        dungeon_boss = DungeonBoss.objects.get(stage=boss_stage, dungeon_type=dungeon_type)
        seed_int = stage_num
        levels = get_campaign_levels_for_stage(1, stage_num, boss_stage)
        prestiges = get_campaign_prestige(boss_stage)

        placement = convert_teamp_comp_to_stage(dungeon_boss.team_comp, stage_num, levels, prestiges, seed_int)
        placement = swap_in_peasants(stage_num, placement, prestiges, seed_int)

        # start to overlevel the carry after world 3
        if stage_num > 120:
            placement = overlevel_carry(placement, dungeon_boss.carry_id)

    elif dungeon_type == constants.DungeonType.TOWER.value:
        boss_stage = math.ceil(stage_num / constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]) * constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]
        team_comp = DungeonBoss.objects.get(stage=boss_stage, dungeon_type=dungeon_type).team_comp
        seed_int = stage_num
        levels = get_tower_levels_for_stage(25, stage_num, boss_stage)
        prestiges = [10] * 5

        placement = convert_teamp_comp_to_stage(team_comp, stage_num, levels, prestiges, seed_int)

    elif dungeon_type == constants.DungeonType.TUNNELS.value:
        boss_stage = math.ceil(stage_num / 10)
        team_comp = DailyDungeonStage.objects.get(stage=boss_stage).team_comp
        levels = get_tunnels_levels_for_stage(10, stage_num, boss_stage)
        seed_int = date.today().month + date.today().day + stage_num
        # TODO: perfect place to add in some more prestige as you go deeper
        prestiges = [0] * 5
        placement = convert_teamp_comp_to_stage(team_comp, stage_num, levels, prestiges, seed_int)
        placement = swap_in_peasants(stage_num, placement, prestiges, seed_int)

    else:
        raise Exception("invalid dungeon type")

    return PlacementSchema(placement).data


# To print out all the dungeon levels:
# python manage.py shell_plus
# from playerdata import dungeon_gen
# dungeon_gen.dump_stage_info()
def dump_stage_info():
    test_comp_str = u'[{"char_id": 0, "position": 6}, {"char_id": 1, "position": 10}, {"char_id": 8, "position": 15}, {"char_id": 16, "position": 16}, {"char_id": 12, "position": 22}]'
    team_comp = json.loads(test_comp_str)

    for stage_num in range(1, 1201):
        boss_stage = math.ceil(stage_num / constants.NUM_DUNGEON_SUBSTAGES[0]) * constants.NUM_DUNGEON_SUBSTAGES[0]

        seed_int = stage_num
        levels = get_campaign_levels_for_stage(1, stage_num, boss_stage)
        prestiges = get_campaign_prestige(boss_stage)

        placement = convert_teamp_comp_to_stage(team_comp, stage_num, levels, prestiges, seed_int)
        placement = swap_in_peasants(stage_num, placement, prestiges, seed_int)

        print("lvl:", stage_num,
              " Charlvl: [",
              int(placement.char_1.level),
              int(placement.char_2.level),
              int(placement.char_3.level),
              int(placement.char_4.level),
              int(placement.char_5.level),
              "]",
              "  Prestige: [",  # star level would add whatever is the adjustment per rarity
              int(placement.char_1.prestige),
              int(placement.char_2.prestige),
              int(placement.char_3.prestige),
              int(placement.char_4.prestige),
              int(placement.char_5.prestige),
              "]",
              sep=' ')