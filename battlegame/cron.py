from playerdata import constants
from playerdata.constants import TOURNEY_SIZE
from playerdata.models import User
from playerdata.models import ActiveDailyQuest, get_expiration_date
from playerdata.models import ActiveWeeklyQuest
from playerdata.models import PlayerQuestDaily
from playerdata.models import PlayerQuestWeekly
from playerdata.models import Tournament
from playerdata.models import TournamentMatch
from playerdata.models import TournamentMember
from playerdata.models import TournamentRegistration
from playerdata.models import Placement
from playerdata.tournament import get_next_round_time, TOURNAMENT_BOTS

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
