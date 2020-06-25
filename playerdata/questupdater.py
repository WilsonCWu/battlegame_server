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


def set_progress_to_quest_list(progress, quests):
    for quest in quests:
        if progress + quest.progress >= quest.base_quest.total:
            quest.progress = quest.base_quest.total
            quest.completed = True
        else:
            quest.progress = progress
        quest.save()


class QuestUpdater:

    # Generic
    DAMAGE_DEALT = 0  # Tracked / total damage
    COINS_EARNED = 1  # / total coins
    ULTS_USED = 2
    LEVEL_UP_A_HERO = 3
    PURCHASE_ITEM = 4
    DISCORD = 5
    TWITTER = 6
    ACCOUNT_LINK = 7
    JOIN_GUILD = 8  # Tracked / 1
    FIGHT_GUILD_WAR = 9
    MAKE_A_FRIEND = 10  # Tracked / 1
    WIN_QUICKPLAY_GAMES = 11  # Tracked / total games
    WIN_DUNGEON_GAMES = 12  # Tracked / total games
    OWN_HEROES = 13
    REACH_PLAYER_LEVEL = 14
    REACH_DUNGEON_LEVEL = 15  # Tracked / total dungeon level


    @staticmethod
    def add_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            # Error log negative progress
            return

        cumulative_quests = PlayerQuestCumulative.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)
        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user, base_quest__type=UPDATE_TYPE, completed=False, claimed=False)

        add_progress_to_quest_list(amount, cumulative_quests)
        add_progress_to_quest_list(amount, weekly_quests)
        add_progress_to_quest_list(amount, daily_quests)

    @staticmethod
    def set_progress_by_type(user, UPDATE_TYPE, amount):
        if amount < 0:
            # Error log negative progress
            return

        cumulative_quests = PlayerQuestCumulative.objects.select_related('base_quest').filter(user=user,
                                                                                              base_quest__type=UPDATE_TYPE,
                                                                                              completed=False,
                                                                                              claimed=False)
        weekly_quests = PlayerQuestWeekly.objects.select_related('base_quest').filter(user=user,
                                                                                      base_quest__type=UPDATE_TYPE,
                                                                                      completed=False, claimed=False)
        daily_quests = PlayerQuestDaily.objects.select_related('base_quest').filter(user=user,
                                                                                    base_quest__type=UPDATE_TYPE,
                                                                                    completed=False, claimed=False)

        set_progress_to_quest_list(amount, cumulative_quests)
        set_progress_to_quest_list(amount, weekly_quests)
        set_progress_to_quest_list(amount, daily_quests)
