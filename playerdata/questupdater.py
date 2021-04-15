import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic

from playerdata import constants, server
from playerdata.models import PlayerQuestCumulative, PlayerQuestCumulative2, BaseQuest
from playerdata.models import PlayerQuestWeekly
from playerdata.models import PlayerQuestDaily
from playerdata.models import CumulativeTracker


def add_progress_to_quest_list(progress, quests):
    try:
        for quest in quests:
            if progress + quest.progress >= quest.base_quest.total:
                quest.progress = quest.base_quest.total
                quest.completed = True
            else:
                quest.progress += progress
            quest.save()
    except OverflowError:
        logging.error("stats overflow error")


def set_progress_to_quest_list(progress, quests):
    try:
        for quest in quests:
            if progress >= quest.base_quest.total:
                quest.completed = True

            quest.progress = progress
            quest.save()
    except OverflowError:
        logging.error("stats overflow error")


def update_cumulative_progress(quests, tracker):
    for quest in quests:
        if tracker.progress >= quest.base_quest.total:
            quest.completed = True

    PlayerQuestCumulative.objects.bulk_update(quests, ['completed'])


# quests is a list of BaseQuests
def update_cumulative_progress2(quests, tracker, player_cumulative):
    for quest in quests:
        if tracker.progress >= quest.total:
            player_cumulative.completed_quests.append(quest.id)

    player_cumulative.save()


class QuestUpdater:

    @staticmethod
    @atomic
    def add_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            logging.error("negative progress on quest type: " + UPDATE_TYPE)
            return

        cumulative_quests = PlayerQuestCumulative.objects.select_related('base_quest').filter(user=user,
                                                                                              base_quest__type=UPDATE_TYPE,
                                                                                              completed=False,
                                                                                              claimed=False)
        if server.is_server_version_higher("0.2.2"):
            player_cumulative = PlayerQuestCumulative2.objects.filter(user=user).first()
            cumulative_basequests = BaseQuest.objects.filter(type=UPDATE_TYPE).exclude(
                id__in=(player_cumulative.completed_quests + player_cumulative.claimed_quests))


        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user,
                                                                                      base_quest__type=UPDATE_TYPE,
                                                                                      completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user,
                                                                                    base_quest__type=UPDATE_TYPE,
                                                                                    completed=False, claimed=False)

        try:
            tracker = CumulativeTracker.objects.get(user=user, type=UPDATE_TYPE)
            tracker.progress += amount
            tracker.save()
            if server.is_server_version_higher("0.2.2"):
                update_cumulative_progress2(cumulative_basequests, tracker, player_cumulative)
            else:
                update_cumulative_progress(cumulative_quests, tracker)
        except ObjectDoesNotExist:
            pass
        except OverflowError:
            logging.error("stats overflow error")

        add_progress_to_quest_list(amount, weekly_quests)
        add_progress_to_quest_list(amount, daily_quests)

    @staticmethod
    @atomic
    def set_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            logging.error("negative progress on quest type: " + UPDATE_TYPE)
            return

        cumulative_quests = PlayerQuestCumulative.objects.select_related('base_quest').filter(user=user,
                                                                                              base_quest__type=UPDATE_TYPE,
                                                                                              completed=False,
                                                                                              claimed=False)

        if server.is_server_version_higher("0.2.2"):
            player_cumulative = PlayerQuestCumulative2.objects.filter(user=user).first()
            cumulative_basequests = BaseQuest.objects.filter(type=UPDATE_TYPE).exclude(id__in=(player_cumulative.completed_quests + player_cumulative.claimed_quests))

        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user,
                                                                                      base_quest__type=UPDATE_TYPE,
                                                                                      completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user,
                                                                                    base_quest__type=UPDATE_TYPE,
                                                                                    completed=False, claimed=False)

        try:
            tracker = CumulativeTracker.objects.get(user=user, type=UPDATE_TYPE)
            tracker.progress = amount
            tracker.save()
            if server.is_server_version_higher("0.2.2"):
                update_cumulative_progress2(cumulative_basequests, tracker, player_cumulative)
            else:
                update_cumulative_progress(cumulative_quests, tracker)
        except ObjectDoesNotExist:
            pass

        set_progress_to_quest_list(amount, weekly_quests)
        set_progress_to_quest_list(amount, daily_quests)

    @staticmethod
    def game_won_by_char_id(user, char_id):
        quest_type = constants.WIN_X_GAMES_WITH_CHAR_NAMESPACE + char_id
        QuestUpdater.add_progress_by_type(user, quest_type, 1)
