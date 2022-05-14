import statistics

import requests
from django.db.transaction import atomic
from sentry_sdk import capture_exception
from django_redis import get_redis_connection
from datetime import timedelta
from playerdata import tier_system, relic_shop, refunds, base, resource_shop, server, regal_rewards
from playerdata.antihacking import MatchValidator
from playerdata.constants import TOURNEY_SIZE
from playerdata.daily_dungeon import daily_dungeon_team_gen_cron
from playerdata.dungeon import get_redis_dungeon_winrate_key
from playerdata.models import *
from playerdata.purchases import refresh_daily_deals_cronjob, refresh_weekly_deals_cronjob, \
    refresh_monthly_deals_cronjob
from playerdata.quest import refresh_daily_quests, refresh_weekly_quests
from playerdata.statusupdate import calculate_tourney_elo, get_redis_quickplay_usage_key, skip_cap
from playerdata.tournament import get_next_round_time, TOURNAMENT_BOTS, get_random_char_set
from . import settings
from .jobs import update_redis_player_elos

"""
For reference:
Add/update cron job: `python manage.py crontab add`
Remove all jobs:" `python manage.py crontab remove`

To check what jobs are actually scheduled on crontab: `crontab -l`
Double check that crontab on the server is running on UTC timezone
"""

def cron(uuid=None, retries=0):
    def notify_success():
        if uuid is not None and not settings.DEVELOPMENT:
            try:
                requests.get("https://hc-ping.com/%s" % uuid, timeout=10)
            except requests.RequestException as e:
                cron_logger("Failed to ping hc: %s" % e)

    def cron_logger(s):
        # TODO: we should definately just use the logging package.
        print("[%s] %s" % (datetime.now().strftime("%d/%m/%Y %H:%M:%S"), s))

    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = retries + 1
            for i in range(attempts):
                cron_logger("Running %s, attempt (%d/%d)." % (func.__name__, i + 1, attempts))
                try:
                    ret = func(*args, **kwargs)
                    cron_logger("Success!")
                    notify_success()
                    return ret
                except Exception as e:
                    cron_logger("Caught error: %s" % e)
                    capture_exception(e)
            return None
        return wrapper
    return inner


@cron(uuid="75a7e314-2bb2-48e8-b319-1f813dd86999")
def daily_quests_cron():
    # remove top 3 from daily
    refresh_daily_quests()


@cron(uuid="40561eec-8a6c-4485-b9ae-838f1b229c39")
def weekly_quests_cron():
    # remove top 5 from weekly
    refresh_weekly_quests()


@cron(uuid="3f6f9ed0-ef95-4a56-b27d-968e2bf3678d")
def daily_deals_cron():
    refresh_daily_deals_cronjob()


@cron(uuid="e89b6f19-473b-42d1-9093-25aac7e57ad3")
def weekly_deals_cron():
    refresh_weekly_deals_cronjob()


@cron(uuid="e84bbafc-c0f2-4c69-9f7d-f59b5d9d3b8d")
def monthly_deals_cron():
    refresh_monthly_deals_cronjob()


@cron(uuid="222e1a79-98e1-4d9f-8d74-6dcf31cb00bd")
@atomic
def daily_clean_matches_cron():
    # Validate matches in the last day.
    validator = MatchValidator(sample_rate=1)
    for mr in MatchReplay.objects.filter(uploaded_at__gte=timezone.now() - timedelta(days=1)):
        validator.validate(mr.match, mr)
    
    Match.objects.filter(uploaded_at__lte=timezone.now() - timedelta(days=14)).delete()
    MatchReplay.objects.filter(uploaded_at__lte=timezone.now() - timedelta(days=14)).delete()


