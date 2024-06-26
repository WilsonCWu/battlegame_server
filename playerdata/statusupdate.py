import collections
import math

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.transaction import atomic
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata.models import DungeonProgress, Chest, Match, MatchReplay
from playerdata.models import ServerStatus
from playerdata.models import TournamentMatch
from playerdata.models import TournamentMember
from playerdata.models import UserStats
from . import constants, formulas, rolls, tier_system, server, pvp_queue, matcher, afk_rewards, leaderboards, base
from .formulas import vip_exp_to_level
from .questupdater import QuestUpdater
from .serializers import UploadResultSerializer, BotResultsSerializer


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

    # pity for gold chests, if 6 silver chests in a row then we drop a gold
    if chest_rarity == constants.ChestType.SILVER.value:
        user.userstats.silver_chest_counter += 1
        if user.userstats.silver_chest_counter == 6:
            chest_rarity = constants.ChestType.GOLD.value
            user.userstats.silver_chest_counter = 0
    elif chest_rarity == constants.ChestType.GOLD.value:
        user.userstats.silver_chest_counter = 0

    # chest cycle: drop 4 mythical chests in 240 quickplay chests
    user.userstats.chest_counter += 1
    if user.userstats.chest_counter in [28, 91, 153, 212]:
        chest_rarity = constants.ChestType.MYTHICAL.value
    if user.userstats.chest_counter >= 240:
        user.userstats.chest_counter = 0
    user.userstats.save()

    tier_rank = tier_system.elo_to_tier(user.userinfo.elo)
    chest = Chest.objects.create(user=user, rarity=chest_rarity, tier_rank=tier_rank.value)

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

    @atomic
    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data['result']

        win = valid_data['win']
        opponent = valid_data['opponent_id']
        stats = valid_data['stats']
        seed = valid_data['seed'] if 'seed' in valid_data else 0
        attacking_team = valid_data['attacking_team'] if 'attacking_team' in valid_data else None
        defending_team = valid_data['defending_team'] if 'defending_team' in valid_data else None

        return handle_quickplay(request, win, opponent, stats, seed, attacking_team, defending_team)


class UploadTourneyResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data['result']

        win = valid_data['win']
        opponent = valid_data['opponent_id']

        return handle_tourney(request, win, opponent)


def update_stats(user, win, stats):
    user_stats = user.userstats
    user_stats.num_games += 1
    user_stats.pvp_skips += min(3, skip_cap(user.userinfo) - user_stats.pvp_skips)
    user_stats.num_wins += 1 if win else 0
    user_stats.daily_wins += 1 if win else 0
    user_stats.daily_games += 1
    user_stats.win_streak = 0 if not win else user_stats.win_streak + 1
    user_stats.longest_win_streak = max(user_stats.win_streak, user_stats.longest_win_streak)
    user_stats.save()

    total_damage_dealt_stat = 0
    for stat in stats:
        total_damage_dealt_stat += stat['damage_dealt']
    QuestUpdater.add_progress_by_type(user, constants.DAMAGE_DEALT, total_damage_dealt_stat)
    QuestUpdater.set_progress_by_type(user, constants.WIN_STREAK, user_stats.win_streak)


def reduce_low_elo_loss(original_elo, new_elo):
    if not server.is_server_version_higher("0.5.0"):
        return new_elo

    diff = new_elo - original_elo
    if diff > 0:
        return new_elo

    if original_elo <= 100:
        return original_elo + (diff / 4)  # Only lose 1/4 of the full amount
    elif original_elo <= 200:
        return original_elo + (diff / 3)  # Only lose 1/3 of the full amount
    elif original_elo <= 600:
        return original_elo + (diff / 2)  # Lose 1/2 of the full amount
    elif original_elo <= 1000:
        return original_elo + min(diff + 3, -1)
    elif original_elo <= 1500:
        return original_elo + min(diff + 2, -1)
    elif original_elo <= 3000:
        return original_elo + min(diff + 1, -1)
    else:
        return new_elo


