from django.db import models
from django.contrib.auth.models import User

class BaseCharacter(models.Model):
    char_id = models.AutoField(primary_key=True)
    health = models.IntegerField()
    mana = models.IntegerField()
    speed = models.IntegerField()
    attack = models.IntegerField()
    ar = models.IntegerField()
    mr = models.IntegerField()
    attack_range = models.IntegerField()
    rarity = models.IntegerField()
    crit_chance = models.IntegerField()