@cron(uuid="cb651e8b-e227-4be1-a786-acd6fcac037c")
def reset_daily_wins_cron():
    with atomic():
        user_stats = UserStats.objects.filter(daily_wins__gt=0, daily_games__gt=0)
        base.user_lock_related_users(user_stats)
        user_stats.update(daily_wins=0, daily_games=0)

    with atomic():
        user_stats = UserStats.objects.filter(num_games__gt=0).select_related('user__userinfo').exclude(user__userinfo__isnull=True)
        base.user_lock_related_users(user_stats)
        for stat in user_stats:
            stat.pvp_skips = skip_cap(stat.user.userinfo)
        UserStats.objects.bulk_update(user_stats, ['pvp_skips'])
    update_redis_player_elos()


@cron(uuid="84a58d71-49a3-4744-b5f8-f9ed9f557459")
def reset_resource_shop_cron():
    resource_shop.reset_resource_shop()


MAX_DAILY_DUNGEON_TICKET = 5
MAX_DAILY_DUNGEON_GOLDEN_TICKET = 3


@cron(uuid="8c7cdffd-d2bb-4fff-8a12-57666965db8c")
@atomic
def daily_dungeon_golden_ticket_drop():
    to_inc = Inventory.objects.filter(daily_dungeon_golden_ticket__lt=MAX_DAILY_DUNGEON_GOLDEN_TICKET)
    for inv in to_inc:
        inv.daily_dungeon_golden_ticket += 1
    Inventory.objects.bulk_update(to_inc, ['daily_dungeon_golden_ticket'])


@cron(uuid="f7ca56fc-0970-4ba7-9b18-80fa81833e3e")
@atomic
def daily_dungeon_ticket_drop():
    to_inc = Inventory.objects.filter(daily_dungeon_ticket__lt=MAX_DAILY_DUNGEON_TICKET)
    for inv in to_inc:
        inv.daily_dungeon_ticket += 1
    Inventory.objects.bulk_update(to_inc, ['daily_dungeon_ticket'])


@cron(uuid="b843e92a-fb04-4332-831f-e086cc4ffe5e")
def refresh_daily_dungeon():
    daily_dungeon_team_gen_cron()


@cron(uuid="3f972350-ea40-40cf-bb94-36a68b3f5d5b")
def reset_season():
    tier_system.restart_season()


@cron(uuid="fec82791-ace6-4e2c-aeb3-a987d538e7c9")
def refresh_relic_shop():
    relic_shop.refresh_shop()


@cron(uuid="5e327e1e-e954-45b7-815d-7feed9f7c6ca")
def refund_google():
    refunds.google_refund_cron()


@cron(uuid="ffe37586-9527-4b2c-9989-19d359c291a5")
def update_clan_leaderboards_cron():
    if not server.is_server_version_higher('1.1.0'):
        return
    clans = Clan2.objects.all()
    userinfos = UserInfo.objects.exclude(clanmember__clan2=None).values('clanmember__clan2__name', 'elo')
    elo_sums = defaultdict(int)

    # for all members in the clan, update the leaderboard
    for userinfo in userinfos:
        clan_name = userinfo['clanmember__clan2__name']
        elo_sums[clan_name] += userinfo['elo']

    for clan in clans:
        clan.elo = elo_sums[clan.name]

    with atomic():
        Clan2.objects.bulk_update(clans, ['elo'])


@cron(uuid="fcdb9373-7a08-4bd6-a0ce-5070c0259f0d")
def grass_event_token_drop_cron():
    grass_events = GrassEvent.objects.all()
    for event in grass_events:
        event.tickets += 1

    GrassEvent.objects.bulk_update(grass_events, ['tickets'])


@cron(uuid="6732858b-80ab-4d3f-88c1-c0a45f7a629e")
def regal_rewards_cron():
    regal_rewards.reset_regal_rewards_cron()


