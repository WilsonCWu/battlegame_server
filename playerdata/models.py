import json
import random
import string
from datetime import datetime, date, time, timedelta
from packaging import version
import time as ptime
import functools

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import IntegrityError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django_better_admin_arrayfield.models.fields import ArrayField
from decouple import config

from bulk_update_or_create import BulkUpdateOrCreateQuerySet
from playerdata import constants

# Developer account IDs for in-game accounts
from playerdata.constants import DealType, DungeonType

DEV_ACCOUNT_IDS = json.loads(config("DEV_ACCOUNT_IDS",  default='{"data": []}'))["data"]


class ServerStatus(models.Model):
    id = models.AutoField(primary_key=True)
    creation_time = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=1, choices=(
        ('V', 'Version'),
        ('M', 'Maintenance'),
    ))
    # Fields for Version events.
    version_number = models.CharField(max_length=15, blank=True, null=True)
    require_update = models.BooleanField(default=True)

    # Fields for Maintenance events.
    maintenance_start = models.DateTimeField(blank=True, null=True)
    expected_end = models.DateTimeField(blank=True, null=True)
    patch_notes = models.TextField(default="", blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['creation_time', 'event_type']),
        ]

    @functools.lru_cache(maxsize=1)
    def latest_version(ttl=int(ptime.time()//60)):
        """Return the latest server version, cached with TTL of 60 seconds."""
        status = ServerStatus.objects.filter(event_type='V').latest('creation_time')
        return status.version_number

    def clean(self):
        if self.event_type == 'V':
            if not self.version_number:
                raise ValidationError("version number is none")
        elif self.event_type == 'M':
            if not self.maintenance_start:
                raise ValidationError("maintenance_start is none")
            if self.expected_end and self.expected_end < self.maintenance_start:
                raise ValidationError("expected_end before maintenance_start")

    def __str__(self):
        if self.event_type == 'V':
            return "Version: %s (%s)" % (self.version_number, self.creation_time)
        elif self.maintenance_start <= timezone.now():
            return "Past maintenance: %s" % (self.maintenance_start)
        else:
            return "Upcoming maintenance: %s" % (self.maintenance_start)


class Flag(models.Model):
    name = models.CharField(max_length=30, primary_key=True)
    value = models.BooleanField(default=False)

    def __str__(self):
        return '%s: %s' % (self.name, str(self.value))


class UserFlag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flag = models.ForeignKey(Flag, on_delete=models.CASCADE)
    value = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'flag')

    def __str__(self):
        return '%s (%s): %s' % (str(self.flag), str(self.user), str(self.value))
        

class BaseCharacter(models.Model):
    char_type = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)
    rarity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    rollable = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['rarity', 'rollable']),
        ]


    def __str__(self):
        return str(self.char_type) + ': ' + self.name


class BaseCharacterStats(models.Model):
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)
    version = models.CharField(max_length=30, default='0.0.0')

    health = models.IntegerField()
    starting_mana = models.IntegerField()
    mana = models.IntegerField()
    speed = models.IntegerField()
    attack_damage = models.IntegerField()
    ability_damage = models.IntegerField()
    attack_speed = models.FloatField()
    ar = models.IntegerField()
    mr = models.IntegerField()
    attack_range = models.IntegerField()
    crit_chance = models.IntegerField()
    health_scale = models.IntegerField()
    attack_scale = models.IntegerField()
    ability_scale = models.IntegerField()
    ar_scale = models.IntegerField()
    mr_scale = models.IntegerField()

    class Meta:
        unique_together = ('char_type', 'version')

    def __str__(self):
        return self.char_type.name + ': ' + self.version

    # TODO: remove after deprecation from base.
    def clone_from_base(base_char, version):
        return BaseCharacterStats.objects.create(
            char_type = base_char,
            version = version,
            health = base_char.health,
            starting_mana = base_char.starting_mana,
            mana = base_char.mana,
            speed = base_char.speed,
            attack_damage = base_char.attack_damage,
            ability_damage = base_char.ability_damage,
            attack_speed = base_char.attack_speed,
            ar = base_char.ar,
            mr = base_char.mr,
            attack_range = base_char.attack_range,
            crit_chance = base_char.crit_chance,
            health_scale = base_char.health_scale,
            attack_scale = base_char.attack_scale,
            ability_scale = base_char.ability_scale,
            ar_scale = base_char.ar_scale,
            mr_scale = base_char.mr_scale,
        )

    def get_active():
        stats = {}
        for s in BaseCharacterStats.objects.all():
            # We expect server versions to be triplets.
            if s.char_type not in stats or version.parse(s.version) > version.parse(stats[s.char_type].version):
                stats[s.char_type] = s
        return stats.values()

    def get_active_under_version(v):
        stats = {}
        for s in BaseCharacterStats.objects.all():
            if version.parse(s.version) > version.parse(v):
                continue
            
            # We expect server versions to be triplets.
            if s.char_type not in stats or version.parse(s.version) > version.parse(stats[s.char_type].version):
                stats[s.char_type] = s
        return stats.values()


