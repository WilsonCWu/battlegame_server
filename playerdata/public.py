"""Public APIs that we're exposing to our users (i.e. accessible outside of
the Unity client).
"""

import csv

from django.http import HttpResponse
from rest_framework.views import APIView

from playerdata.models import BaseCharacterStats
from playerdata.models import ServerStatus


# These two functions are translated from BaseInfo.cs#L420.
def scaled_stat(level, base, scaler):
    stat = base * (1 + ((level - 1) / 10.0))
    if level >= 15:
        stat += (scaler / 30.0) * (level - 15) ** 1.6
    return int(stat)


def scaled_resistance_stat(level, base, scaler):
    return int(base + (scaler / 100.0) * level)


class PublicStatsView(APIView):
    def get(self, request, version=None):
        if version is None:
            # We do this differently from base, to ensure that we don't expose
            # stats that have not yet been released yet.
            version = ServerStatus.latest_version()

        response = HttpResponse(
            # Opt to display it instead of downloading it for now.
            content_type="text/plain"
        )

        writer = csv.writer(response)
        writer.writerow(['Level', 'AD', 'AP', 'HP', 'AR', 'MR', 'Crit Chance'])

        def write_level(level, stat):
            writer.writerow([
                str(level),
                scaled_stat(level, stat.attack_damage, stat.attack_scale),
                scaled_stat(level, stat.ability_damage, stat.ability_scale),
                scaled_stat(level, stat.health, stat.health_scale),
                scaled_resistance_stat(level, stat.ar, stat.ar_scale),
                scaled_resistance_stat(level, stat.mr, stat.mr_scale),
                stat.crit_chance
            ])

        for stat in BaseCharacterStats.get_active_under_version(version):
            if not stat.char_type.rollable:
                continue
            writer.writerow([stat.char_type.name])
            for i in range(1, 240, 20):
                write_level(i, stat)
            write_level(240, stat)

        return response
