import random
import statistics

from playerdata import constants
from playerdata.constants import TOURNEY_SIZE
from playerdata.models import UserInfo
from playerdata.models import User, Character, TournamentTeam
from playerdata.models import ActiveDailyQuest, get_expiration_date
from playerdata.models import ActiveWeeklyQuest
from playerdata.models import PlayerQuestDaily
from playerdata.models import PlayerQuestWeekly
from playerdata.models import Tournament
from playerdata.models import TournamentMatch
from playerdata.models import TournamentMember
from playerdata.models import TournamentRegistration
from playerdata.models import Placement
from playerdata.statusupdate import calculate_tourney_elo
from playerdata.tournament import get_next_round_time, TOURNAMENT_BOTS, get_random_char_set

"""
For reference:
Add/update cron job: `python manage.py crontab add`
Remove all jobs:" `python manage.py crontab remove`

To check what jobs are actually scheduled on crontab: `crontab -l`
Double check that crontab on the server is running on UTC timezone
"""


# https://stackoverflow.com/questions/57167237/how-to-delete-first-n-items-from-queryset-in-django
def _delete_first_n_rows(quest_class, n):
    quest_class.objects.filter(
        id__in=list(quest_class.objects.values_list('pk', flat=True)[:n])).delete()


def daily_quests_cron():
    # remove top 3 from daily
    print("running daily quest reset cronjob")

    _delete_first_n_rows(ActiveDailyQuest, constants.NUM_DAILY_QUESTS)
    PlayerQuestDaily.objects.all().delete()

    # pull new ones and make them for every user
    active_quests = ActiveDailyQuest.objects.all()[:constants.NUM_DAILY_QUESTS]
    expiry_date = get_expiration_date(1)
    users = User.objects.all()
    bulk_quests = []
    for quest in active_quests:
        for user in users:
            player_quest = PlayerQuestDaily(base_quest=quest.base_quest, user=user, expiration_date=expiry_date)
            bulk_quests.append(player_quest)

    PlayerQuestDaily.objects.bulk_create(bulk_quests)
    print("daily quest cronjob complete!")


def weekly_quests_cron():
    # remove top 5 from weekly
    print("running weekly quest reset cronjob")

    _delete_first_n_rows(ActiveWeeklyQuest, constants.NUM_WEEKLY_QUESTS)
    PlayerQuestWeekly.objects.all().delete()

    # pull new ones and make them for every user
    active_quests = PlayerQuestWeekly.objects.all()[:constants.NUM_WEEKLY_QUESTS]
    expiry_date = get_expiration_date(7)
    users = User.objects.all()
    bulk_quests = []
    for quest in active_quests:
        for user in users:
            player_quest = PlayerQuestWeekly(base_quest=quest.base_quest, user=user, expiration_date=expiry_date)
            bulk_quests.append(player_quest)

    PlayerQuestWeekly.objects.bulk_create(bulk_quests)
    print("weekly quest cronjob complete!")


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

        placement = Placement.objects.create()
        tournament_member = TournamentMember(user=reg_user.user, tournament=tourney, defence_placement=placement)
        tournament_list.append(tournament_member)
        group_member_count += 1

    # make last group with bots to pad empty spots
    num_bots_needed = TOURNEY_SIZE - group_member_count
    while num_bots_needed > 0:
        placement = Placement.objects.create()
        tournament_member = TournamentMember(user_id=TOURNAMENT_BOTS[num_bots_needed - 1],
                                             tournament=tourney, defence_placement=placement)
        tournament_list.append(tournament_member)
        num_bots_needed -= 1

    TournamentMember.objects.bulk_create(tournament_list)

    # clean up
    TournamentRegistration.objects.all().delete()


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


def next_round(self, request, queryset):
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
    TournamentMember.objects.bulk_update(members_to_update, ['has_picked'])
    TournamentMatch.objects.bulk_create(matches_to_update)
    UserInfo.objects.bulk_update(userinfos_to_update, ['tourney_elo'])


def _update_elo(tourney):
    # update all elo's
    group_members = TournamentMember.objects.filter(tournament=tourney).order_by('-num_wins')

    userinfo_list = []
    avg_elo = statistics.mean(member.user.userinfo.tourney_elo for member in group_members)

    for standing, member in enumerate(group_members):
        member.user.userinfo.prev_tourney_elo = member.user.userinfo.tourney_elo
        member.user.userinfo.tourney_elo = max(calculate_tourney_elo(member.user.userinfo.tourney_elo, avg_elo, standing), 0)
        userinfo_list.append(member.user.userinfo)

    return userinfo_list


def end_tourney():
    # clean up
    TournamentTeam.objects.all().delete()
    TournamentMember.objects.all().delete()
    Tournament.objects.all().delete()
