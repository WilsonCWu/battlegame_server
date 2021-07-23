from rest_framework import status
from rest_framework.test import APITestCase
import playerdata.constants
from playerdata import formulas, constants

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
            level=201,
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
        self.assertEqual(response.data['unequip_char_id'], -1)

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
            level=201,
        )

        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'W',
            'target_char_id': owned_archer_2.char_id,
            'target_item_id': self.owned_bow.item_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.owned_archer.refresh_from_db()
        owned_archer_2.refresh_from_db()
        self.assertEqual(response.data['unequip_char_id'], self.owned_archer.char_id)
        self.assertEqual(response.data['unequip_slot'], 'W')
        self.assertIsNone(self.owned_archer.weapon)
        self.assertEqual(owned_archer_2.weapon, self.owned_bow)


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

        # Equipping same trinket on different slot succeeds.
        response = self.client.post('/inventory/equipitem/', {
            'target_slot': 'T2',
            'target_char_id': self.owned_archer.char_id,
            'target_item_id': trinket.item_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.owned_archer.refresh_from_db()
        self.assertEqual(response.data['unequip_char_id'], self.owned_archer.char_id)
        self.assertEqual(response.data['unequip_slot'], 'T1')
        self.assertIsNone(self.owned_archer.trinket_1)
        self.assertEqual(self.owned_archer.trinket_2, trinket)


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
        self.assertIn('already hit max level ' + str(playerdata.constants.MAX_CHARACTER_LEVEL), response.data['reason'])


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


class RefundAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_refund(self):
        char1 = Character.objects.filter(user=self.u).first()
        char1.level = 200
        char1.save()

        inventory = self.u.inventory
        inventory.coins = 0
        inventory.dust = 0
        inventory.gems = 1000
        inventory.save()

        response = self.client.post('/refund/', {
            'value': char1.char_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        char1.refresh_from_db()
        inventory.refresh_from_db()

        self.assertEqual(char1.level, 1)
        self.assertEqual(inventory.gems, 0)
        self.assertEqual(inventory.coins, formulas.char_level_to_coins(200))
        self.assertEqual(inventory.dust, formulas.char_level_to_dust(200))


class VIPExpLevelUpTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    # check that the level up from 29 -> 30 gives vip exp
    def test_level_up(self):
        self.u.userinfo.player_exp = 13440  # this is level 29
        self.u.userinfo.save()

        self.assertEqual(self.u.userinfo.vip_exp, 0)

        response = self.client.post('/dungeon/setprogress/stage/', {
            'is_win': True,
            'dungeon_type': constants.DungeonType.CAMPAIGN.value,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        token = response.data['token']
        response = self.client.post('/dungeon/setprogress/commit/', {
            'is_win': True,
            'dungeon_type': constants.DungeonType.CAMPAIGN.value,
            'token': token,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.userinfo.refresh_from_db()
        self.assertEqual(self.u.userinfo.vip_exp, 100)
