from django.db import models
from django.contrib.auth.models import User

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

    def __str__(self):
        return self.name

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
            models.Index(fields=['user',]),
        ]

    def __str__(self):
        return str(self.user) + ": " + str(self.item_type)

class Character(models.Model):
    char_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)
    exp = models.IntegerField()
    prestige = models.IntegerField()
    weapon = models.ForeignKey(Item, null=True, on_delete=models.SET_NULL)
    
    class Meta:
        indexes = [
            models.Index(fields=['user',]),
        ]

    def __str__(self):
        return str(self.user) + ": " + str(self.char_type)

