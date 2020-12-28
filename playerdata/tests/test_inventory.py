from rest_framework import status
from rest_framework.test import APITestCase
import playerdata.constants

from playerdata.models import User, BaseCharacter, Character, BaseItem, Item


class EquipItemAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        base_bow = BaseItem.objects.get(name="Bow")
        self.owned_bow = Item.objects.create(
            user=self.u,
            item_type=base_bow,
            exp=0,
        )

        base_archer = BaseCharacter.objects.get(name="Archer")
        self.owned_archer = Character.objects.create(
            user=self.u,
            char_type=base_archer,
        )

    def test_equipping_item(self):
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'W',
            'target_char_id': self.owned_archer.char_id,
            'target_item_id': self.owned_bow.item_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.owned_archer.refresh_from_db()
        self.assertEqual(self.owned_archer.weapon, self.owned_bow)

    def test_equipping_item_wrong_slot(self):
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'H',
            'target_char_id': self.owned_archer.char_id,
            'target_item_id': self.owned_bow.item_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
        self.owned_archer.refresh_from_db()
        self.assertIsNone(self.owned_archer.hat)
        self.assertIsNone(self.owned_archer.weapon)

    def test_equipping_equipped_item(self):
        self.owned_archer.weapon = self.owned_bow
        self.owned_archer.save()

        owned_archer_2 = Character.objects.create(
            user=self.u,
            char_type=self.owned_archer.char_type,
        )

        # This request will result in a DB transactional failure, as we have
        # one-to-one setup for character and items.
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'W',
            'target_char_id': owned_archer_2.char_id,
            'target_item_id': self.owned_bow.item_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_equipping_duplicate_trinkets(self):
        base_trinket = BaseItem.objects.create(
            item_type=99,
            name='ring',
            gear_slot='T',
            rarity=1,
            cost=10,
        )
        trinket = Item.objects.create(item_type=base_trinket, user=self.u)

        self.owned_archer.trinket_1 = trinket
        self.owned_archer.save()

        # Re-equipping is a no-op.
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'T1',
            'target_char_id': self.owned_archer.char_id,
            'target_item_id': trinket.item_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.owned_archer.refresh_from_db()
        self.assertEqual(self.owned_archer.trinket_1, trinket)

        # Equipping same trinket on different slot fails.
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'T2',
            'target_char_id': self.owned_archer.char_id,
            'target_item_id': trinket.item_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
        self.owned_archer.refresh_from_db()
        self.assertIsNone(self.owned_archer.trinket_2)

        # Equipping same trinket on different character fails.
        owned_archer_2 = Character.objects.create(
            user=self.u,
            char_type=self.owned_archer.char_type,
        )
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'T2',
            'target_char_id': owned_archer_2.char_id,
            'target_item_id': trinket.item_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
        owned_archer_2.refresh_from_db()
        self.assertIsNone(owned_archer_2.trinket_2)


class UnequipItemAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_equipping_item(self):
        # First create a character with an item.
        base_bow = BaseItem.objects.get(name="Bow")
        base_archer = BaseCharacter.objects.get(name="Archer")

        owned_bow = Item.objects.create(
            user=self.u,
            item_type=base_bow,
            exp=0,
        )
        owned_archer = Character.objects.create(
            user=self.u,
            char_type=base_archer,
            weapon=owned_bow,
        )

        # Unequip the same item.
        response = self.client.post('/inventory/unequipitem/', {
            'target_slot': 'W',
            'target_char_id': owned_archer.char_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        owned_archer.refresh_from_db()
        self.assertIsNone(owned_archer.weapon)


class LevelUpAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_level_up_max_cap(self):
        base_archer = BaseCharacter.objects.get(name="Archer")
        owned_archer = Character.objects.create(
            user=self.u,
            char_type=base_archer,
            copies=2,
            level=playerdata.constants.MAX_CHARACTER_LEVEL,
        )
        inventory = self.u.inventory
        inventory.coins += 1000000000
        inventory.save()

        response = self.client.post('/levelup/', {
            'target_char_id': owned_archer.char_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
        self.assertIn('already hit max level 170', response.data['reason'])


class PrestigeAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_prestige(self):
        base_ninja = BaseCharacter.objects.get(name="Ninja")
        owned_ninja = Character.objects.create(
            user=self.u,
            char_type=base_ninja,
            copies=2,
            level=30,
        )

        response = self.client.post('/prestige/', {
            'target_char_id': owned_ninja.char_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        owned_ninja.refresh_from_db()
        self.assertEqual(owned_ninja.prestige, 1)

    def test_prestige_cap(self):
        base_ninja = BaseCharacter.objects.get(name="Ninja")
        owned_ninja = Character.objects.create(
            user=self.u,
            char_type=base_ninja,
            copies=500,
            level=30,
            prestige=5
        )

        response = self.client.post('/prestige/', {
            'target_char_id': owned_ninja.char_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
        self.assertIn('character has already hit max prestige', response.data['reason'])