class BaseCharacterAbility2(models.Model):
    """Model holding character ability specs which are progressively unlocked.

    Unlocking occurs at lvl % 20 == 1 (until there is no more abilities to be
    unlocked). Each character has a max of four abilities. The ability specs
    are encoded in JSON for flexibility.

    In addition to unlocking levels, they can be unlocked with prestiges. The
    prestige specs must be bonuses of specs unlocked by character levels.

    Within each ability spec, we expect JSON in the following format: {
        <unlock_level>: {
            "damage": 1,
            ...
        },
        ...
    }.
    """
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)
    version = models.CharField(max_length=30, default='0.0.0')

    def is_num_key(v):
        try:
            _ = float(v)
            return True
        except:
            return False

    def is_prestige_key(v):
        return v.startswith("prestige-") and BaseCharacterAbility2.is_num_key(v.lstrip("prestige-"))

    def validate_ability_specs(specs):
        seen_levels = set()
        seen_ability_level_keys, seen_prestige_level_keys = set(), set()
        for unlock_level in specs:
            # We only expect keys to be unlock_levels.
            if not BaseCharacterAbility2.is_num_key(unlock_level) and not BaseCharacterAbility2.is_prestige_key(unlock_level):
                raise ValidationError('unlock level %s should be a number or a prestige.'
                                      % unlock_level)

            # Abilities should only be unlocked in increments of 20.
            if BaseCharacterAbility2.is_num_key(unlock_level) and int(unlock_level) % 20 != 1:
                raise ValidationError('unlock levels should be in increments '
                                      'of 20.')

            # No duplicates can exist in a level itself.
            if unlock_level in seen_levels:
                raise ValidationError('spec cannot have duplicate unlock '
                                      'levels.')
            seen_levels.add(unlock_level)

            # All specs themselves must be a one layer flat list of strings
            # to numbers.
            for v in specs[unlock_level].values():
                if not BaseCharacterAbility2.is_num_key(v):
                    raise ValidationError('inner specs can only have numeric '
                                          'values.')

            # Validate that ability leveling and prestige leveling have the
            # same keys, but they don't overlap.
            if BaseCharacterAbility2.is_num_key(unlock_level):
                if not seen_ability_level_keys:
                    seen_ability_level_keys = set(specs[unlock_level])
                elif seen_ability_level_keys != set(specs[unlock_level]):
                    raise ValidationError('ability levels must have identical keys!')
            else:
                if not seen_prestige_level_keys:
                    seen_prestige_level_keys = set(specs[unlock_level])
                elif seen_prestige_level_keys != set(specs[unlock_level]):
                    raise ValidationError('prestige levels must have identical keys!')

        if seen_ability_level_keys and seen_prestige_level_keys:
            if seen_ability_level_keys.intersection(seen_prestige_level_keys):
                raise ValidationError('ability level keys and prestige keys ',
                                      'should not intersect.')
            for prestige_key in seen_prestige_level_keys:
                if not prestige_key.endswith('_bonus'):
                    raise ValidationError('prestige key must end with _bonus.')
                if not prestige_key[:-len('_bonus')] in seen_ability_level_keys:
                    raise ValidationError('prestige key must be bonuses of ',
                                          'level keys.')


    ability1_specs = JSONField(blank=True, null=True,
                               validators=[validate_ability_specs])
    ability1_desc = models.CharField(max_length=250, blank=True, null=True)

    ability2_specs = JSONField(blank=True, null=True,
                               validators=[validate_ability_specs])
    ability2_desc = models.CharField(max_length=250, blank=True, null=True)

    ability3_specs = JSONField(blank=True, null=True,
                               validators=[validate_ability_specs])
    ability3_desc = models.CharField(max_length=250, blank=True, null=True)

    ultimate_specs = JSONField(blank=True, null=True,
                               validators=[validate_ability_specs])
    ultimate_desc = models.CharField(max_length=250, blank=True, null=True)

    def clean(self):
        # Ensure that our levels increase by increments of 20 overall.
        seen_levels = set()
        for specs in (self.ability1_specs, self.ability2_specs,
                      self.ability3_specs, self.ultimate_specs):
            if specs is None:
                continue

            try:
                levels_in_spec = {int(lvl) for lvl in specs
                                  if not BaseCharacterAbility2.is_prestige_key(lvl)}
            except:
                raise ValidationError('ability levels must be integers')

            # There should be no duplicate levels, unless it is for prestige.
            if seen_levels.intersection(levels_in_spec):
                raise ValidationError('two ability specs have the same '
                                      'unlock level.')
            seen_levels.update(levels_in_spec)

            # Prestiges can only grant ability buffs from starlevel 5-10.
            prestige_levels_in_spec = {lvl for lvl in specs
                                       if BaseCharacterAbility2.is_prestige_key(lvl)}
            for prestige_level in prestige_levels_in_spec:
                int_level = int(prestige_level.lstrip("prestige-"))
                prestige_cap = constants.PRESTIGE_CAP_BY_RARITY[self.char_type.rarity]
                if int_level > prestige_cap:
                    raise ValidationError('prestige level %d exceeds cap.' % int_level)
                if int_level <= prestige_cap - 5:
                    raise ValidationError('prestige level %d should not have ability bonuses.' % int_level)

        for i in range(len(seen_levels)):
            expected_level = i * 20 + 1
            if expected_level not in seen_levels:
                raise ValidationError('specs expected to have level %d.'
                                      % expected_level)

    def get_active():
        specs = {}
        for a in BaseCharacterAbility2.objects.all():
            # We expect server versions to be triplets.
            if a.char_type not in specs or version.parse(a.version) > version.parse(specs[a.char_type].version):
                specs[a.char_type] = a
        return specs.values() 

    def get_active_under_version(v):
        specs = {}
        for a in BaseCharacterAbility2.objects.all():
            if version.parse(a.version) > version.parse(v):
                continue
            
            # We expect server versions to be triplets.
            if a.char_type not in specs or version.parse(a.version) > version.parse(specs[a.char_type].version):
                specs[a.char_type] = a
        return specs.values() 
 
    class Meta:
        unique_together = ('char_type', 'version')
 
    def __str__(self):
        return self.char_type.name + ': ' + self.version

    