# Take all registered users
# Sort by elo
# Create tourney groups of 8
def setup_tournament():
    reg_users = TournamentRegistration.objects.order_by('-user__userinfo__elo')
    group_member_count = 0
    round_expiration = get_next_round_time()
    tournament_list = []

    tourney = Tournament.objects.create(round_expiration=round_expiration)

    for reg_user in reg_users:
        if group_member_count >= TOURNEY_SIZE:
            tourney = Tournament.objects.create(round_expiration=round_expiration)
            group_member_count = 0

        placement = Placement.objects.create(user=reg_user.user, is_tourney=True)
        tournament_member = TournamentMember(user=reg_user.user, tournament=tourney, defence_placement=placement)
        tournament_list.append(tournament_member)
        group_member_count += 1

    # make last group with bots to pad empty spots
    num_bots_needed = TOURNEY_SIZE - group_member_count
    while num_bots_needed > 0:
        placement = Placement.objects.create(user_id=TOURNAMENT_BOTS[num_bots_needed - 1],
                                             is_tourney=True)
        tournament_member = TournamentMember(user_id=TOURNAMENT_BOTS[num_bots_needed - 1],
                                             tournament=tourney, defence_placement=placement)
        tournament_list.append(tournament_member)
        num_bots_needed -= 1

    TournamentMember.objects.bulk_create(tournament_list)

    # clean up
    TournamentRegistration.objects.all().delete()

    next_round()


def _play_bot_moves():
    bots = TournamentMember.objects.filter(user_id__in=TOURNAMENT_BOTS)
    bot_matches = TournamentMatch.objects.filter(attacker__user_id__in=TOURNAMENT_BOTS)
    tourney_round = bot_matches.first().round if len(bot_matches) > 0 else 0

    for bot in bots:
        # pick cards
        selection_num = 2 if tourney_round <= 2 else 1
        card_hand = get_random_char_set(5)[:selection_num]
        for card in card_hand:
            new_char = Character.objects.create(user=bot.user, char_type_id=card, is_tourney=True)
            TournamentTeam.objects.create(user=bot.user, character=new_char)
        bot.has_picked = True
        bot.save()

        # TODO: refactor this along with other placement refactor
        # set defense
        team = TournamentTeam.objects.filter(user=bot.user).order_by('?')  # order_by('?') not expensive since small set

        bot.defence_placement.pos_1 = 12
        bot.defence_placement.pos_2 = 13
        bot.defence_placement.char_1 = team[0].character
        bot.defence_placement.char_2 = team[1].character

        bot.defence_placement.pos_3 = 14 if len(team) > 2 else -1
        bot.defence_placement.pos_4 = 15 if len(team) > 3 else -1
        bot.defence_placement.pos_5 = 16 if len(team) > 4 else -1

        bot.defence_placement.char_3 = team[2].character if len(team) > 2 else None
        bot.defence_placement.char_4 = team[3].character if len(team) > 3 else None
        bot.defence_placement.char_5 = team[4].character if len(team) > 4 else None
        bot.defence_placement.save()

    for match in bot_matches:
        is_win = random.randint(0, 1) == 1
        match.is_win = is_win
        match.has_played = True
        if is_win:
            match.attacker.num_wins += 1
            match.defender.num_losses += 1
        else:
            match.defender.num_wins += 1
            match.attacker.num_losses += 1
        match.attacker.save()
        match.defender.save()
        match.save()


# Returns list of matches to be created
def _make_matches(tourney_members):
    matches_list = []
    if len(tourney_members) == 4:
        for i, member in enumerate(tourney_members):
            for defender in tourney_members:
                if defender != member:
                    match = TournamentMatch(attacker=member, defender=defender, round=member.tournament.round)
                    matches_list.append(match)

    elif len(tourney_members) == 6:
        # the player at index i plays each group of 3 defenders
        # so player 0 plays [1, 2, 3], player 3 plays [0, 4, 5]
        matches_for_6 = [[1, 2, 3], [0, 2, 4], [0, 1, 5], [0, 4, 5], [1, 3, 5], [2, 3, 4]]
        for i, matches in enumerate(matches_for_6):
            for defender in matches:
                match = TournamentMatch(attacker=tourney_members[i], defender=tourney_members[defender],
                                        round=tourney_members[i].tournament.round)
                matches_list.append(match)
    else:
        return

    return matches_list


