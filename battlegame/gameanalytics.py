import math
import collections
from django.http.response import HttpResponse

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from battlegame.figures import *
from playerdata.admin import HackerAlertAdmin, UserInfoAdmin, BaseCharacterUsageAdmin, DungeonStatsAdmin
from playerdata.models import *


def percentile(data, perc: int):
    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]


def print_player_prog(perc=50):
    today = datetime.now(timezone.utc)
    print("day, elo, dungeon, best_dd_stage")

    for day_delta in range(0, 185, 5):
        start_date = today - timedelta(days=day_delta + 5)
        end_date = today - timedelta(days=day_delta)
        stats = UserStats.objects.filter(time_started__range=(start_date, end_date)).select_related('user__userinfo').select_related('user__dungeonprogress')

        active_players = [x for x in stats if x.user.userinfo.elo > 0]
        elos = [x.user.userinfo.elo for x in active_players]
        dungeon_prog = [x.user.dungeonprogress.campaign_stage for x in active_players]
        best_dd = [x.user.userinfo.best_daily_dungeon_stage for x in active_players]

        if len(active_players) == 0:
            print("Day " + str(day_delta) + " (" + str(len(active_players)) + " users)" + ": 0, 0, 0")
            continue

        elo_percentile = percentile(elos, perc)
        dungeon_percentile = percentile(dungeon_prog, perc)
        dd_percentile = percentile(best_dd, perc)

        print("Day " + str(day_delta) + " (" + str(len(active_players)) + " users)" + ": " + str(elo_percentile) + ", " + str(dungeon_percentile) + ", " + str(dd_percentile))


def get_single_character_ability_changes(p, a):
    char_diff = ['Changed abilities: %s\n\n' % a.char_type.name]
    for ability_type, ability_name, specs, prev_specs in zip(
            ['Ability1', 'Ability2', 'Ability3', 'Ultimate'],
            [a.ability1_desc, a.ability2_desc, a.ability3_desc, a.ultimate_desc],
            [a.ability1_specs, a.ability2_specs, a.ability3_specs, a.ultimate_specs],
            [p.ability1_specs, p.ability2_specs, p.ability3_specs, p.ultimate_specs],
    ):
        if not prev_specs:
            char_diff.append('NEW %s (%s)' % (ability_type, ability_name))
            continue

        # Check if we have any changes before noting that an ability
        # has diffed.
        ability_diff = []

        # Assume that the levels are the same and don't actually
        # change.
        for lvl in sorted(specs.keys(), key=lambda x: int(x) if BaseCharacterAbility2.is_num_key(x) else 1000 + int(x.lstrip('prestige-'))):
            if lvl not in prev_specs:
                ability_diff.append('LEVEL CHANGES (missing level %s)' % lvl)
                continue

            ability_diff.append(lvl)
            has_changes = False
            removed_keys = set(prev_specs[lvl]) - set(specs[lvl])
            if removed_keys:
                has_changes = True
                ability_diff.append('REMOVED: %s' % str(removed_keys))

            new_keys = {k: v for k, v in specs[lvl].items() if k not in prev_specs[lvl]}
            if new_keys:
                has_changes = True
                ability_diff.append('NEW: %s' % str(new_keys))

            changed_keys = {k: str(prev_specs[lvl][k]) + ' -> ' + str(v)
                            for k, v in specs[lvl].items()
                            if k in prev_specs[lvl] and v != prev_specs[lvl][k]}
            if changed_keys:
                has_changes = True
                ability_diff.append('CHANGED: %s' % str(changed_keys))

            if not has_changes: ability_diff.pop()

        if ability_diff - specs.keys():
            char_diff.append(f'{ability_type} ({ability_name})')
            for diff in ability_diff:
                char_diff.append(diff)

    return char_diff if len(char_diff) > 1 else None  # We don't want only the line "Changed Character" with no changes.


def get_single_character_stat_changes(p, a):
    char_diff = ['Changed character stats: %s\n\n' % a.char_type.name]

    # Get ready for the if-statements baby.
    if p.health != a.health:
        char_diff.append('HEALTH: %s -> %s' % (p.health, a.health))
    if p.starting_mana != a.starting_mana:
        char_diff.append('STARTING MANA: %s -> %s' % (p.starting_mana, a.starting_mana))
    if p.mana != a.mana:
        char_diff.append('MANA: %s -> %s' % (p.mana, a.mana))
    if p.starting_ability_ticks != a.starting_ability_ticks:
        char_diff.append('STARTING ABILITY TICKS: %s -> %s' % (p.starting_ability_ticks, a.starting_ability_ticks))
    if p.ability_ticks != a.ability_ticks:
        char_diff.append('ABILITY TICKS: %s -> %s' % (p.ability_ticks, a.ability_ticks))
    if p.speed != a.speed:
        char_diff.append('SPEED: %s -> %s' % (p.speed, a.speed))
    if p.attack_damage != a.attack_damage:
        char_diff.append('AD: %s -> %s' % (p.attack_damage, a.attack_damage))
    if p.ability_damage != a.ability_damage:
        char_diff.append('AP: %s -> %s' % (p.ability_damage, a.ability_damage))
    if p.attack_speed != a.attack_speed:
        char_diff.append('AS: %s -> %s' % (p.attack_speed, a.attack_speed))
    if p.ar != a.ar:
        char_diff.append('AR: %s -> %s' % (p.ar, a.ar))
    if p.mr != a.mr:
        char_diff.append('MR: %s -> %s' % (p.mr, a.mr))
    if p.attack_range != a.attack_range:
        char_diff.append('Range: %s -> %s' % (p.attack_range, a.attack_range))
    if p.crit_chance != a.crit_chance:
        char_diff.append('Crit: %s -> %s' % (p.crit_chance, a.crit_chance))
    if p.health_scale != a.health_scale:
        char_diff.append('HEALTH Scale: %s -> %s' % (p.health_scale, a.health_scale))
    if p.attack_scale != a.attack_scale:
        char_diff.append('AD Scale: %s -> %s' % (p.attack_scale, a.attack_scale))
    if p.ability_scale != a.ability_scale:
        char_diff.append('AP Scale: %s -> %s' % (p.ability_scale, a.ability_scale))
    if p.ar_scale != a.ar_scale:
        char_diff.append('AR Scale: %s -> %s' % (p.ar_scale, a.ar_scale))
    if p.mr_scale != a.mr_scale:
        char_diff.append('MR Scale: %s -> %s' % (p.mr_scale, a.mr_scale))

    return char_diff if len(char_diff) > 1 else None