class BaseCharacterAbility:
    def validate_ability_specs():
        # NOTE: we should not put validators inside of model classes, because
        # now past migrations will refer to them.
        pass


class BaseCharacterUsage(models.Model):
    char_type = models.OneToOneField(BaseCharacter, on_delete=models.CASCADE, primary_key=True)
    num_games = models.IntegerField(default=0)
    num_wins = models.IntegerField(default=0)

    def __str__(self):
        return self.char_type.name


class StatModifiers(models.Model):
    # Basic stat changes.
    attack_flat = models.IntegerField(blank=True, null=True)
    attack_mult = models.FloatField(blank=True, null=True)
    ability_flat = models.IntegerField(blank=True, null=True)
    ability_mult = models.FloatField(blank=True, null=True)
    attack_speed_flat = models.FloatField(blank=True, null=True)
    # TODO: deprecated.
    attack_speed_mult = models.FloatField(blank=True, null=True)
    ar_flat = models.IntegerField(blank=True, null=True)
    ar_mult = models.FloatField(blank=True, null=True)
    mr_flat = models.IntegerField(blank=True, null=True)
    mr_mult = models.FloatField(blank=True, null=True)
    speed_flat = models.IntegerField(blank=True, null=True)
    speed_mult = models.FloatField(blank=True, null=True)
    crit_flat = models.IntegerField(blank=True, null=True)
    # TODO: deprecated.
    crit_mult = models.FloatField(blank=True, null=True)
    mana_tick_flat = models.IntegerField(blank=True, null=True)
    mana_tick_mult = models.FloatField(blank=True, null=True)
    range_flat = models.IntegerField(blank=True, null=True)
    max_health_flat = models.IntegerField(blank=True, null=True)
    max_health_mult = models.FloatField(blank=True, null=True)

    # These are recognized by the client and its effects are encoded there.
    effect_ids = ArrayField(models.IntegerField(), blank=True, null=True)

    class Meta:
        abstract = True


class BaseItem(StatModifiers):
    GEAR_SLOT_CHOICES = (
        ('H', 'Hat'),
        ('A', 'Armor'),
        ('B', 'Boots'),
        ('W', 'Weapon'),
        ('T', 'Tricket'),
        # Items that are not to be equipped, but consumed (e.g. tickets needed
        # for an event).
        ('C', 'Consumables'),
    )

    item_type = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=250, default='')
    gear_slot = models.CharField(max_length=1, choices=GEAR_SLOT_CHOICES)

    rarity = models.IntegerField()
    cost = models.IntegerField()
    is_unique = models.BooleanField(default=False)

    rollable = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class BasePrestige(StatModifiers):
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)
    level = models.IntegerField()

    class Meta:
        unique_together = (("char_type", "level"),)

    def clean(self):
        # Clean will ensure that all prestige levels are within bounds.
        rarity = self.char_type.rarity

        # For common characters, they start off with 0 star level, which means
        # that they won't need prestige-0, which is used for padding star
        # levels given by base rarity.
        bounds = (1 if rarity == 1 else 0, constants.PRESTIGE_CAP_BY_RARITY[rarity])
        if self.level < bounds[0] or self.level > bounds[1]:
            raise ValidationError("Expected prestige for char rarity %d to be between %s" % (rarity, bounds))

    def __str__(self):
        return self.char_type.name + ": " + str(self.level)


class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_type = models.ForeignKey(BaseItem, on_delete=models.CASCADE)
    exp = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user', ]),
        ]

    def __str__(self):
        return str(self.user) + ": " + str(self.item_type) + " " + str(self.item_id)


@deconstructible
class SlotValidator():
    """Validates that the item is placed in the appropriate slot."""
    def __init__(self, slot_type):
        self.slot_type = slot_type
    def __eq__(self, other):
        return self.slot_type == other.slot_type
    def __call__(self, item):
        # These validators are only triggered for form objects, e.g. the admin
        # interface -- hence it's okay for it to not be perfectly performant.
        if Item.objects.select_related('item_type').get(item_id=item).item_type.gear_slot != self.slot_type:
            raise ValidationError('item must be of type ' + self.slot_type)


