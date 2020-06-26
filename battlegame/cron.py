from playerdata import constants
from playerdata.models import User
from playerdata.models import ActiveDailyQuest, get_expiration_date
from playerdata.models import ActiveWeeklyQuest
from playerdata.models import PlayerQuestDaily
from playerdata.models import PlayerQuestWeekly


def daily_quests_cron():
    # remove top 3 from daily
    print("running daily quest reset cronjob")
    ActiveDailyQuest.objects.filter(id__in=list(ActiveDailyQuest.objects.values_list('pk', flat=True)[:constants.NUM_DAILY_QUESTS])).delete()
    # remove all playerquests that are from there
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
    ActiveWeeklyQuest.objects.filter(id__in=list(ActiveWeeklyQuest.objects.values_list('pk', flat=True)[:constants.NUM_WEEKLY_QUESTS])).delete()
    # remove all playerquests that are from there
    PlayerQuestWeekly.objects.all().delete()

    # pull new ones and make them for every user
    active_quests = ActiveDailyQuest.objects.all()[:constants.NUM_WEEKLY_QUESTS]
    expiry_date = get_expiration_date(7)
    users = User.objects.all()
    bulk_quests = []
    for quest in active_quests:
        for user in users:
            player_quest = PlayerQuestWeekly(base_quest=quest.base_quest, user=user, expiration_date=expiry_date)
            bulk_quests.append(player_quest)

    PlayerQuestWeekly.objects.bulk_create(bulk_quests)
    print("weekly quest cronjob complete!")
