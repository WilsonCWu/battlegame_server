from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields
from functools import lru_cache
from enum import Enum

from playerdata.models import BaseCharacter
from playerdata.models import BaseCharacterAbility2
from playerdata.models import BaseCharacterStats
from playerdata.models import BaseItem
from playerdata.models import BasePrestige
from playerdata.models import Flag, UserFlag


class UserSchema(Schema):
    user_id = fields.Int(attribute='id')
    first_name = fields.Str()


class BaseCharacterSchema(Schema):
    char_type = fields.Int()
    name = fields.Str()
    rarity = fields.Int()
    rollable = fields.Bool()


class BaseCharacterStatsSchema(Schema):
    char_type = fields.Int(attribute='char_type_id')
    health = fields.Int()
    starting_mana = fields.Int()
    mana = fields.Int()
    starting_ability_ticks = fields.Int()
    ability_ticks = fields.Int()
    speed = fields.Int()
    attack_damage = fields.Int()
    ability_damage = fields.Int()
    attack_speed = fields.Float()
    ar = fields.Int()
    mr = fields.Int()
    attack_range = fields.Int()
    crit_chance = fields.Int()
    health_scale = fields.Int()
    attack_scale = fields.Int()
    ability_scale = fields.Int()
    ar_scale = fields.Int()
    mr_scale = fields.Int()


class BaseCharacterAbilitySchema(Schema):
    char_type = fields.Int(attribute='char_type_id')
    ability1_specs = fields.Str()
    ability2_specs = fields.Str()
    ability3_specs = fields.Str()
    ultimate_specs = fields.Str()


class StatModifierSchema(Schema):
    attack_flat = fields.Int()
    attack_mult = fields.Float()
    ability_flat = fields.Int()
    ability_mult = fields.Float()
    attack_speed_flat = fields.Float()
    attack_speed_mult = fields.Float()
    ar_flat = fields.Int()
    ar_mult = fields.Float()
    mr_flat = fields.Int()
    mr_mult = fields.Float()
    speed_flat = fields.Int()
    speed_mult = fields.Float()
    crit_flat = fields.Int()
    crit_mult = fields.Float()
    mana_tick_flat = fields.Int()
    mana_tick_mult = fields.Float()
    range_flat = fields.Int()
    max_health_flat = fields.Int()
    max_health_mult = fields.Float()


class BaseItemSchema(StatModifierSchema):
    item_type = fields.Int()
    name = fields.Str()
    description = fields.Str()
    gear_slot = fields.String()

    rarity = fields.Int()
    cost = fields.Int()
    is_unique = fields.Bool()


class BasePrestigeSchema(StatModifierSchema):
    char_type = fields.Int(attribute='char_type_id')
    level = fields.Int()


class FlagName(Enum):
    LEVEL_BOOST_240 = 'level_boost_240'


@lru_cache()
def get_char_rarity(char_type: int):
    return BaseCharacter.objects.get(char_type=char_type).rarity


# returns false if flag doesn't exist or is false value
def is_flag_active(flag_name: FlagName):
    flag = Flag.objects.filter(name=flag_name.value).first()
    return flag and flag.value


class BaseInfoView(APIView):
    permission_classes = (IsAuthenticated,)

    def serialize_base_characters(version):
        if version is not None:
            stats = BaseCharacterStats.get_active_under_version(version)
        else:
            stats = BaseCharacterStats.get_active()

        for bc in BaseCharacter.objects.all():
            serialized = BaseCharacterSchema(bc).data

            char_stats = next(s for s in stats if s.char_type.char_type == bc.char_type)
            serialized_stats = BaseCharacterStatsSchema(char_stats).data
            serialized.update(serialized_stats)
            yield serialized

    def flags(user):
        """Return global flags with user overrides for the given user."""
        flags = {f.name: {'name': f.name, 'value': f.value} for f in Flag.objects.all()}
        for uf in UserFlag.objects.select_related('flag').filter(user=user):
            flags[uf.flag.name]['value'] = uf.value
        return list(flags.values())

    def get(self, request, version=None):
        itemSerializer = BaseItemSchema(BaseItem.objects.all(), many=True)
        prestigeSerializer = BasePrestigeSchema(BasePrestige.objects.all(), many=True)

        # For specs, check if the client specified a spec version - if not,
        # just return the latest.
        if version is not None:
            specSerializer = BaseCharacterAbilitySchema(BaseCharacterAbility2.get_active_under_version(version), many=True)
        else:
            specSerializer = BaseCharacterAbilitySchema(BaseCharacterAbility2.get_active(), many=True)

        return Response({
            'status': True,
            'characters': list(BaseInfoView.serialize_base_characters(version)),
            'items': itemSerializer.data,
            'specs': specSerializer.data,
            'prestige': prestigeSerializer.data,
            'flags': BaseInfoView.flags(request.user),
        })