class Character(models.Model):
    char_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE)
    level = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_CHARACTER_LEVEL)])
    copies = models.IntegerField(default=0)
    prestige = models.IntegerField(default=0)
    total_damage_dealt = models.BigIntegerField(default=0)
    total_damage_taken = models.BigIntegerField(default=0)
    total_health_healed = models.BigIntegerField(default=0)
    num_games = models.IntegerField(default=0)
    num_wins = models.IntegerField(default=0)
    is_tourney = models.BooleanField(default=False)
    is_boosted = models.BooleanField(default=False)

    # Character equipments (hat, armor, weapon, boots, tricket 1/2).
    hat = models.OneToOneField(Item, blank=True, null=True, on_delete=models.SET_NULL, related_name='hat', validators=[SlotValidator('H')])
    armor = models.OneToOneField(Item, blank=True, null=True, on_delete=models.SET_NULL, related_name='armor', validators=[SlotValidator('A')])
    weapon = models.OneToOneField(Item, blank=True, null=True, on_delete=models.SET_NULL, related_name='weapon', validators=[SlotValidator('W')])
    boots = models.OneToOneField(Item, blank=True, null=True, on_delete=models.SET_NULL, related_name='boots', validators=[SlotValidator('B')])
    trinket_1 = models.OneToOneField(Item, blank=True, null=True, on_delete=models.SET_NULL, related_name='trinket_1', validators=[SlotValidator('T')])
    trinket_2 = models.OneToOneField(Item, blank=True, null=True, on_delete=models.SET_NULL, related_name='trinket_2', validators=[SlotValidator('T')])

    class Meta:
        indexes = [
            models.Index(fields=['user', ]),
        ]

    def clean(self):
        # Raise if our trinket is equipped by someone else's but on a different
        # slot.
        if self.trinket_1 and hasattr(self.trinket_1, 'trinket_2'):
            raise ValidationError({'trinket_1': 'Trinket is already in use by another character.'})
        if self.trinket_2 and hasattr(self.trinket_2, 'trinket_1'):
            raise ValidationError({'trinket_2': 'Trinket is already in use by another character.'})

    def __str__(self):
        return str(self.user) + ": " + str(self.char_type) + " " + str(self.char_id)


class Placement(models.Model):
    placement_id = models.AutoField(primary_key=True)
    # TODO(yanke): delete null on user.
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    pos_1 = models.IntegerField(default=-1)
    char_1 = models.ForeignKey(Character, blank=True, null=True, on_delete=models.SET_NULL, related_name='char_1')
    pos_2 = models.IntegerField(default=-1)
    char_2 = models.ForeignKey(Character, blank=True, null=True, on_delete=models.SET_NULL, related_name='char_2')
    pos_3 = models.IntegerField(default=-1)
    char_3 = models.ForeignKey(Character, blank=True, null=True, on_delete=models.SET_NULL, related_name='char_3')
    pos_4 = models.IntegerField(default=-1)
    char_4 = models.ForeignKey(Character, blank=True, null=True, on_delete=models.SET_NULL, related_name='char_4')
    pos_5 = models.IntegerField(default=-1)
    char_5 = models.ForeignKey(Character, blank=True, null=True, on_delete=models.SET_NULL, related_name='char_5')

    is_tourney = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_tourney']),
        ]

    def __str__(self):
        return str(self.user) + ": " + str(self.placement_id)


class UserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField(max_length=20, default='new player')
    description = models.TextField(default='A description has not been set.')
    profile_picture = models.IntegerField(default=0)
    default_placement = models.ForeignKey(Placement, null=True, on_delete=models.SET_NULL)
    player_exp = models.IntegerField(default=0)
    is_bot = models.BooleanField(default=False)

    # Player skills ranking.
    elo = models.IntegerField(default=0)
    highest_elo = models.IntegerField(default=0)  # we'll want to have this when showing the elo rewards panel
    tier_rank = models.IntegerField(choices=[(tier.value, tier.name) for tier in constants.Tiers],
                                       default=constants.Tiers.BRONZE_FIVE.value)
    tourney_elo = models.IntegerField(default=0)
    prev_tourney_elo = models.IntegerField(default=0)
    best_daily_dungeon_stage = models.IntegerField(default=0)
    best_moevasion_stage = models.BigIntegerField(default=0)
    highest_moevasion_reward_collected = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['elo', ]),
            models.Index(fields=['best_moevasion_stage', ]),
        ]

    def __str__(self):
        return self.name + '(' + str(self.user.id) + ')'


class UserStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    num_games = models.IntegerField(default=0)
    num_wins = models.IntegerField(default=0)
    time_started = models.DateTimeField(auto_now_add=True)
    win_streak = models.IntegerField(default=0)
    longest_win_streak = models.IntegerField(default=0)
    daily_wins = models.IntegerField(default=0)
    mythic_pity_counter = models.IntegerField(default=0)
    silver_pity_counter = models.IntegerField(default=0)
    gold_pity_counter = models.IntegerField(default=0)
    chest_counter = models.IntegerField(default=0)
    pvp_skips = models.IntegerField(default=5)

    def __str__(self):
        return self.user.userinfo.name + '(' + str(self.user.id) + ')'


