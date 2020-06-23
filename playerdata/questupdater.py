from playerdata.models import PlayerQuestCumulative
from playerdata.models import PlayerQuestWeekly
from playerdata.models import PlayerQuestDaily


def add_progress_to_quest_list(progress, quests):
    for quest in quests:
        if progress + quest.progress >= quest.base_quest.total:
            quest.progress = quest.base_quest.total
            quest.completed = True
        else:
            quest.progress += progress
        quest.save()


class QuestUpdater:

    # Time based
    DAMAGE_DEALT = 0
    COINS_EARNED = 1
    ULTS_USED = 2
    COMPLETE_A_LEVEL_DUNGEON = 3
    LEVEL_UP_HERO = 4
    PURCHASE_ITEM = 5

    # Cumulative
    DISCORD = 6
    TWITTER = 7

    ACCOUNT_LINK = 8
    JOIN_GUILD = 9
    GUILD_WAR = 10
    MAKE_FRIENDS = 11

    WIN_GAMES = 12
    OWN_HEROES = 13
    REACH_LEVEL_DUNGEON = 14
    REACH_LEVEL_HERO = 15
    REACH_LEVEL_PLAYER = 16

    @staticmethod
    def add_update_type(user, UPDATE_TYPE, amount):
        # check instances of quests that are related to damage
        if amount < 0:
            # Error log negative progress
            return

        cumulative_quests = PlayerQuestCumulative.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)
        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)

        add_progress_to_quest_list(amount, cumulative_quests)
        add_progress_to_quest_list(amount, weekly_quests)
        add_progress_to_quest_list(amount, daily_quests)

