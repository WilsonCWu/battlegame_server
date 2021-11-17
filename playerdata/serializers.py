from rest_framework import serializers


class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class RecoverAccountSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    token = serializers.CharField(required=True)


class CreateNewUserSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class ChangeNameSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)


class GetUserSerializer(serializers.Serializer):
    target_user = serializers.IntegerField(required=True)


class GetOpponentsSerializer(serializers.Serializer):
    search_count = serializers.IntegerField(required=True)


class BotResultsSerializer(serializers.Serializer):
    id1s = serializers.ListField(child=serializers.IntegerField(), required=True)
    id2s = serializers.ListField(child=serializers.IntegerField(), required=True)
    wons = serializers.ListField(child=serializers.BooleanField(), required=True)


class UpdatePlacementSerializer(serializers.Serializer):
    placement_id = serializers.IntegerField(required=False)
    characters = serializers.ListField(child=serializers.IntegerField(),
        required=True, min_length=5, max_length=5)
    positions = serializers.ListField(child=serializers.IntegerField(),
        required=True, min_length=5, max_length=5)


class UploadResultSerializer(serializers.Serializer):
    result = serializers.JSONField()


class DailyDungeonStartSerializer(serializers.Serializer):
    is_golden = serializers.BooleanField(required=True)
    tier = serializers.IntegerField(required=True)


class CharStateResultSerializer(serializers.Serializer):
    is_loss = serializers.BooleanField(required=True)
    characters = serializers.JSONField(required=True)


class MoevasionResultSerializer(serializers.Serializer):
    is_loss = serializers.BooleanField(required=True)
    characters = serializers.JSONField(required=True)
    damage = serializers.IntegerField(required=True)


class TargetCharSerializer(serializers.Serializer):
    target_char_id = serializers.IntegerField(required=True)


class BuyItemSerializer(serializers.Serializer):
    target_item_type = serializers.IntegerField(required=True)


class ValidateReceiptSerializer(serializers.Serializer):
    receipt = serializers.CharField(required=True)
    store = serializers.IntegerField(required=True)
    transaction_id = serializers.CharField(required=True)
    new_purchase_token = serializers.CharField(required=False)


class PurchaseSerializer(serializers.Serializer):
    purchase_id = serializers.CharField(required=True)
    transaction_id = serializers.CharField(required=True)


class PurchaseItemSerializer(serializers.Serializer):
    purchase_item_id = serializers.CharField(required=True)


class ValueSerializer(serializers.Serializer):
    value = serializers.CharField(required=True)


class BooleanSerializer(serializers.Serializer):
    value = serializers.BooleanField(required=True)


class IntSerializer(serializers.Serializer):
    value = serializers.IntegerField(required=True)


class NullableValueSerializer(serializers.Serializer):
    value = serializers.CharField(required=True, allow_blank=True)


class NewClanSerializer(serializers.Serializer):
    clan_name = serializers.CharField(required=True)
    clan_description = serializers.CharField(required=True)


class AcceptFriendRequestSerializer(serializers.Serializer):
    accept = serializers.BooleanField(required=True)
    target_id = serializers.IntegerField(required=True)


class UpdateClanMemberStatusSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(required=True)
    member_status = serializers.CharField(required=True)


class UpdateClanRequestSerializer(serializers.Serializer):
    target_user_id = serializers.IntegerField(required=True)
    accept = serializers.BooleanField(required=True)


class ClaimQuestSerializer(serializers.Serializer):
    quest_id = serializers.IntegerField(required=True)


class RedeemCodeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)


class ClaimReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(required=True)
    device_id = serializers.CharField(required=True)


class SelectCardSerializer(serializers.Serializer):
    selection = serializers.JSONField(required=True)


class GetCardSerializer(serializers.Serializer):
    num_cards = serializers.IntegerField(required=True)


class SetDefenceSerializer(serializers.Serializer):
    pos_1 = serializers.IntegerField(required=True)
    char_1 = serializers.IntegerField(required=True)
    pos_2 = serializers.IntegerField(required=True)
    char_2 = serializers.IntegerField(required=True)
    pos_3 = serializers.IntegerField(required=True)
    char_3 = serializers.IntegerField(required=True)
    pos_4 = serializers.IntegerField(required=True)
    char_4 = serializers.IntegerField(required=True)
    pos_5 = serializers.IntegerField(required=True)
    char_5 = serializers.IntegerField(required=True)


class EquipItemSerializer(serializers.Serializer):
    target_char_id = serializers.IntegerField(required=True)
    target_item_id = serializers.IntegerField(required=True)
    target_slot = serializers.ChoiceField((
        ('H', 'Hat'),
        ('A', 'Armor'),
        ('B', 'Boots'),
        ('W', 'Weapon'),
        ('T1', 'Tricket 1'),
        ('T2', 'Tricket 2'),
    ), required=True)


class UnequipItemSerializer(serializers.Serializer):
    target_char_id = serializers.IntegerField(required=True)
    target_slot = serializers.ChoiceField((
        ('H', 'Hat'),
        ('A', 'Armor'),
        ('B', 'Boots'),
        ('W', 'Weapon'),
        ('T1', 'Tricket 1'),
        ('T2', 'Tricket 2'),
    ), required=True)


class ScrapItemSerializer(serializers.Serializer):
    scrap_item_ids = serializers.JSONField(required=True)
    target_item_id = serializers.IntegerField(required=True)


class CollectChestSerializer(serializers.Serializer):
    chest_id = serializers.IntegerField(required=True)
    is_skip = serializers.BooleanField(required=True)


class SetDungeonProgressSerializer(serializers.Serializer):
    is_win = serializers.BooleanField(required=True)
    dungeon_type = serializers.IntegerField(required=True)
    token = serializers.CharField(required=False)


class GetMatchHistorySerializer(serializers.Serializer):
    count = serializers.IntegerField(required=True)


class SlotSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField(required=True)
    char_id = serializers.IntegerField(required=True)


class SendMailSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField(required=True)
    message = serializers.CharField(required=True)


class SummonShardSerializer(serializers.Serializer):
    num_chars = serializers.IntegerField(required=True)
    rarity = serializers.IntegerField(required=True)


class StarterPetSerializer(serializers.Serializer):
    pet_id = serializers.IntegerField(required=True)
    legacy_unlock = serializers.BooleanField(required=True)
