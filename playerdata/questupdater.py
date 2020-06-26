from playerdata.models import PlayerQuestCumulative
from playerdata.models import PlayerQuestWeekly
from playerdata.models import PlayerQuestDaily
from playerdata.models import CumulativeTracker


def add_progress_to_quest_list(progress, quests):
    for quest in quests:
        if progress + quest.progress >= quest.base_quest.total:
            quest.progress = quest.base_quest.total
            quest.completed = True
        else:
            quest.progress += progress
        quest.save()


def set_progress_to_quest_list(progress, quests):
    for quest in quests:
        if progress + quest.progress >= quest.base_quest.total:
            quest.progress = quest.base_quest.total
            quest.completed = True
        else:
            quest.progress = progress
        quest.save()


def update_cumulative_progress(progress, quests, tracker):
    tracker.progress += progress
    tracker.save()
    for quest in quests:
        if tracker.progress >= quest.base_quest.total:
            quest.completed = True
            quest.save()


class QuestUpdater:

    @staticmethod
    def add_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            # Error log negative progress
            return

        cumulative_quests = PlayerQuestCumulative.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)
        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)

        tracker = CumulativeTracker.objects.get(user=user, type=UPDATE_TYPE)
        update_cumulative_progress(amount, cumulative_quests, tracker)

        add_progress_to_quest_list(amount, weekly_quests)
        add_progress_to_quest_list(amount, daily_quests)