def next_round():
    _play_bot_moves()

    # handle unfinished users (games not played)
    # lose all ppl who didn't play their matches
    unplayed_matches = TournamentMatch.objects.filter(has_played=False)

    for match in unplayed_matches:
        match.is_win = False
        match.has_played = True

        match.attacker.num_losses += 1
        match.defender.num_wins += 1

        match.attacker.save()
        match.defender.save()

    TournamentMatch.objects.bulk_update(unplayed_matches, ['is_win', 'has_played'])

    # eliminate bottom two in round  >= 3
    # sort by group, sort by losses, in each group, delete first two
    tournaments = Tournament.objects.all()
    members_to_update = []
    tournies_to_update = []
    matches_to_update = []
    userinfos_to_update = []

    # for each tournament
    # eliminate players, make new matches, update tournament info
    for tourney in tournaments:
        # eliminate players with most losses
        group_members = TournamentMember.objects.filter(tournament=tourney, is_eliminated=False).order_by('-num_losses')
        tourney_round = tourney.round

        if tourney_round >= 3:
            group_members[0].is_eliminated = True
            group_members[1].is_eliminated = True
            group_members[0].save()
            group_members[1].save()

        # Make matches for next day
        # in each group, 8: 4/4, 6:special one, 4 again
        if tourney_round <= 2:
            # split into groups of 4 and battle it out
            matches_to_update.extend(_make_matches(group_members[4:]))
            matches_to_update.extend(_make_matches(group_members[:4]))
        elif tourney_round == 3:
            matches_to_update.extend(_make_matches(group_members[2:]))
        elif tourney_round == 4:
            matches_to_update.extend(_make_matches(group_members[2:]))
        elif tourney_round == 5:
            userinfos_to_update.extend(_update_elo(tourney))

        for member in group_members:
            member.has_picked = False
            member.fights_left = 3
            members_to_update.append(member)

        tourney.round += 1
        tourney.round_expiration = get_next_round_time()
        tournies_to_update.append(tourney)

    # bulk update
    Tournament.objects.bulk_update(tournies_to_update, ['round', 'round_expiration'])
    TournamentMember.objects.bulk_update(members_to_update, ['has_picked', 'fights_left'])
    TournamentMatch.objects.bulk_create(matches_to_update)
    UserInfo.objects.bulk_update(userinfos_to_update, ['tourney_elo'])


def _update_elo(tourney):
    # update all elo's
    group_members = TournamentMember.objects.filter(tournament=tourney).order_by('-num_wins')

    userinfo_list = []
    avg_elo = statistics.mean(member.user.userinfo.tourney_elo for member in group_members)

    for standing, member in enumerate(group_members):
        member.user.userinfo.prev_tourney_elo = member.user.userinfo.tourney_elo
        member.user.userinfo.tourney_elo = calculate_tourney_elo(member.user.userinfo.tourney_elo, avg_elo, standing)
        userinfo_list.append(member.user.userinfo)

    return userinfo_list


def end_tourney():
    # clean up
    Character.objects.filter(is_tourney=True).delete()
    TournamentTeam.objects.all().delete()
    TournamentMember.objects.all().delete()
    Tournament.objects.all().delete()


@cron(uuid='788e2963-6794-4011-a4b2-baf7c0c1b1dd')
@atomic
def expire_creator_codes():
    expiretime = datetime.utcnow() - timedelta(days=7)
    CreatorCodeTracker.objects.filter(created_time__lt=expiretime).update(is_expired=True)


