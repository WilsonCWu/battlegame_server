from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import constants
from .questupdater import QuestUpdater
from .serializers import UploadResultSerializer

from playerdata.models import Character
from playerdata.models import UserStats
from playerdata.models import Tournament
from playerdata.models import TournamentMatch


# r1, r2 ratings of player 1,2. s1 = 1 if win, 0 if loss, 0.5 for tie
def calculate_elo(r1, r2, s1):
    k = 50  # larger for more volatility
    R1 = 10 ** (r1 / 400)
    R2 = 10 ** (r2 / 400)
    E1 = R1 / (R1 + R2)
    new_r1 = r1 + k * (s1 - E1)
    return new_r1


class UploadResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data['result']

        win = valid_data['win']
        mode = valid_data['mode']
        opponent = valid_data['opponent_id']
        stats = valid_data['stats']

        total_damage_dealt_stat = 0

        # Update stats per hero
        for stat in stats:
            char_id = stat['id']
            hero = Character.objects.select_related('char_type__basecharacterusage').get(char_id=char_id)
            hero.total_damage_dealt += stat['damage_dealt']
            total_damage_dealt_stat += stat['damage_dealt']
            hero.total_damage_taken += stat['damage_taken']
            hero.total_health_healed += stat['health_healed']
            hero.num_games += 1
            hero.num_wins += 1 if win else 0
            hero.save()

            hero.char_type.basecharacterusage.num_games += 1
            hero.char_type.basecharacterusage.num_wins += 1 if win else 0
            hero.char_type.basecharacterusage.save()

        QuestUpdater.add_progress_by_type(request.user, constants.DAMAGE_DEALT, total_damage_dealt_stat)

        response = {}

        if mode == 0:  # quickplay
            user_stats = UserStats.objects.get(user=request.user)
            opponent_stats = UserStats.objects.get(user_id=opponent)

            user_stats.num_games += 1
            opponent_stats.num_games += 1

            if win:
                user_stats.num_wins += 1
                QuestUpdater.add_progress_by_type(request.user, constants.WIN_QUICKPLAY_GAMES, 1)
            else:
                opponent_stats.num_wins += 1

            user_stats.save()
            opponent_stats.save()

            other_user = get_user_model().objects.select_related('userinfo').get(id=opponent)
            updated_rating = calculate_elo(request.user.userinfo.elo, other_user.userinfo.elo, win)
            response = {"rating": updated_rating}

        elif mode == 1:  # tournament
            tournament = Tournament.objects.filter(user=request.user).first()
            if tournament is None:
                return Response({'status': False, 'reason': 'not competing in current tournament'})
            if tournament.fights_left <= 0:
                return Response({'status': False, 'reason': 'no fights left'})
            TournamentMatch.objects.create(user=request.user, opponent_id=opponent,
                                           is_win=win, tournament=tournament, round=tournament.round)
            tournament.fights_left -= 1
            tournament.save()

        return Response(response)
