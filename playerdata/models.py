from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


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


@receiver(post_save, sender=User)
def create_user_info(sender, instance, created, **kwargs):
    if created:
        userinfo = UserInfo.objects.create(user=instance)
        UserStats.objects.create(user=instance)
        Inventory.objects.create(user=instance)
        ClanMember.objects.create(userinfo=userinfo)


@receiver(post_save, sender=User)
def save_user_info(sender, instance, **kwargs):
    instance.userinfo.save()
    instance.userstats.save()
    instance.inventory.save()
    instance.userinfo.clanmember.save()
