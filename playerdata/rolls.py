import random
from playerdata import constants, wishlist
from playerdata.models import BaseItem, BaseCharacter, Character, Item
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
def get_weighted_odds_item(rarity_odds=None, excluded_ids=None):
    if rarity_odds is None:
        rarity_odds = constants.REGULAR_ITEM_ODDS_PER_CHEST[0]  # default SILVER chest rarity odds

    rarity = constants.ITEM_RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_rand_base_item_from_rarity(rarity, excluded_ids)


def get_rand_base_item_from_rarity(rarity, excluded_ids=None):
    if excluded_ids is None:
        base_items = BaseItem.objects.filter(rarity=rarity, rollable=True)
    else:
        base_items = BaseItem.objects.filter(rarity=rarity, rollable=True).exclude(item_type__in=excluded_ids)

    num_items = base_items.count()
    chosen_item = base_items[random.randrange(num_items)]
    return chosen_item


def get_n_unique_weighted_odds_item(user, num_rolls, rarity_odds=None):
    items = []
    unique_ids = list(Item.objects.filter(user=user, item_type__is_unique=True).values_list('item_type_id', flat=True))

    for n in range(0, num_rolls):
        items.append(get_weighted_odds_item(rarity_odds, unique_ids))

    return items


# returns a random BaseCharacter with weighted odds
def get_weighted_odds_character(rarity_odds=None, available_chars=None):
    if rarity_odds is None:
        rarity_odds = constants.SUMMON_RARITY_BASE

    rarity = constants.CHAR_RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_rand_base_char_from_rarity(rarity, available_chars)


# returns a random character with weighted odds + wishlist odds
# double chance wrt non-wishlist chars
def get_wishlist_odds_char_type(wish_list, rarity_odds=None):
    if rarity_odds is None:
        rarity_odds = constants.SUMMON_RARITY_BASE

    rarity = constants.CHAR_RARITY_INDEX[weighted_pick_from_buckets(rarity_odds)]
    return get_wishlist_base_char_from_rarity(wish_list, rarity)


def get_wishlist_base_char_from_rarity(wish_list, rarity) -> int:
    base_chars = list(BaseCharacter.objects.filter(rarity=rarity, rollable=True).values_list('char_type', flat=True))
    wishlist_copies = wishlist.get_wishlist_chars_for_rarity(wish_list, rarity)
    base_chars.extend(wishlist_copies)
    num_chars = len(base_chars)

    chosen_char = base_chars[random.randrange(num_chars)]
    return chosen_char


def get_rand_base_char_from_rarity(rarity, available_chars=None) -> BaseCharacter:
    if available_chars is None:
        base_chars = BaseCharacter.objects.filter(rarity=rarity, rollable=True)
    else:
        base_chars = BaseCharacter.objects.filter(rarity=rarity, rollable=True, char_type__in=available_chars)
    num_chars = base_chars.count()
    if num_chars == 0:
        return None
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


# Normal distribution gem drop
# minimum of 150 gems
# if you win the lottery you get 10k gems
def login_chest_gems():
    # lotto max jackpot
    retire_young_baby = random.randint(1, 1000)
    if retire_young_baby == 888:
        return 10000

    mu = 250
    sigma = 100
    return int(max(random.gauss(mu, sigma), 150))