class UserMatchState(models.Model):
    """UserMatchState represents a user's PvE match states.

    A staged state represents a match that has started (with results uploaded),
    but not yet reached the end of the count down.

    A committed state represents a match that has been recorded, with rewards
    and progress fully tracked.

    This model's main focus is to facilitate replay interactions, such as
    forfeiting or force-exiting. Individual states are tracked in a JSON
    field for each game mode for flexibility.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    campaign_state = JSONField(blank=True, null=True)
    tower_state = JSONField(blank=True, null=True)
    tunnels_state = JSONField(blank=True, null=True)
    dailydungeon_state = JSONField(blank=True, null=True)
    moevasion_state = JSONField(blank=True, null=True)


class Match(models.Model):
    """Match represents a QuickPlay match.

    This differs from Tournament matches which reference tournament members
    instead of users.
    """
    attacker = models.ForeignKey(User, on_delete=models.CASCADE)
    defender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opponent')
    is_win = models.BooleanField()

    # Match metadata.
    uploaded_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=15, blank=True, null=True)
    match_type = models.CharField(max_length=1, choices=(
        ('Q', 'Quickplay'),
    ))

    # User info at time of match.
    original_attacker_elo = models.IntegerField(default=0)
    updated_attacker_elo = models.IntegerField(default=0)
    original_defender_elo = models.IntegerField(default=0)
    updated_defender_elo = models.IntegerField(default=0)


    class Meta:
        indexes = [
            models.Index(fields=['attacker', 'defender', 'uploaded_at']),
        ]

    def __str__(self):
        return "%s (%s) vs %s" % (self.attacker.userinfo.name,
                                  "W" if self.is_win else "L",
                                  self.defender.userinfo.name)


class MatchReplay(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, primary_key=True)
    seed = models.IntegerField(blank=True, null=True)
    attacking_team = JSONField(blank=True, null=True)
    defending_team = JSONField(blank=True, null=True)

    # Duplicate-ish field on Match, but this allows us to clean up replays
    # separately easier.
    uploaded_at = models.DateTimeField(auto_now_add=True)


class DailyDungeonStatus(models.Model):
    """DailyDungeonStatus represents a user's progress (or lack of progress)
    in a single daily dungeon run. A user can only have one daily dungeon run
    at a time.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    is_golden = models.BooleanField(default=False)
    # Stage 0 implies that the player is currently NOT in a daily dungeon run.
    stage = models.IntegerField(default=0)
    # We expect character state to be in the format of
    # {<character_id>: <character_health>}.
    character_state = JSONField(blank=True, null=True)
    # The run date of the daily dungeon.
    run_date = models.DateField(auto_now=True)

    def is_active(self):
        return self.stage > 0 and self.run_date == date.today()

    def get_expired_for_user(user):
        q = DailyDungeonStatus.objects.filter(user=user,
                                              stage__gt=0,
                                              run_date__lt=date.today())
        return q[0] if q else None

    def get_active_for_user(user):
        q = DailyDungeonStatus.objects.filter(user=user,
                                              stage__gt=0,
                                              run_date=date.today())
        return q[0] if q else None


class DailyDungeonStage(models.Model):
    """
    DailyDungeonStage holds the 8 team comps that make up the 8 stages for
    the day's DailyDungeon run. This is updated by a daily cron job
    """
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    stage = models.IntegerField(default=0)
    # We expect team_comp to be in format of
    # [ {'char_id': <char_id>, 'position': <position>}, {...}, ... ]
    team_comp = JSONField(blank=True, null=True)

    def __str__(self):
        return 'Daily Dungeon Stage: ' + str(self.stage)


class MoevasionStatus(models.Model):
    """MoevasionStatus represents a user's progress (or lack of progress) in
    a single Moevasion run. NOTE: if we have more similar gamemodes like this
    in the future, we can look to consolidate the logic between this and
    daily dungeons.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    # Stage 0 implies that the player is currently NOT in a daily dungeon run.
    stage = models.IntegerField(default=0)
    # We expect character state to be in the format of
    # {<character_id>: <character_health>}.
    character_state = JSONField(blank=True, null=True)
    damage = models.BigIntegerField(default=0)

    def is_active(self):
        return self.stage > 0

    def start(self):
        self.stage = 1

    def end(self):
        self.stage = 0
        self.damage = 0
        self.character_state = None
        

class Chest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rarity = models.IntegerField()
    locked_until = models.DateTimeField(blank=True, null=True)
    tier_rank = models.IntegerField(choices=[(tier.value, tier.name) for tier in constants.Tiers],
                                    default=constants.Tiers.BRONZE_FIVE.value)


class EloRewardTracker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    last_completed = models.IntegerField(default=-1)
    last_claimed = models.IntegerField(default=-1)


class ChampBadgeTracker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    last_completed = models.IntegerField(default=-1)
    last_claimed = models.IntegerField(default=-1)


class SeasonReward(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    tier_rank = models.IntegerField(choices=[(tier.value, tier.name) for tier in constants.Tiers],
                                    default=constants.Tiers.BRONZE_FIVE.value)
    is_claimed = models.BooleanField(default=False)


def get_default_afk_datetime():
    return timezone.now() - timedelta(hours=3)


class Inventory(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    char_limit = models.IntegerField(default=50)
    coins = models.IntegerField(default=1000)
    gems = models.IntegerField(default=5000)
    dust = models.IntegerField(default=100)
    essence = models.IntegerField(default=0)
    relic_stones = models.IntegerField(default=0)
    champ_badges = models.IntegerField(default=0)
    daily_dungeon_ticket = models.IntegerField(default=3)
    daily_dungeon_golden_ticket = models.IntegerField(default=1)
    hero_exp = models.IntegerField(default=0)
    is_auto_retire = models.BooleanField(default=False)
    last_collected_rewards = models.DateTimeField(default=get_default_afk_datetime)
    profile_pics = ArrayField(models.IntegerField(), blank=True, null=True)

    gems_bought = models.IntegerField(default=0)

    chest_slot_1 = models.ForeignKey(Chest, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='chest_slot_1')
    chest_slot_2 = models.ForeignKey(Chest, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='chest_slot_2')
    chest_slot_3 = models.ForeignKey(Chest, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='chest_slot_3')
    chest_slot_4 = models.ForeignKey(Chest, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='chest_slot_4')

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
    sender_profile_picture_id = models.IntegerField(default=0)
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


class Clan2(models.Model):
    name = models.TextField(unique=True)
    description = models.TextField(default='A description has not been set.')
    chat = models.ForeignKey(Chat, null=True, on_delete=models.SET_NULL)
    time_started = models.DateTimeField(auto_now_add=True)
    elo = models.IntegerField(default=0)
    profile_picture = models.IntegerField(default=0)
    num_members = models.IntegerField(default=1)
    cap = models.IntegerField(default=30)
    exp = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['elo']),
            models.Index(fields=['exp']),
        ]

    def __str__(self):
        return "%d: %s" % (self.id, self.name)


def week_old_date(): return date.today() - timedelta(days=30)


class ClanMember(models.Model):
    userinfo = models.OneToOneField(UserInfo, on_delete=models.CASCADE, primary_key=True)
    clan2 = models.ForeignKey(Clan2, on_delete=models.SET_NULL, null=True, default=None)
    is_elder = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)  # Coleader
    is_owner = models.BooleanField(default=False)  # Leader

    # Defaults to the user's first characters.
    pve_character_lending = ArrayField(models.IntegerField(), default=list)
    # By tracking last reward on a per-user basis, we prevent clan hopping.
    last_farm_reward = models.DateField(default=week_old_date)


def empty_farms(): return [{}, {}, {}, {}, {}, {}, {}]
def empty_rewards(): return {'total_farms': 0, 'clan_members': []}


class ClanFarming(models.Model):
    clan = models.ForeignKey(Clan2, on_delete=models.CASCADE)
    # Dictionary for each day to track what players have farmed for a given
    # day in a week. Monday is index 0 (matches Python's weekday() function).
    daily_farms = ArrayField(JSONField(), default=empty_farms)

    # Track rewards for the previous week in-case it hasn't been claimed yet.
    # We also store IDs of clan members who were involved in the farm process.
    previous_farm_reward = models.DateField(default=week_old_date)
    unclaimed_rewards = JSONField(default=empty_rewards)

    def reset(self):
        self.daily_farms = empty_farms()


class ClanPVEResult(models.Model):
    """Store Clan PVE results for the best run the user had for a singular
    boss."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    boss = models.CharField(max_length=1, choices=(
        ('1', 'The Wall'),
        ('2', 'One Shot Wonder'),
        ('3', 'AOE Boss'), 
    ))
    best_score = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'boss')

    def __str__(self):
        return "%d: %s" % (self.user.id, self.boss)


