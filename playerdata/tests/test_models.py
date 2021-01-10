from django.core.exceptions import ValidationError
from django.test import TestCase

from playerdata.models import BaseCharacter, BaseCharacterAbility, Character, BaseItem, Item, User

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


class BaseCharacterAbilityTestCase(TestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.base_char = BaseCharacter.objects.get(name='Archer')

    def test_valid_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "1": {
                "foo": 1,
            },
        }
        specs.ability2_specs = {
            "21": {
                "boo": 1,
            },
            "41": {
                "boo": 2,
            },
        }
        specs.full_clean()

    def test_off_indexed_level_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "12": {
                "foo": 1,
            },
        }

        with self.assertRaises(ValidationError):
            specs.full_clean()

    def test_non_numeric_inner_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "1": {
                "foo": "hello",
            },
        }

        with self.assertRaises(ValidationError):
            specs.full_clean()

    def test_duplicate_level_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "1": {
                "foo": 1,
            },
        }
        specs.ability2_specs = {
            "1": {
                "foo": 2,
            },
        }

        with self.assertRaises(ValidationError):
            specs.full_clean()

    def test_missing_level_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "1": {
                "foo": 1,
            },
        }
        specs.ability2_specs = {
            "41": {
                "foo": 2,
            },
        }

        with self.assertRaises(ValidationError):
            specs.full_clean()

    def test_bad_key_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "hello1": {
                "foo": 1,
            },
        }

        with self.assertRaises(ValidationError):
            specs.full_clean()

    def test_prestige_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "1": {
                "foo": 1,
            },
            "prestige-1": {
                "foo": 2,
            },
        }
        specs.full_clean()

    def test_over_prestiged_spec(self):
        specs = BaseCharacterAbility.objects.create(char_type=self.base_char)
        specs.ability1_specs = {
            "prestige-12": {
                "foo": 1,
            },
        }
        with self.assertRaises(ValidationError):
            specs.full_clean()