# Regularly save quickplay usage numbers from redis to the db.
def push_quickplay_usage_to_db():
    r = get_redis_connection("default")
    # Increment every base character usage object by what we have stored
    all_usage = BaseCharacterUsage.objects.all()
    for single_usage in all_usage:
        redis_key = get_redis_quickplay_usage_key(single_usage.char_type.char_type)

        for index in range(0, len(single_usage.num_games_buckets)):
            redis_bucket_key = f"{redis_key}_{index}"
            games = r.get(f"{redis_bucket_key}_games")
            if games == 0:
                continue
            wins = r.get(f"{redis_bucket_key}_wins")
            def_games = r.get(f"{redis_bucket_key}_defense_games")
            def_wins = r.get(f"{redis_bucket_key}_defense_wins")
            if games is not None:
                single_usage.num_games_buckets[index] += int(games)
            if wins is not None:
                single_usage.num_wins_buckets[index] += int(wins)
            if def_games is not None:
                single_usage.num_defense_games_buckets[index] += int(def_games)
            if def_wins is not None:
                single_usage.num_defense_wins_buckets[index] += int(def_wins)
            # Also clear redis after recording.
            r.set(f"{redis_bucket_key}_games", 0)
            r.set(f"{redis_bucket_key}_wins", 0)
            r.set(f"{redis_bucket_key}_defense_games", 0)
            r.set(f"{redis_bucket_key}_defense_wins", 0)

    BaseCharacterUsage.objects.bulk_update(all_usage, ['num_games_buckets', 'num_wins_buckets',
                                                       'num_defense_games_buckets', 'num_defense_wins_buckets'])


# Regularly save dungeon winrate numbers from redis to the db.
def push_dungeon_games_to_db():
    r = get_redis_connection("default")
    # Increment every base character usage object by what we have stored
    all_stats = DungeonStats.objects.all()
    for stage_stats in all_stats:
        redis_key = get_redis_dungeon_winrate_key(stage_stats.dungeon_type, stage_stats.stage)

        games = r.get(f"{redis_key}_games")
        if games == 0:
            continue
        wins = r.get(f"{redis_key}_wins")

        if games is not None:
            stage_stats.games += int(games)
        if wins is not None:
            stage_stats.wins += int(wins)
        r.set(f"{redis_key}_games", 0)
        r.set(f"{redis_key}_wins", 0)

    DungeonStats.objects.bulk_update(all_stats, ['wins', 'games'])


# We will automatically simulate reported matches.
def process_hacker_alerts():
    reports = HackerAlert.objects.filter(match_simulated=False, skip_simulation=False).select_related('suspicious_match')
    updated_reports = []
    reports_simulated = 0
    now = datetime.utcnow()

    MAX_REPORTS_TO_SIM_IN_ONE_JOB = 10
    SIM_SERVER_HOSTNAME = "127.0.0.1"
    SIM_PORT = "8007"

    for report in reports:
        # Try to get the replay, if not just flag as unreachable so we don't keep trying.
        reported_match = report.suspicious_match
        if reported_match is None:
            report.skip_simulation = True
            updated_reports.append(report)
            continue
        if ServerStatus.latest_version() != reported_match.version:
            report.skip_simulation = True
            updated_reports.append(report)
            continue
        replay = MatchReplay.objects.filter(match=reported_match).first()
        if replay is None:
            report.skip_simulation = True
            updated_reports.append(report)
            continue

        # Get placement from replay
        seed = replay.seed
        # teams are formatted correctly as placementjson strings already.
        attacking_team = replay.attacking_team
        defending_team = replay.defending_team
        jsonStr = json.dumps([attacking_team, defending_team])  # Local sim server accepts array of two placementjson strings.
        # Simulate the game
        reports_simulated += 1
        try:
            response = requests.get(f'http://{SIM_SERVER_HOSTNAME}:{SIM_PORT}/simulate/{seed}', data=jsonStr, timeout=1)
        except requests.Timeout:
            break  # Stop until next cron job if we timeout, or it might hurt server performance for a noticeable time
        except:
            continue

        win = (response.content == b"True")
        # Set flags to show that we've simulated the report, and flag if it doesn't match.
        report.match_simulated = True
        report.match_simulated_time = now
        report.match_simulated_alert = not (win == reported_match.is_win)
        updated_reports.append(report)

        # Since this is a regular cron job, we'll cap the amount of matches to process so we don't kill the server if there's some spam reports.
        if reports_simulated >= MAX_REPORTS_TO_SIM_IN_ONE_JOB:
            break

    HackerAlert.objects.bulk_update(updated_reports, ['skip_simulation',
                                    'match_simulated', 'match_simulated_time', 'match_simulated_alert'])
