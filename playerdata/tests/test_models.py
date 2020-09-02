from django.core.exceptions import ValidationError
from django.test import TestCase

from playerdata.models import BaseCharacter, Character, BaseItem, Item, User

class CharacterTestCase(TestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.user = User.objects.get(username='battlegame')
        self.base_char = BaseCharacter.objects.get(name='Archer')
        self.character = Character.objects.create(user=self.user, char_type=self.base_char)

    def test_item_slot_validation(self):
        base_hat = BaseItem.objects.create(
            item_type=99,
            name='wizard hat',
            gear_slot='H',
            rarity=1,
            cost=10,
        )
        self.character.hat = Item.objects.create(item_type=base_hat, user=self.user)
        self.character.full_clean()

        with self.assertRaises(ValidationError):
            base_hat.gear_slot='W'
            base_hat.save()
            self.character.full_clean()

        # Does not validate when no item is given.
        self.character.hat = None
        self.character.full_clean()

    def test_unique_trinket_validation(self):
        base_trinket = BaseItem.objects.create(
            item_type=99,
            name='ring',
            gear_slot='T',
            rarity=1,
            cost=10,
        )
        trinket = Item.objects.create(item_type=base_trinket, user=self.user)
        self.character.trinket_1 = trinket
        self.character.save()
        self.character.full_clean()

        with self.assertRaises(ValidationError):
            self.character.trinket_2 = trinket
            self.character.full_clean()

        with self.assertRaises(ValidationError):
            other_character = Character.objects.create(
                user=self.user, char_type=self.base_char, trinket_2=trinket)
            other_character.full_clean()
