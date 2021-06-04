import math

from playerdata.models import *


def percentile(data, perc: int):
    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]


def print_player_prog(perc=50):
    today = datetime.now(timezone.utc)
    print("day, elo, dungeon")

    for day_delta in range(0, 185, 5):
        start_date = today - timedelta(days=day_delta + 5)
        end_date = today - timedelta(days=day_delta)
        stats = UserStats.objects.filter(time_started__range=(start_date, end_date)).select_related('user__userinfo').select_related('user__dungeonprogress')

        active_players = [x for x in stats if x.user.userinfo.elo > 0]
        elos = [x.user.userinfo.elo for x in active_players]
        dungeon_prog = [x.user.dungeonprogress.campaign_stage for x in active_players]
        best_dd = [x.user.userinfo.best_daily_dungeon_stage for x in active_players]

        if len(active_players) == 0:
            print("Day " + str(day_delta) + ": 0, 0, 0")
            continue

        elo_percentile = percentile(elos, perc)
        dungeon_percentile = percentile(dungeon_prog, perc)
        dd_percentile = percentile(best_dd, perc)

        print("Day " + str(day_delta) + ": " + str(elo_percentile) + ", " + str(dungeon_percentile) + ", " + str(dd_percentile))