class ClanPVEEvent(models.Model):
    clan = models.ForeignKey(Clan2, on_delete=models.CASCADE)
    date = models.DateField()
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('clan', 'date')

    def __str__(self):
        return "%s: %s" % (self.clan.name, str(self.date))


def clan_pve_ticket_default():
    return {'1': 1, '2': 1, '3': 1}

class ClanPVEStatus(models.Model):
    """Store Clan PVE tickets and character lending information for a given
    day."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(ClanPVEEvent, on_delete=models.CASCADE, null=True)
    # Store ticket in format of {'<mode_id>': <tickets>}.
    tickets_1 = JSONField(default=clan_pve_ticket_default)
    tickets_2 = JSONField(default=clan_pve_ticket_default)
    tickets_3 = JSONField(default=clan_pve_ticket_default)
    # Store characters to lend in the format of {'default': <bool>,
    # 'characters': [{'char_id': <int>, 'uses_remaining': <int>}]}.
    character_lending = JSONField(default=dict)
    # Current run information.
    current_boss = models.IntegerField(default=-1)
    current_borrowed_character = models.IntegerField(default=-1)

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return "%d: %s" % (self.user.id, str(self.event))


class ClanRequest(models.Model):
    userinfo = models.OneToOneField(UserInfo, on_delete=models.CASCADE)
    clan2 = models.ForeignKey(Clan2, on_delete=models.CASCADE)


class DungeonStage(models.Model):
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    stage = models.IntegerField(null=True)
    mob = models.ForeignKey(Placement, on_delete=models.CASCADE)
    player_exp = models.IntegerField()
    coins = models.IntegerField()
    gems = models.IntegerField()
    dungeon_type = models.IntegerField(choices=[(dungeon.value, dungeon.name) for dungeon in DungeonType], default=DungeonType.CAMPAIGN.value)
    story_text = models.TextField(default="", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['stage', 'dungeon_type'], name='unique_stage')
        ]

    def __str__(self):
        return "Stage " + str(self.stage)


class DungeonProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    campaign_stage = models.IntegerField()
    tower_stage = models.IntegerField(default=1)

    def __str__(self):
        return "user " + str(self.user.id) + ": campaign " + str(self.campaign_stage) + ", tower " + str(self.tower_stage)


class DungeonBoss(models.Model):
    stage = models.IntegerField()
    placement = models.ForeignKey(Placement, on_delete=models.CASCADE, blank=True, null=True)
    dungeon_type = models.IntegerField(choices=[(dungeon.value, dungeon.name) for dungeon in DungeonType], default=DungeonType.CAMPAIGN.value)

    # We expect team_comp to be in format of
    # [ {'char_id': <char_id>, 'position': <position>}, {...}, ... ]
    team_comp = JSONField(blank=True, null=True)

    # The character id of the carry in that level
    carry_id = models.IntegerField(default=-1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['stage', 'dungeon_type'], name='unique_dungeonboss')
        ]

    def __str__(self):
        return "Stage: " + str(self.stage)


class BaseQuest(models.Model):
    title = models.TextField()
    type = models.IntegerField()
    total = models.BigIntegerField()
    gems = models.IntegerField(default=0)
    coins = models.IntegerField(default=0)
    dust = models.IntegerField(default=0)
    item_type = models.ForeignKey(BaseItem, on_delete=models.CASCADE, blank=True, null=True)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "(" + str(self.id) + ") " + self.title


class CumulativeTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.BigIntegerField(default=0)
    type = models.IntegerField()

    def __str__(self):
        return "user: " + str(self.user.id) + ", type " + str(self.type) + ", progress: " + str(self.progress)


class PlayerQuestCumulative2(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    completed_quests = ArrayField(models.IntegerField(), blank=True, null=True, default=list)
    claimed_quests = ArrayField(models.IntegerField(), blank=True, null=True, default=list)


class PlayerQuestDaily(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.BigIntegerField(default=0)
    completed = models.BooleanField(default=False)
    claimed = models.BooleanField(default=False)
    expiration_date = models.DateTimeField()

    def __str__(self):
        return "user:" + str(self.user_id) + " " + self.base_quest.title


class PlayerQuestWeekly(models.Model):
    base_quest = models.ForeignKey(BaseQuest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.BigIntegerField(default=0)
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


class IPTracker(models.Model):
    ip = models.TextField(unique=True)
    user_list = ArrayField(models.IntegerField(), blank=True, null=True, default=list)
    suspicious = models.BooleanField(default=False)

    def __str__(self):
        return str(self.ip)


class HackerAlert(models.Model):
    """An alert indicating a potential hacking incident by user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Detailed info of hacker's activity.
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='report')
    suspicious_match_id = models.IntegerField(default=0)
    notes = models.TextField(default='')

    # Metadata for management.
    verified_hacker = models.BooleanField(null=True, blank=True)

    def __str__(self):
        if self.reporter:
            return str(self.user) + ' reporter by ' + str(self.reporter)
        else:
            return str(self.user)