# Mostly duplicate of equivalent action in admin tool, but changed for formatting output.  Can't reuse this in admin because of a circular import.
def get_character_ability_changes(v=None):
    if v is None:
        v = ServerStatus.latest_version()
    changed = BaseCharacterAbility2.objects.filter(version=v)

    previous = {}
    for a in BaseCharacterAbility2.objects.all():
        if version.parse(a.version) >= version.parse(v):
            continue
        if a.char_type not in previous or version.parse(a.version) > version.parse(previous[a.char_type].version):
            previous[a.char_type] = a

    changes = {}
    for a in changed:
        if a.char_type not in previous:
            changes[a.char_type.name] = ['NEW CHARACTER: %s' % a.char_type.name]
        else:
            p = previous[a.char_type]
            char_diff = get_single_character_ability_changes(p, a)
            if char_diff is None:
                continue
            changes[a.char_type.name] = char_diff
    return changes


# Mostly duplicate of equivalent action in admin tool, but changed for formatting output.  Can't reuse this in admin because of a circular import.
def get_character_stat_changes(v=None):
    if v is None:
        v = ServerStatus.latest_version()
    changed = BaseCharacterStats.objects.filter(version=v)

    previous = {}
    for a in BaseCharacterStats.objects.all():
        if version.parse(a.version) >= version.parse(v):
            continue
        if a.char_type not in previous or version.parse(a.version) > version.parse(previous[a.char_type].version):
            previous[a.char_type] = a

    changes = {}
    for a in changed:
        if a.char_type not in previous:
            changes[a.char_type.name] = ['NEW CHARACTER: %s' % a.char_type.name]
        else:
            p = previous[a.char_type]
            char_diff = get_single_character_stat_changes(p, a)
            if char_diff is None:
                continue
            changes[a.char_type.name] = char_diff
    return changes


def get_all_character_changes(v=None):
    # expect dictionary<char_id,list<string>> with the values being the list of diffs
    stat_changes = get_character_stat_changes(v)
    ability_changes = get_character_ability_changes(v)

    master_changes = stat_changes if stat_changes is not None else {}
    # put all ability changes into master_changes, accounting for the fact that these are string lists
    for char_name in ability_changes:
        if len(ability_changes[char_name]) == 1:  # Only 1 length strings are the "new character" ones, we don't need dupes of this
            continue
        if char_name in master_changes:
            for change in ability_changes[char_name]:
                master_changes[char_name].append(change)
        else:
            master_changes[char_name] = ability_changes[char_name]

    master_changes_sorted = collections.OrderedDict(sorted(master_changes.items()))
    return master_changes_sorted


GRAPH_TEMPLATE_NAME = "graphs.html"
TABLE_TEMPLATE_NAME = "table.html"


@login_required(login_url='/admin/')
def get_defense_placement_report_view(request):
    if not request.user.is_superuser:
        return HttpResponse()
    return UserInfoAdmin.generate_defense_placement_report(UserInfoAdmin, request, UserInfo.objects.all())


@login_required(login_url='/admin/')
def get_base_character_usage_view(request):
    if not request.user.is_superuser:
        return HttpResponse()
    return BaseCharacterUsageAdmin.generate_base_character_usage_report(BaseCharacterUsageAdmin, request, BaseCharacterUsage.objects.all())


@login_required(login_url='/admin/')
def get_graph_view(request, name=None):
    if not request.user.is_superuser:
        return HttpResponse()
    return render(request, GRAPH_TEMPLATE_NAME, get_graph_context(name))


@login_required(login_url='/admin/')
def get_dungeon_table_view(request, name=None):
    if not request.user.is_superuser:
        return HttpResponse()
    return DungeonStatsAdmin.generate_dungeon_stats_report(DungeonStatsAdmin, request, DungeonStats.objects.all())


@login_required(login_url='/admin/')
def get_hacker_report_view(request):
    if not request.user.is_superuser:
        return HttpResponse()
    return HackerAlertAdmin.generate_hacker_report(HackerAlertAdmin, request, HackerAlert.objects.all())


@login_required(login_url='/admin/')
def get_latest_character_changes_view(request):
    return get_character_changes_view(request, v=ServerStatus.latest_version())


@login_required(login_url='/admin/')
def get_character_changes_view(request, v=None):
    if not request.user.is_superuser:
        return HttpResponse()
    changes = get_all_character_changes(v)
    response = HttpResponse()
    for k, v in changes.items():
        response.write(f'<h3>{k}</h3>')
        response.write('<p>')
        for change in v:
            response.write(f'{change}<br>')
        response.write('</p>')
    return response


@login_required(login_url='/admin/')
def get_player_progress_by_level_report(request):
    if not request.user.is_superuser:
        return HttpResponse()
    context = get_table_context(get_level_and_progress_dataframe(DungeonProgress.objects.all()))
    context['other_data'] = ["Raw data.  See /stats/graph/list for visualization"]
    return render(request, TABLE_TEMPLATE_NAME, context)
