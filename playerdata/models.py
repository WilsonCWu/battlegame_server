import random
import string
from datetime import datetime, date, time, timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_better_admin_arrayfield.models.fields import ArrayField

from playerdata import constants


class BaseCharacter(models.Model):
    char_type = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)
    health = models.IntegerField()
    mana = models.IntegerField()
    speed = models.IntegerField()
    attack = models.IntegerField()
    ar = models.IntegerField()
    mr = models.IntegerField()
    attack_range = models.IntegerField()
    rarity = models.IntegerField()
    crit_chance = models.IntegerField()
    health_scale = models.IntegerField()
    attack_scale = models.IntegerField()
    ar_scale = models.IntegerField()
    mr_scale = models.IntegerField()

    def __str__(self):
        return self.name


class BaseCharacterUsage(models.Model):
    char_type = models.OneToOneField(BaseCharacter, on_delete=models.CASCADE, primary_key=True)
    num_games = models.IntegerField(default=0)
    num_wins = models.IntegerField(default=0)

    def __str__(self):
        return self.char_type.name


class BaseItem(models.Model):
    item_type = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)
    attack = models.IntegerField()
    penetration = models.IntegerField()
    attack_speed = models.IntegerField()
    rarity = models.IntegerField()
    cost = models.IntegerField()

    def __str__(self):
        return self.name


class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_type = models.ForeignKey(BaseItem, on_delete=models.CASCADE)
    exp = models.IntegerField()
    copies = models.IntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['user', ]),
        ]

    def __str__(self):
        return str(self.user) + ": " + str(self.item_type)


class Character(models.Model):
    char_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)
    level = models.IntegerField(default=1)
    copies = models.IntegerField(default=1)
    prestige = models.IntegerField(default=0)
    weapon = models.ForeignKey(Item, null=True, on_delete=models.SET_NULL)
    total_damage_dealt = models.IntegerField(default=0)
    total_damage_taken = models.IntegerField(default=0)
    total_health_healed = models.IntegerField(default=0)
    num_games = models.IntegerField(default=0)
    num_wins = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user', ]),
        ]

    def __str__(self):
        return str(self.user) + ": " + str(self.char_type)


class Placement(models.Model):
    placement_id = models.AutoField(primary_key=True)
    pos_1 = models.IntegerField(default=-1)
    char_1 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='char_1')
    pos_2 = models.IntegerField(default=-1)
    char_2 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='char_2')
    pos_3 = models.IntegerField(default=-1)
    char_3 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='char_3')
    pos_4 = models.IntegerField(default=-1)
    char_4 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='char_4')
    pos_5 = models.IntegerField(default=-1)
    char_5 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='char_5')

    def __str__(self):
        return str(self.placement_id)
        # return str(self.userinfo.user) + ": " + str(self.placement_id)


class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    char_1 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='tchar_1')
    char_2 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='tchar_2')
    char_3 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='tchar_3')
    char_4 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='tchar_4')
    char_5 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='tchar_5')
    char_6 = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name='tchar_6')

    def __str__(self):
        return str(self.team_id)


class UserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    elo = models.IntegerField(default=0)
    name = models.CharField(max_length=20, default='new player')
    profile_picture = models.IntegerField(default=0)
    default_placement = models.OneToOneField(Placement, null=True, on_delete=models.SET_NULL)
    team = models.OneToOneField(Team, null=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=['elo', ]),
        ]

    def __str__(self):
        return self.name + '(' + str(self.user.id) + ')'


class UserStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    num_games = models.IntegerField(default=0)
    num_wins = models.IntegerField(default=0)
    time_started = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.userinfo.name + '(' + str(self.user.id) + ')'


class Inventory(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    char_limit = models.IntegerField(default=50)
    coins = models.IntegerField(default=0)
    gems = models.IntegerField(default=0)
    hero_exp = models.IntegerField(default=0)

    def __str__(self):
        return self.user.userinfo.name + '(' + str(self.user.id) + ')'


class Chat(models.Model):
    chat_name = models.TextField(default='')

    def __str__(self):
        return self.chat_name + '(' + str(self.id) + ')'


class ChatMessage(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    message = models.TextField()
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    time_send = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['chat', 'time_send']),
        ]

    def __str__(self):
        return str(self.chat_id) + ':' + self.message + '(' + str(self.id) + ')'