class Tournament(models.Model):
    round = models.IntegerField(default=0)
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
    attacker = models.ForeignKey(TournamentMember, on_delete=models.CASCADE)
    defender = models.ForeignKey(TournamentMember, on_delete=models.CASCADE, related_name='opponent')
    is_win = models.BooleanField(blank=True, null=True)
    has_played = models.BooleanField(default=False)
    round = models.IntegerField()
    # TODO: reference to replay when it's implemented

    def __str__(self):
        return str(self.id) + ": tourney(" + str(self.attacker.tournament) +"): attacker(" + str(self.attacker) + ") defender(" + str(self.defender) +")"


class TournamentTeam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)


class TournamentSelectionCards(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cards = ArrayField(models.IntegerField())


class InvalidReceipt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.TextField()
    date = models.IntegerField()
    product_id = models.TextField()
    receipt = models.TextField(default='')


class BaseDeal(models.Model):
    gems = models.IntegerField(default=0)
    coins = models.IntegerField(default=0)
    dust = models.IntegerField(default=0)
    item = models.ForeignKey(BaseItem, on_delete=models.CASCADE, blank=True, null=True)
    item_quantity = models.IntegerField(default=0)
    char_type = models.ForeignKey(BaseCharacter, on_delete=models.CASCADE, blank=True, null=True)
    deal_type = models.IntegerField(choices=[(deal.value, deal.name) for deal in DealType])
    order = models.IntegerField(default=0)
    gems_cost = models.IntegerField(default=0)
    purchase_id = models.TextField(default='')

    def __str__(self):
        return "ID: " + str(self.id) + " Type: " + str(self.deal_type) + " Order: " + str(self.order)


class ActiveDeal(models.Model):
    base_deal = models.ForeignKey(BaseDeal, on_delete=models.CASCADE)
    expiration_date = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['expiration_date']),
        ]


class PurchasedTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deal = models.ForeignKey(ActiveDeal, on_delete=models.SET_NULL, blank=True, null=True)
    purchase_id = models.TextField(default='')
    transaction_id = models.TextField(default='')
    purchase_time = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'deal'], name='unique_purchase')
        ]


def default_slot_list():
    return [-1] * constants.LEVEL_BOOSTER_SLOTS


def default_cooldown_slot_list():
    return [None] * constants.LEVEL_BOOSTER_SLOTS


class LevelBooster(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    booster_level = models.IntegerField(default=240)
    unlocked_slots = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(constants.LEVEL_BOOSTER_SLOTS)])

    # slots contain the char_id of the heroes
    slots = ArrayField(models.IntegerField(), default=default_slot_list)

    # list of either the cooldown datetime or None
    cooldown_slots = ArrayField(models.DateTimeField(blank=True, null=True), default=default_cooldown_slot_list)


