import json
import math
import random
from datetime import date

from playerdata import constants, base, server
from playerdata.matcher import PlacementSchema
from playerdata.models import Placement, Character, DungeonBoss, DailyDungeonStage, Item


# Adjust the prestige based on prestige rarity cap
def prestige_for_rarity(rarity, prestige):
    prestige -= constants.MAX_PRESTIGE_LEVEL_15 - constants.PRESTIGE_CAP_BY_RARITY_15[rarity]
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

    if stage_num <= 20:
        early_game_level = math.ceil(stage_num / 2)
        return [early_game_level] * 3 + [max(early_game_level - 1, 1)] * 2
    if stage_num <= 620:
        boss_level = starting_level + 7 * (math.ceil(stage_num / 20) - 1)
        level_dip = 10 / 2  # keeping this to know we actually dip 10 on 20 stages, but half for half the stage
    # Here we slow down the level increments as we approach the end
    else:
        boss_level = math.floor((boss_stage - 620) / 20) * 4 + 224
        level_dip = 6 / 2


    # Here we treat each stage of 20 levels as two halves, with a mini boss at the 10th stage
    position_in_stage = stage_num % 20
    if 1 <= position_in_stage <= 10:
        # A mini boss that's half as strong as the final one
        boss_level = max(boss_level - level_dip, level_dip)  # the max is only for the first few stages when it would go negative
    else:
        position_in_stage -= 10

    # TODO: this is hardcoded level progression for the 10 filler stages
    # makes it much easier to tune and change for now
    if position_in_stage == 1:
        return [boss_level - level_dip] * 5
    elif position_in_stage == 2:
        return [(boss_level - math.floor(level_dip * 0.9))] * 3 + [(boss_level - level_dip)] * 2
    elif position_in_stage == 3:
        return [(boss_level - math.floor(level_dip * 0.9))] * 4 + [(boss_level - math.floor(level_dip * 0.8))]
    elif position_in_stage == 4:
        return [(boss_level - math.floor(level_dip * 0.6))] * 3 + [(boss_level - math.floor(level_dip * 0.5))] * 2
    elif position_in_stage == 5:
        return [boss_level - math.floor(level_dip * 0.5)] * 5
    elif position_in_stage == 6:
        return [(boss_level - math.floor(level_dip * 0.4))] * 3 + [(boss_level - math.floor(level_dip * 0.3))] * 2
    elif position_in_stage == 7:
        return [(boss_level - math.floor(level_dip * 0.3))] * 3 + [(boss_level - math.floor(level_dip * 0.4))] * 2
    elif position_in_stage == 8:
        return [(boss_level - math.floor(level_dip * 0.2))] * 4 + [(boss_level - math.floor(level_dip * 0.3))]
    elif position_in_stage == 9:
        return [(boss_level - math.floor(level_dip * 0.1))] * 2 + [(boss_level - math.floor(level_dip * 0.2))] * 2 + [boss_level]
    else:
        return [boss_level] * 5


# returns a list of 5 levels based on which filler level it is or a boss stage
def get_tower_levels_for_stage(starting_level, stage_num, boss_stage):
    level_increment = constants.CHAR_LEVEL_DIFF_BETWEEN_STAGES[constants.DungeonType.TOWER.value]
    return [starting_level + (stage_num * level_increment)] * 5


# returns a list of 5 levels based on which filler level it is or a boss stage
def get_tunnels_levels_for_stage(starting_level, stage_num):
    boss_level = starting_level + math.ceil(stage_num * 2.5)
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
    prestige = min(math.ceil(world / 3), constants.MAX_PRESTIGE_LEVEL_15)

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
    # Don't swap for first 20 hardcoded teams
    if stage_num <= 20:
        return placement

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


# Hardcoding teams early game teams when the fighting isn't as interesting first 20 levels
def early_campaign_teams(stage_num):
    if stage_num <= 2:
        team_comp = [{"char_id": 3, "position": 6}, {"char_id": 1, "position": 8}, {"char_id": 2, "position": 9}]
    elif stage_num <= 5:
        team_comp = [{"char_id": 3, "position": 6}, {"char_id": 8, "position": 5}, {"char_id": 3, "position": 4}, {"char_id": 2, "position": 9}]
    elif stage_num <= 10:
        team_comp = [{"char_id": 3, "position": 8}, {"char_id": 32, "position": 12}, {"char_id": 8, "position": 6}, {"char_id": 3, "position": 4}]
    elif stage_num <= 15:
        team_comp = [{"char_id": 4, "position": 2}, {"char_id": 1, "position": 10}, {"char_id": 8, "position": 3}, {"char_id": 32, "position": 14}]
    elif stage_num <= 20:
        team_comp = [{"char_id": 4, "position": 6}, {"char_id": 8, "position": 5}, {"char_id": 32, "position": 10}, {"char_id": 5, "position": 2}, {"char_id": 2, "position": 20}]

    return team_comp


# Although there's some duplicate code
# keeping it separate to accommodate easier future changes
def stage_generator(stage_num, dungeon_type):
    if dungeon_type == constants.DungeonType.CAMPAIGN.value:
        boss_stage = math.ceil(stage_num / constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]) * constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]

        dungeon_boss = DungeonBoss.objects.get(stage=boss_stage, dungeon_type=dungeon_type)
        if stage_num <= 20:
            dungeon_boss.team_comp = early_campaign_teams(stage_num)

        seed_int = stage_num
        levels = get_campaign_levels_for_stage(10, stage_num, boss_stage)
        prestiges = get_campaign_prestige(boss_stage)

        placement = convert_teamp_comp_to_stage(dungeon_boss.team_comp, stage_num, levels, prestiges, seed_int)
        placement = swap_in_peasants(stage_num, placement, prestiges, seed_int)

        # hardcode dragon boss
        if server.is_server_version_higher('1.0.8'):
            if stage_num == 20 or stage_num == 40:
                dragon = Character(user_id=1, char_type_id=36, level=stage_num + 22, prestige=(stage_num//20))
                placement = Placement(char_1=dragon, pos_1=13)

        # start to overlevel the carry after world 2
        if stage_num > 80:
            placement = overlevel_carry(placement, dungeon_boss.carry_id)

    elif dungeon_type == constants.DungeonType.TOWER.value:
        boss_stage = math.ceil(stage_num / constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]) * constants.NUM_DUNGEON_SUBSTAGES[dungeon_type]
        team_comp = DungeonBoss.objects.get(stage=boss_stage, dungeon_type=dungeon_type).team_comp
        seed_int = stage_num
        levels = get_tower_levels_for_stage(5, stage_num, boss_stage)
        prestiges = [10] * 5  #TODO: can increase this up to 15 as you progress

        placement = convert_teamp_comp_to_stage(team_comp, stage_num, levels, prestiges, seed_int)

    elif dungeon_type == constants.DungeonType.TUNNELS.value:
        boss_stage = math.ceil(stage_num / 4)
        team_comp = DailyDungeonStage.objects.get(stage=boss_stage).team_comp
        levels = get_tunnels_levels_for_stage(10, stage_num)
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
        levels = get_campaign_levels_for_stage(10, stage_num, boss_stage)
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