class ChatLastReadMessage(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    time_send = models.DateTimeField()

    def __str__(self):
        return str(self.chat_id) + ': user,' + str(self.user) + ' ' + str(self.time_send)


# sorted order. User1<User2
class Friend(models.Model):
    user_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_user_1')
    user_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_user_2')
    chat = models.ForeignKey(Chat, null=True, on_delete=models.SET_NULL, default=None)

    def __str__(self):
        return self.user_1.userinfo.name + ',' + self.user_2.userinfo.name


class FriendRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fr_user')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fr_target')

    def __str__(self):
        return self.user.userinfo.name + ',' + self.target.userinfo.name


class Clan(models.Model):
    name = models.TextField(primary_key=True)
    description = models.TextField(default='A description has not been set.')
    chat = models.ForeignKey(Chat, null=True, on_delete=models.SET_NULL)
    time_started = models.DateTimeField(auto_now_add=True)
    elo = models.IntegerField(default=0)
    profile_picture = models.IntegerField(default=0)
    num_members = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['elo', ]),
        ]


class ClanMember(models.Model):
    userinfo = models.OneToOneField(UserInfo, on_delete=models.CASCADE, primary_key=True)
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, null=True, default=None)
    is_admin = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)


class ClanRequest(models.Model):
    userinfo = models.OneToOneField(UserInfo, on_delete=models.CASCADE)
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)


class DungeonStage(models.Model):
    mob = models.ForeignKey(Placement, on_delete=models.CASCADE)
    exp = models.IntegerField()
    coins = models.IntegerField()
    gems = models.IntegerField()

    def __str__(self):
        return "Stage " + str(self.id)


class DungeonProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    stage_id = models.IntegerField()

    def __str__(self):
        return "user " + str(self.user.id) + ": stage " + str(self.stage_id)


class BaseQuest(models.Model):
    title = models.TextField()
    type = models.IntegerField()
    total = models.IntegerField()
    gems = models.IntegerField(null=True)
    coins = models.IntegerField(null=True)
    item_type = models.ForeignKey(BaseItem, on_delete=models.CASCADE, blank=True, null=True)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "(" + str(self.id) + ") " + self.title


class CumulativeTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    type = models.IntegerField()

    def __str__(self):
        return "user: " + str(self.user.id) + ", type " + str(self.type) + ", progress: " + str(self.progress)


