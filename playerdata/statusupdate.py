import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import constants, formulas
from .purchases import weighted_pick_from_buckets
from .questupdater import QuestUpdater
from .serializers import UploadResultSerializer

from playerdata.models import Character, DungeonProgress, Chest
from playerdata.models import UserStats
from playerdata.models import TournamentMember
from playerdata.models import TournamentMatch

import math


# r1, r2 ratings of player 1,2. s1 = 1 if win, 0 if loss, 0.5 for tie
# k larger for more volatility
def calculate_elo(r1, r2, s1, k=50):
    R1 = 10 ** (r1 / 400)
    R2 = 10 ** (r2 / 400)
    E1 = R1 / (R1 + R2)
    new_r1 = r1 + k * (s1 - E1)
    return max(new_r1, 0)


# standing is zero-based integer
def calculate_tourney_elo(r1, avg_elo, standing):
    elo_standing_mult = [1, 0.75, 0.5, 0.25, 0.25, 0.5, 0.75, 1]
    # calculate as win if top 4, lose if bottom 4
    s1 = int(standing < len(elo_standing_mult) / 2)
    delta_elo = calculate_elo(r1, avg_elo, s1, 100) - r1
    new_r1 = r1 + round(delta_elo * elo_standing_mult[standing])
    return max(new_r1, 0)


# returns the rarity of chest
# if no chest was awarded returns 0
def award_chest(user):
    slots = [user.inventory.chest_slot_1,
             user.inventory.chest_slot_2,
             user.inventory.chest_slot_3,
             user.inventory.chest_slot_4]

    if all(chest is not None for chest in slots):
        return 0

    chest_rarity = weighted_pick_from_buckets(constants.CHEST_ODDS) + 1
    chest = Chest.objects.create(user=user, rarity=chest_rarity)

    if user.inventory.chest_slot_1 is None:
        user.inventory.chest_slot_1 = chest
    elif user.inventory.chest_slot_2 is None:
        user.inventory.chest_slot_2 = chest
    elif user.inventory.chest_slot_3 is None:
        user.inventory.chest_slot_3 = chest
    elif user.inventory.chest_slot_4 is None:
        user.inventory.chest_slot_4 = chest

    user.inventory.save()

    return chest_rarity


class UploadResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data['result']

        win = valid_data['win']
        mode = valid_data['mode']
        opponent = valid_data['opponent_id']  # assume opponent's TournamentMember id if tourney mode
        stats = valid_data['stats']

        if mode == constants.QUICKPLAY:
            return handle_quickplay(request, win, opponent, stats)
        elif mode == constants.TOURNAMENT:  # tournament
            return handle_tourney(request, win, opponent)


def update_stats(user, win, stats):
    total_damage_dealt_stat = 0

    # Update stats per hero
    for stat in stats:
        char_id = stat['id']
        hero = Character.objects.select_related('char_type__basecharacterusage').get(char_id=char_id)

        try:
            hero.total_damage_dealt += stat['damage_dealt']
            total_damage_dealt_stat += stat['damage_dealt']
            hero.total_damage_taken += stat['damage_taken']
            hero.total_health_healed += stat['health_healed']
        except OverflowError:
            logging.error("stats overflow error")

        hero.num_games += 1
        hero.num_wins += 1 if win else 0
        hero.save()

        hero.char_type.basecharacterusage.num_games += 1
        hero.char_type.basecharacterusage.num_wins += 1 if win else 0
        hero.char_type.basecharacterusage.save()

        if win:
            QuestUpdater.game_won_by_char_id(user, hero.char_type.char_type)

    QuestUpdater.add_progress_by_type(user, constants.DAMAGE_DEALT, total_damage_dealt_stat)


def update_rating(original_elo, opponent, win):
    other_user = get_user_model().objects.select_related('userinfo').get(id=opponent)
    updated_rating = calculate_elo(original_elo, other_user.userinfo.elo, win)

    # update enemy elo
    other_user.userinfo.elo = calculate_elo(other_user.userinfo.elo, original_elo, not win)
    other_user.userinfo.save()

    return updated_rating


def handle_quickplay(request, win, opponent, stats):
    update_stats(request.user, win, stats)

    chest_rarity = 0
    coins = 0
    player_exp = 0

    user_stats = UserStats.objects.get(user=request.user)
    user_stats.num_games += 1

    if win:
        chest_rarity = award_chest(request.user)
        user_stats.num_wins += 1
        QuestUpdater.add_progress_by_type(request.user, constants.WIN_QUICKPLAY_GAMES, 1)

        dungeon_progress = DungeonProgress.objects.get(user=request.user)
        elo_scaler = 50 + math.floor(request.user.userinfo.elo / 10)
        reward_scaler = min(dungeon_progress.campaign_stage, elo_scaler)
        player_exp = formulas.player_exp_reward_quickplay(reward_scaler)

    user_stats.save()

    # rewards
    original_elo = request.user.userinfo.elo
    updated_rating = update_rating(original_elo, opponent, win)

    request.user.userinfo.elo = updated_rating
    request.user.userinfo.player_exp += player_exp
    request.user.userinfo.save()

    return Response({"elo": updated_rating, 'prev_elo': original_elo, 'coins': coins,
                     'player_exp': player_exp, 'chest_rarity': chest_rarity})


def handle_tourney(request, win, opponent):
    tournament_member = TournamentMember.objects.filter(user=request.user).first()

    if tournament_member is None:
        return Response({'status': False, 'reason': 'not competing in current tournament'})
    if tournament_member.fights_left <= 0:
        return Response({'status': False, 'reason': 'no fights left'})

    opponent_member = TournamentMember.objects.get(user_id=opponent)
    match_round = tournament_member.tournament.round - 1
    TournamentMatch.objects.filter(attacker=tournament_member, defender=opponent_member,
                                   round=match_round).update(is_win=win, has_played=True)
    tournament_member.fights_left -= 1

    if win:
        tournament_member.num_wins += 1
        tournament_member.rewards_left += 1
        opponent_member.num_losses += 1
    else:
        tournament_member.num_losses += 1
        opponent_member.num_wins += 1
    tournament_member.save()
    opponent_member.save()

    return Response({'status': True})
