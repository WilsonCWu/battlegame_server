import math

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from battlegame.figures import get_graph_context
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


GRAPH_TEMPLATE_NAME = "graphs.html"
TABLE_TEMPLATE_NAME = "table.html"


@login_required(login_url='/admin/')
def get_defense_placement_report_view(request):
    return UserInfoAdmin.generate_defense_placement_report(UserInfoAdmin, request, UserInfo.objects.all())


@login_required(login_url='/admin/')
def get_base_character_usage_view(request):
    return BaseCharacterUsageAdmin.generate_base_character_usage_report(BaseCharacterUsageAdmin, request, BaseCharacterUsage.objects.all())


@login_required(login_url='/admin/')
def get_graph_view(request, name=None):
    return render(request, GRAPH_TEMPLATE_NAME, get_graph_context(name))


@login_required(login_url='/admin/')
def get_dungeon_table_view(request, name=None):
    return DungeonStatsAdmin.generate_dungeon_stats_report(DungeonStatsAdmin, request, DungeonStats.objects.all())


@login_required(login_url='/admin/')
def get_hacker_report_view(request):
    return HackerAlertAdmin.generate_hacker_report(HackerAlertAdmin, request, HackerAlert.objects.all())