class RelicShop(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    purchased_relics = ArrayField(models.IntegerField(), default=list)


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    legendaries = ArrayField(models.IntegerField(), default=list)
    epics = ArrayField(models.IntegerField(), default=list)
    rares = ArrayField(models.IntegerField(), default=list)
    is_active = models.BooleanField(default=False)


def chapter_rewards_pack_deadline():
    return timezone.now() + timedelta(days=14)


class ChapterRewardPack(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    is_active = models.BooleanField(default=False)
    last_completed = models.IntegerField(default=-1)
    last_claimed = models.IntegerField(default=-1)
    expiration_date = chapter_rewards_pack_deadline()
    type = models.IntegerField(choices=[(chapter.value, chapter.name) for chapter in constants.ChapterRewardsPack],
                               default=constants.ChapterRewardsPack.CHAPTER19)


def create_user_referral(user):
    try:
        UserReferral.objects.create(user=user, referral_code=generate_referral_code())
    except IntegrityError:
        create_user_referral(user)


@receiver(post_save, sender=User)
def create_user_info(sender, instance, created, **kwargs):
    if created:

        # starter team / 3 peasants
        peasant_archer = Character.objects.create(user=instance, char_type_id=1)
        peasant_mage = Character.objects.create(user=instance, char_type_id=2)
        peasant_swordsman = Character.objects.create(user=instance, char_type_id=3)

        default_placement = Placement.objects.create(user=instance,
                                                     char_1=peasant_swordsman, pos_1=3,
                                                     char_2=peasant_archer, pos_2=10,
                                                     char_3=peasant_mage, pos_3=11)

        userinfo = UserInfo.objects.create(user=instance, default_placement=default_placement)
        UserStats.objects.create(user=instance)
        Inventory.objects.create(user=instance)
        ClanMember.objects.create(userinfo=userinfo, pve_character_lending=[
            peasant_archer.char_id, peasant_mage.char_id,
            peasant_swordsman.char_id])
        DungeonProgress.objects.create(user=instance, campaign_stage=1)
        EloRewardTracker.objects.create(user=instance)
        ChampBadgeTracker.objects.create(user=instance)
        SeasonReward.objects.create(user=instance)
        LevelBooster.objects.create(user=instance)
        RelicShop.objects.create(user=instance)
        Wishlist.objects.create(user=instance)
        create_user_referral(instance)

        # Add quests
        expiry_date_weekly = get_expiration_date(7)
        expiry_date_daily = get_expiration_date(1)
        create_cumulative_trackers(instance)
        PlayerQuestCumulative2.objects.create(user=instance)
        create_quests_by_class(instance, ActiveWeeklyQuest.objects.all()[:constants.NUM_WEEKLY_QUESTS], PlayerQuestWeekly, expiry_date_weekly)
        create_quests_by_class(instance, ActiveDailyQuest.objects.all()[:constants.NUM_DAILY_QUESTS], PlayerQuestDaily, expiry_date_daily)

        # Add welcome messages, if developer account IDs are defined in env
        if DEV_ACCOUNT_IDS:
            devUserId = random.choice(DEV_ACCOUNT_IDS)
            devUser = User.objects.get(id=devUserId)
            userName = UserInfo.objects.get(user_id=instance.id).name
            devUserName = UserInfo.objects.get(user_id=devUserId).name
            chat = Chat.objects.create(chat_name="dm(%s)" % (devUser.get_username()))
            # TODO(advait): add db-level constraint to prevent duplicate friend pairs
            Friend.objects.create(user_1=instance, user_2=devUser, chat=chat)
            welcomeMessage1 = "Hey there %s! I'm %s, one of the creators of the game. Thanks so much for giving Early Access a shot, you're one of the first people to play it!\n\nPlease note that we're still in active development, and many things may break or change in the process." % (userName, devUserName)
            welcomeMessage2 = "That being said, Early Access users will receive double all gems bought or collected from the shop once we release 1.0. And all progress on your account carries over after Beta."
            welcomeMessage3 = "We also have a big and growing community on " + """<link="https://discord.gg/bQR8DZW"><u><color=#0EB7FF>Discord</color></u></link>""" + " - please join us!\n\nNote that I won't be able to keep track of all messages sent here, but all us devs are super active on Discord!"
            welcomeMessage4 = "Again, thanks for trying out the game, and please send us all your feedback. Battle on!"

            ChatMessage.objects.create(chat=chat, message=welcomeMessage1, sender=devUser)
            ChatMessage.objects.create(chat=chat, message=welcomeMessage2, sender=devUser)
            ChatMessage.objects.create(chat=chat, message=welcomeMessage3, sender=devUser)
            ChatMessage.objects.create(chat=chat, message=welcomeMessage4, sender=devUser)


def create_cumulative_trackers(user):
    trackers = []
    active_quests = ActiveCumulativeQuest.objects.all()
    base_quest_types = []
    for quest in active_quests:
        if quest.base_quest.type not in base_quest_types:
            progress_tracker = CumulativeTracker(user=user, type=quest.base_quest.type)
            base_quest_types.append(quest.base_quest.type)
            trackers.append(progress_tracker)

    CumulativeTracker.objects.bulk_create(trackers)


def create_quests_by_class(user, active_quests, quest_class, expiry_date):
    bulk_quests = []
    for quest in active_quests:
        player_quest = quest_class(base_quest=quest.base_quest, user=user, expiration_date=expiry_date)
        bulk_quests.append(player_quest)
    quest_class.objects.bulk_create(bulk_quests)


# Gets the next expiration date which is just midnight no time zone
def get_expiration_date(interval):
    if interval == 1:
        delta = 1
    else:
        delta = (7 - datetime.today().weekday()) % 7
        if delta == 0:
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