class PlayerQuestCumulative(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.ForeignKey(CumulativeTracker, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    claimed = models.BooleanField(default=False)

    def __str__(self):
        return "user:" + str(self.user_id) + " " + self.base_quest.title


class PlayerQuestDaily(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    claimed = models.BooleanField(default=False)
    expiration_date = models.DateTimeField()

    def __str__(self):
        return "user:" + str(self.user_id) + " " + self.base_quest.title


class PlayerQuestWeekly(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    claimed = models.BooleanField(default=False)
    expiration_date = models.DateTimeField()

    def __str__(self):
        return "user:" + str(self.user_id) + " " + self.base_quest.title


class ActiveCumulativeQuest(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)

    def __str__(self):
        return "(" + str(self.id) + ") " + self.base_quest.title


class ActiveWeeklyQuest(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)

    def __str__(self):
        return "(" + str(self.id) + ") " + self.base_quest.title


class ActiveDailyQuest(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)

    def __str__(self):
        return "(" + str(self.id) + ") " + self.base_quest.title


class BaseCode(models.Model):
    code = models.TextField()
    gems = models.IntegerField(default=0)
    coins = models.IntegerField(default=0)
    items = ArrayField(models.IntegerField(), blank=True, null=True)
    item_amount = ArrayField(models.IntegerField(), blank=True, null=True)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE, blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    num_left = models.IntegerField(default=-1)  # -1 infinite

    def __str__(self):
        return str(self.code)


class ClaimedCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.ForeignKey(BaseCode, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.user) + ": " + str(self.code)


class UserReferral(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    referral_code = models.TextField(unique=True)

    def __str__(self):
        return str(self.user) + ": " + str(self.referral_code)


class ReferralTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    referral = models.ForeignKey(UserReferral, on_delete=models.CASCADE)
    device_id = models.TextField()
    converted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user) + ": " + str(self.referral.referral_code)


class Tournament(models.Model):
    round = models.IntegerField(default=1)
    round_expiration = models.DateTimeField()

    def __str__(self):
        return str(self.id)


class TournamentMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    defence_placement = models.ForeignKey(Placement, on_delete=models.CASCADE)
    num_wins = models.IntegerField(default=0)
    num_losses = models.IntegerField(default=0)
    has_picked = models.BooleanField(default=False)
    rewards_left = models.IntegerField(default=0)
    fights_left = models.IntegerField(default=0)
    is_eliminated = models.BooleanField(default=False)

    def __str__(self):
        return str(self.tournament.id) + ": user(" + str(self.user) + ")"


class TournamentRegistration(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.userinfo.name + '(' + str(self.user.id) + ')'


class TournamentMatch(models.Model):
    attacker = models.ForeignKey(User, on_delete=models.CASCADE)
    defender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opponent')
    tournament_member = models.ForeignKey(TournamentMember, on_delete=models.CASCADE)
    is_win = models.BooleanField(blank=True, null=True)
    has_played = models.BooleanField(default=False)
    round = models.IntegerField()
    # TODO: reference to replay when it's implemented

    def __str__(self):
        return str(self.id) + ": tourney(" + str(self.tournament_member.tournament) +"): attacker(" + str(self.attacker) + ") defender(" + str(self.defender) +")"


class TournamentTeam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    character = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)


class TournamentSelectionCards(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cards = ArrayField(models.IntegerField())


def create_user_referral(user):
    try:
        UserReferral.objects.create(user=user, referral_code=generate_referral_code())
    except IntegrityError:
        create_user_referral(user)


@receiver(post_save, sender=User)
def create_user_info(sender, instance, created, **kwargs):
    if created:
        userinfo = UserInfo.objects.create(user=instance)
        UserStats.objects.create(user=instance)
        Inventory.objects.create(user=instance)
        ClanMember.objects.create(userinfo=userinfo)
        DungeonProgress.objects.create(user=instance, stage_id=1)
        create_user_referral(instance)

        # Add quests
        expiry_date_weekly = get_expiration_date(7)
        expiry_date_daily = get_expiration_date(1)
        create_cumulative_quests(instance)
        create_quests_by_class(instance, ActiveWeeklyQuest.objects.all()[:constants.NUM_WEEKLY_QUESTS], PlayerQuestWeekly, expiry_date_weekly)
        create_quests_by_class(instance, ActiveDailyQuest.objects.all()[:constants.NUM_DAILY_QUESTS], PlayerQuestDaily, expiry_date_daily)


def create_cumulative_quests(user):
    cumulative_quests = []
    active_quests = ActiveCumulativeQuest.objects.all()
    for quest in active_quests:
        if quest.base_quest.type is constants.REACH_DUNGEON_LEVEL:
            progress_tracker, _ = CumulativeTracker.objects.get_or_create(user=user, type=quest.base_quest.type, progress=1)
        else:
            progress_tracker, _ = CumulativeTracker.objects.get_or_create(user=user, type=quest.base_quest.type)
        player_quest = PlayerQuestCumulative(base_quest=quest.base_quest, user=user, progress=progress_tracker)
        cumulative_quests.append(player_quest)
    PlayerQuestCumulative.objects.bulk_create(cumulative_quests)


def create_quests_by_class(user, active_quests, quest_class, expiry_date):
    bulk_quests = []
    for quest in active_quests:
        player_quest = quest_class(base_quest=quest.base_quest, user=user, expiration_date=expiry_date)
        bulk_quests.append(player_quest)
    quest_class.objects.bulk_create(bulk_quests)


# Gets the next expiration date which is just midnight no time zone
def get_expiration_date(interval):
    if interval is 1:
        delta = 1
    else:
        delta = (7 - datetime.today().weekday()) % 7
        if delta is 0:
            delta = 7

    return datetime.combine(date.today(), time()) + timedelta(days=delta)


# Generates a random 12 letter uppercase string
# https://stackoverflow.com/questions/2511222/efficiently-generate-a-16-character-alphanumeric-string
def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase, k=12))


@receiver(post_save, sender=User)
def save_user_info(sender, instance, **kwargs):
    instance.userinfo.save()
    instance.userstats.save()
    instance.inventory.save()
    instance.userinfo.clanmember.save()
