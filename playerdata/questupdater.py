import logging
from collections import defaultdict

from django.db.transaction import atomic

from mainsocket import notifications
from playerdata import constants
from playerdata.models import PlayerQuestCumulative2, BaseQuest
from playerdata.models import PlayerQuestDaily
from playerdata.models import PlayerQuestWeekly


def add_progress_to_quest_list(progress, quests):
    completed_count = 0
    try:
        for quest in quests:
            if progress + quest.progress >= quest.base_quest.total:
                quest.progress = quest.base_quest.total
                quest.completed = True
                completed_count += 1
            else:
                quest.progress += progress
            quest.save()
    except OverflowError:
        logging.error("stats overflow error")
    return completed_count


def set_progress_to_quest_list(progress, quests):
    completed_count = 0
    try:
        for quest in quests:
            if progress >= quest.base_quest.total:
                quest.completed = True
                completed_count += 1

            quest.progress = progress
            quest.save()
    except OverflowError:
        logging.error("stats overflow error")
    return completed_count


# quests is a list of BaseQuests
def update_cumulative_progress2(quests, progress, player_cumulative):
    completed_count = 0
    for quest in quests:
        if progress >= quest.total:
            player_cumulative.completed_quests.append(quest.id)
            completed_count += 1

    player_cumulative.save()
    return completed_count


class CumulativeBadgeNotifCount(notifications.BadgeNotifCount):
    def get_badge_notif(self, user):
        player_cumulative = PlayerQuestCumulative2.objects.filter(user=user).first()
        completed_set = set(player_cumulative.completed_quests)
        count = len(completed_set.difference(player_cumulative.claimed_quests))
        return notifications.BadgeNotif(constants.NotificationType.CUMULATIVE_QUEST.value, count)


class DailyBadgeNotifCount(notifications.BadgeNotifCount):
    def get_badge_notif(self, user):
        count = PlayerQuestDaily.objects.filter(user=user, completed=True, claimed=False).count()
        return notifications.BadgeNotif(constants.NotificationType.DAILY_QUEST.value, count)


class WeeklyBadgeNotifCount(notifications.BadgeNotifCount):
    def get_badge_notif(self, user):
        count = PlayerQuestWeekly.objects.filter(user=user, completed=True, claimed=False).count()
        return notifications.BadgeNotif(constants.NotificationType.WEEKLY_QUEST.value, count)


class QuestUpdater:

    @staticmethod
    @atomic
    def add_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            logging.error("negative progress on quest type: " + UPDATE_TYPE)
            return

        player_cumulative = PlayerQuestCumulative2.objects.filter(user=user).first()
        cumulative_basequests = BaseQuest.objects.filter(type=UPDATE_TYPE).exclude(
            id__in=(player_cumulative.completed_quests + player_cumulative.claimed_quests))


        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user,
                                                                                      base_quest__type=UPDATE_TYPE,
                                                                                      completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user,
                                                                                    base_quest__type=UPDATE_TYPE,
                                                                                    completed=False, claimed=False)
        cumulative_count = 0
        try:
            user.userstats.cumulative_stats = defaultdict(int, user.userstats.cumulative_stats)
            user.userstats.cumulative_stats[str(UPDATE_TYPE)] += amount
            user.userstats.save()

            cumulative_count = update_cumulative_progress2(cumulative_basequests, user.userstats.cumulative_stats[str(UPDATE_TYPE)], player_cumulative)
        except OverflowError:
            logging.error("stats overflow error")

        daily_count = add_progress_to_quest_list(amount, daily_quests)
        weekly_count = add_progress_to_quest_list(amount, weekly_quests)

        # TODO: These updates are newly completed counts, send using incremental instead of replace
        notifications.send_badge_notifs(user.id,
                                        notifications.BadgeNotif(constants.NotificationType.DAILY_QUEST.value, daily_count),
                                        notifications.BadgeNotif(constants.NotificationType.WEEKLY_QUEST.value, weekly_count),
                                        notifications.BadgeNotif(constants.NotificationType.CUMULATIVE_QUEST.value, cumulative_count)
                                        )


    @staticmethod
    @atomic
    def set_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            logging.error("negative progress on quest type: " + UPDATE_TYPE)
            return

        player_cumulative = PlayerQuestCumulative2.objects.filter(user=user).first()
        cumulative_basequests = BaseQuest.objects.filter(type=UPDATE_TYPE).exclude(id__in=(player_cumulative.completed_quests + player_cumulative.claimed_quests))

        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user,
                                                                                      base_quest__type=UPDATE_TYPE,
                                                                                      completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user,
                                                                                    base_quest__type=UPDATE_TYPE,
                                                                                    completed=False, claimed=False)

        user.userstats.cumulative_stats[str(UPDATE_TYPE)] = amount
        user.userstats.save()

        cumulative_count = update_cumulative_progress2(cumulative_basequests, user.userstats.cumulative_stats[str(UPDATE_TYPE)], player_cumulative)

        daily_count = set_progress_to_quest_list(amount, daily_quests)
        weekly_count = set_progress_to_quest_list(amount, weekly_quests)

        # TODO: These updates are newly completed counts, send using incremental instead of replace
        notifications.send_badge_notifs(user.id,
                                        notifications.BadgeNotif(constants.NotificationType.DAILY_QUEST.value, daily_count),
                                        notifications.BadgeNotif(constants.NotificationType.WEEKLY_QUEST.value, weekly_count),
                                        notifications.BadgeNotif(constants.NotificationType.CUMULATIVE_QUEST.value, cumulative_count)
                                        )

    @staticmethod
    def game_won_by_char_id(user, char_id):
        quest_type = constants.WIN_X_GAMES_WITH_CHAR_NAMESPACE + char_id
        QuestUpdater.add_progress_by_type(user, quest_type, 1)
