from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import BaseCharacter
from playerdata.models import BaseItem


class UserSchema(Schema):
    user_id = fields.Int(attribute='id')
    first_name = fields.Str()


class BaseCharacterSchema(Schema):
    char_type = fields.Int()
    name = fields.Str()
    health = fields.Int()
    mana = fields.Int()
    speed = fields.Int()
    attack_damage = fields.Int()
    ability_damage = fields.Int()
    attack_speed = fields.Float()
    ar = fields.Int()
    mr = fields.Int()
    attack_range = fields.Int()
    rarity = fields.Int()
    crit_chance = fields.Int()
    health_scale = fields.Int()
    attack_scale = fields.Int()
    ability_scale = fields.Int()
    ar_scale = fields.Int()
    mr_scale = fields.Int()
    specs = fields.Str()


class BaseItemSchema(Schema):
    item_type = fields.Int()
    name = fields.Str()
    description = fields.Str()
    gear_slot = fields.String()

    rarity = fields.Int()
    cost = fields.Int()
    is_unique = fields.Bool()

    attack_flat = fields.Int()
    attack_mult = fields.Float()
    ability_flat = fields.Int()
    ability_mult = fields.Float()
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


class BaseInfoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        charSerializer = BaseCharacterSchema(BaseCharacter.objects.all(), many=True)
        itemSerializer = BaseItemSchema(BaseItem.objects.all(), many=True)
        return Response({'characters': charSerializer.data, 'items': itemSerializer.data})
