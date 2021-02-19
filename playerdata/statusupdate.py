import logging
import multiprocessing

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import constants, formulas, rolls
from .questupdater import QuestUpdater
from .serializers import UploadResultSerializer

from playerdata.models import Character, DungeonProgress, Chest, Match
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

    chest_rarity = rolls.weighted_pick_from_buckets(constants.CHEST_ODDS) + 1
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


class UploadQuickplayResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data['result']

        win = valid_data['win']
        opponent = valid_data['opponent_id']
        stats = valid_data['stats']

        return handle_quickplay(request, win, opponent, stats)


class UploadTourneyResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data['result']

        win = valid_data['win']
        opponent = valid_data['opponent_id']

        return handle_tourney(request, win, opponent)


def update_stats(user, win, stats, _):
    user_stats = UserStats.objects.get(user=user)
    user_stats.num_games += 1
    user_stats.num_wins += 1 if win else 0
    user_stats.win_streak = 0 if not win else user_stats.win_streak + 1
    QuestUpdater.set_progress_by_type(user, constants.WIN_STREAK, user_stats.win_streak)
    user_stats.longest_win_streak = max(user_stats.win_streak, user_stats.longest_win_streak)
    user_stats.save()

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


def update_match_history(attacker, defender_id, win, _):
    # In the future there will be more processing for TTL, long-term retention,
    # caching and what not, but for now, let's keep it simple.
    Match.objects.create(attacker=attacker, defender_id=defender_id, is_win=win)


def update_rewards(user, elo, win, result_queue):
    """ Give the user chests and coins on victory."""
    if not win:
        result_queue.put({'coins': 0, 'chest_rarity': 0})
        return

    chest_rarity = award_chest(user)
    QuestUpdater.add_progress_by_type(user, constants.WIN_QUICKPLAY_GAMES, 1)

    coins = formulas.coins_chest_reward(elo, 1) / 20
    user.inventory.coins += coins
    user.inventory.save()
    result_queue.put({'coins': coins, 'chest_rarity': chest_rarity})
    

def update_elo_and_exp(user, win, opponent_id, result_queue):
    """ Update userinfo elo and player experience based on the match."""
    if win:
        dungeon_progress = DungeonProgress.objects.get(user=user)
        elo_scaler = 50 + math.floor(user.userinfo.elo / 10)
        reward_scaler = min(dungeon_progress.campaign_stage, elo_scaler)
        player_exp = formulas.player_exp_reward_quickplay(reward_scaler)
    else:
        player_exp = 0

    opponent = get_user_model().objects.select_related('userinfo').get(id=opponent_id)
    updated_rating = calculate_elo(user.userinfo.elo, opponent.userinfo.elo, win)

    # Update enemy elo if not a bot.
    if not opponent.userinfo.is_bot:
        opponent.userinfo.elo = calculate_elo(opponent.userinfo.elo, user.userinfo.elo, not win)
        opponent.userinfo.save()

    result_queue.put({'prev_elo': user.userinfo.elo})

    # Update our own elo and exp.
    user.userinfo.elo = updated_rating
    user.userinfo.player_exp += player_exp
    user.userinfo.save()
    result_queue.put({'elo': updated_rating, 'player_exp': player_exp})

    
def handle_quickplay(request, win, opponent, stats):
    jobs = []
    result_queue = multiprocessing.Queue()

    # update_stats(request.user, win, stats, result_queue)
    # update_match_history(request.user, opponent, win, result_queue)
    # update_rewards(request.user, request.user.userinfo.elo, win, result_queue)
    # update_elo_and_exp(request.user, win, opponent, result_queue)
    
    jobs.append(multiprocessing.Process(target=update_stats,
                                        args=(request.user, win, stats, result_queue)))
    jobs.append(multiprocessing.Process(target=update_match_history,
                                        args=(request.user, opponent, win, result_queue)))
    jobs.append(multiprocessing.Process(target=update_rewards,
                                        args=(request.user, request.user.userinfo.elo, win, result_queue)))
    jobs.append(multiprocessing.Process(target=update_elo_and_exp,
                                        args=(request.user, win, opponent, result_queue)))
    for j in jobs:
        j.start()

    res = {}
    for _ in range(3):
    # while not result_queue.empty():
         partial_res = result_queue.get()
         res.update(partial_res)

    for j in jobs:
        j.join()

    print(res)
    return Response(res)


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


class SkipCostView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        coins_cost = formulas.coins_chest_reward(request.user.userinfo.elo, 1) / 30
        gems_cost = 0

        if request.user.inventory.coins < coins_cost:
            coins_cost = 0
            gems_cost = 2

        return Response({'coins_cost': coins_cost, 'gems_cost': gems_cost})


class SkipView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        cost = formulas.coins_chest_reward(request.user.userinfo.elo, 1) / 30

        if request.user.inventory.coins >= cost:
            request.user.inventory.coins -= cost
        elif request.user.inventory.gems >= constants.SKIP_GEM_COST:
            request.user.inventory.gems -= constants.SKIP_GEM_COST
        else:
            return Response({'status': False, 'reason': 'not enough gems to skip!'})

        request.user.inventory.save()
        return Response({'status': True})