def update_rating(original_elo, opponent, win):
    other_user = get_user_model().objects.select_related('userinfo').get(id=opponent)
    new_elo = calculate_elo(original_elo, other_user.userinfo.elo, win)
    updated_rating = reduce_low_elo_loss(original_elo, new_elo)

    original_opponent_elo = other_user.userinfo.elo
    updated_opponent_elo = other_user.userinfo.elo

    # update enemy elo if not a bot
    if not other_user.userinfo.is_bot:
        updated_opponent_elo = calculate_elo(other_user.userinfo.elo, original_elo, not win)
        other_user.userinfo.elo = reduce_low_elo_loss(original_opponent_elo, updated_opponent_elo)
        other_user.userinfo.save()
        leaderboards.update_redis_ranking(opponent, other_user.userinfo.elo, leaderboards.pvp_ranking_key())

    EloUpdates = collections.namedtuple('EloUpdated',
                                        ['attacker_original', 'attacker_new',
                                         'defender_original', 'defender_new'])
    return EloUpdates(original_elo, updated_rating,
                      original_opponent_elo, updated_opponent_elo)


def update_match_history(attacker, defender_id, win, elo_updates, seed, attacking_team, defending_team):
    match = Match.objects.create(attacker=attacker,
                                 defender_id=defender_id,
                                 is_win=win,
                                 match_type='Q',
                                 version=ServerStatus.latest_version(),
                                 original_attacker_elo=elo_updates.attacker_original,
                                 updated_attacker_elo=elo_updates.attacker_new,
                                 original_defender_elo=elo_updates.defender_original,
                                 updated_defender_elo=elo_updates.defender_new)

    if attacking_team and defending_team:
        MatchReplay.objects.create(match=match,
                                seed=seed,
                                attacking_team=attacking_team,
                                defending_team=defending_team)
    return match.id


# Character type is an int
def get_redis_quickplay_usage_key(char_type):
    return f"quickplay_usage_{char_type}"


# When changing the bucket size, clear the existing data, or it'll be nonsense
def get_quickplay_usage_bucket(elo):
    return str(int(elo / constants.USAGE_BUCKET_ELO_SIZE))


def save_usage_into_redis(team, win, elo, key_append):
    r = get_redis_connection("default")
    chars = ['char_1', 'char_2', 'char_3', 'char_4', 'char_5']
    for char_num in chars:
        if(team[char_num] is None or team[char_num]['char_type'] == 0):
            continue
        char_type = team[char_num]['char_type']
        base_key = get_redis_quickplay_usage_key(char_type)
        bucket_num = get_quickplay_usage_bucket(elo)
        key = f"{base_key}_{bucket_num}{key_append}"
        r.incr(f"{key}_games")
        if win:
            r.incr(f"{key}_wins")


