import random
from playerdata import constants
from playerdata.models import BaseItem, BaseCharacter, Character
from playerdata.questupdater import QuestUpdater


# General function that rolls a bucket based on weighted odds
# Expects: buckets to be a list of odds that sum to 1000
# Returns: index of the bucket that was picked
def weighted_pick_from_buckets(buckets):
    rand = random.randint(1, 1000)
    total = 0
    for i, bucket in enumerate(buckets):
        total += bucket
        if rand <= total:
            return i

    raise Exception('Invalid bucket total')


# returns a random BaseItem with weighted odds
def get_weighted_odds_item(rarity_odds=None):
    if rarity_odds is None:
        rarity_odds = constants.REGULAR_ITEM_ODDS_PER_CHEST[0]  # default SILVER chest rarity odds

    rarity = constants.ITEM_RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_rand_base_item_from_rarity(rarity)


def get_rand_base_item_from_rarity(rarity):
    base_items = BaseItem.objects.filter(rarity=rarity, rollable=True)
    num_items = base_items.count()
    chosen_item = base_items[random.randrange(num_items)]
    return chosen_item


# returns a random BaseCharacter with weighted odds
def get_weighted_odds_character(rarity_odds=None, available_chars=None):
    if rarity_odds is None:
        rarity_odds = constants.SUMMON_RARITY_BASE

    rarity = constants.CHAR_RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_rand_base_char_from_rarity(rarity, available_chars)


def get_rand_base_char_from_rarity(rarity, available_chars=None):
    if available_chars is None:
        base_chars = BaseCharacter.objects.filter(rarity=rarity, rollable=True)
    else:
        base_chars = BaseCharacter.objects.filter(rarity=rarity, rollable=True, char_type__in=available_chars)
    num_chars = base_chars.count()
    chosen_char = base_chars[random.randrange(num_chars)]
    return chosen_char


def insert_character(user, chosen_char_id):
    old_char = Character.objects.filter(user=user, char_type_id=chosen_char_id).first()

    if old_char:
        old_char.copies += 1
        old_char.save()
        return old_char

    new_char = Character.objects.create(user=user, char_type_id=chosen_char_id)
    QuestUpdater.add_progress_by_type(user, constants.OWN_HEROES, 1)
    return new_char