def handle_quickplay(request, win, opponent, stats, seed, attacking_team, defending_team):
    base.user_lock_ids([request.user.id])

    # Should be handled by client, so this will only be triggered by spoofed API calls or a glitch.
    if request.user.userstats.daily_games > constants.MAX_DAILY_QUICKPLAY_GAMES:
        return Response({'status': False, 'reason': 'Max daily quickplay games exceeded'})

    update_stats(request.user, win, stats)
    save_usage_into_redis(attacking_team, win, request.user.userinfo.elo, "")
    save_usage_into_redis(defending_team, not win, request.user.userinfo.elo, "_defense")

    chest_rarity = 0
    coins = 0
    player_exp = 0
    runes = 0

    original_elo = request.user.userinfo.elo
    elo_updates = update_rating(original_elo, opponent, win)

    match_id = update_match_history(request.user, opponent, win, elo_updates, seed, attacking_team, defending_team)

    if win:
        if tier_system.elo_to_tier(elo_updates.attacker_new).value > request.user.userinfo.tier_rank:
            request.user.userinfo.tier_rank = tier_system.elo_to_tier(elo_updates.attacker_new).value

        vip_level = vip_exp_to_level(request.user.userinfo.vip_exp)
        runes = afk_rewards.PVP_RUNE_REWARD

        afkrewards = afk_rewards.evaluate_afk_reward_ticks(request.user.afkreward,
                                                           vip_level, afk_rewards.PVP_RUNE_REWARD)
        if afkrewards.runes_left == afk_rewards.get_accumulated_runes_limit(vip_level):
            runes = afk_rewards.RUNES_FULL

        QuestUpdater.add_progress_by_type(request.user, constants.WIN_QUICKPLAY_GAMES, 1)
        QuestUpdater.add_progress_by_type(request.user, constants.WIN_X_TROPHIES, elo_updates.attacker_new - elo_updates.attacker_original)

    # rewards
    if request.user.userstats.daily_wins <= constants.MAX_DAILY_QUICKPLAY_WINS_FOR_GOLD and win:
        coins = formulas.coins_chest_reward(request.user, constants.ChestType.SILVER.value) * 0.15
        request.user.inventory.coins += coins
        request.user.inventory.save()

        dungeon_progress = DungeonProgress.objects.get(user=request.user)
        elo_scaler = 50 + math.floor(request.user.userinfo.elo / 10)
        reward_scaler = min(dungeon_progress.campaign_stage, elo_scaler)
        player_exp = formulas.player_exp_reward_quickplay(reward_scaler)

    request.user.userinfo.highest_elo = max(request.user.userinfo.highest_elo, elo_updates.attacker_new)
    request.user.userinfo.highest_season_elo = max(request.user.userinfo.highest_season_elo, elo_updates.attacker_new)
    tier_system.complete_any_elo_rewards(request.user.userinfo.highest_season_elo, request.user.elorewardtracker)

    request.user.userinfo.elo = elo_updates.attacker_new
    formulas.level_up_check(request.user.userinfo, player_exp)
    request.user.userinfo.player_exp += player_exp
    request.user.userinfo.save()

    pvp_queue.pop_pvp_queue(request.user)
    leaderboards.update_redis_ranking(request.user.id, request.user.userinfo.elo, leaderboards.pvp_ranking_key())

    return Response({'status': True,
                     'elo': elo_updates.attacker_new, 'prev_elo': original_elo,
                     'coins': coins, 'player_exp': player_exp,
                     'chest_rarity': chest_rarity, 'match_id': match_id,
                     'daily_wins': request.user.userstats.daily_wins,
                     'runes': runes})


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


def skip_cap(userinfo):
    player_level = formulas.exp_to_level(userinfo.player_exp)
    base = 5
    additional = player_level // 5
    return base + additional


def is_skip_capped(user):
    return user.userstats.pvp_skips >= skip_cap(user.userinfo)


class SkipsLeftView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        is_skips_capped = is_skip_capped(request.user)
        return Response({'status': True, 'skips_left': request.user.userstats.pvp_skips, 'is_capped': is_skips_capped})


class SkipView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        if request.user.userstats.pvp_skips <= 0:
            return Response({'status': False, 'reason': 'No more skips left today!'})

        request.user.userstats.pvp_skips -= 1
        request.user.userstats.save()

        next_opponent_id = pvp_queue.pop_pvp_queue(request.user)
        query = matcher.userinfo_preloaded().filter(user_id=next_opponent_id).first()
        enemy = matcher.UserInfoSchema(query)
        return Response({'status': True, 'next_enemy': enemy.data})


# TODO: add tests for this
class PostBotResultsView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = BotResultsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id1s = serializer.validated_data['id1s']
        id2s = serializer.validated_data['id2s']
        wons = serializer.validated_data['wons']

        for id1, id2, won in zip(id1s, id2s, wons):
            # get old elos
            user1 = get_user_model().objects.select_related('userinfo').get(id=id1)
            user2 = get_user_model().objects.select_related('userinfo').get(id=id2)
            prev_elo_1 = user1.userinfo.elo
            prev_elo_2 = user2.userinfo.elo

            # calculate and save new elos
            user1.userinfo.elo = calculate_elo(prev_elo_1, prev_elo_2, won)
            user2.userinfo.elo = calculate_elo(prev_elo_2, prev_elo_1, not won)

            user1.userinfo.save()
            user2.userinfo.save()

        return Response({'status': True})
