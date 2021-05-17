from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import constants, level_booster
from playerdata.models import User, Character


class LevelBoosterAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        self.new_char = Character.objects.create(user=self.u, char_type_id=6, level=240, prestige=5)

        # Need 1 maxed out chars to unlock this feature
        self.char1 = Character.objects.create(user=self.u, char_type_id=7, level=240, prestige=5)

    def unlock_slot(self):
        self.u.inventory.gems = 400
        self.u.inventory.save()

        response = self.client.post('/levelbooster/unlock/', {
            'value': 1  # resource value
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        return response

    def fill_slot_with_charid(self, char_id):
        self.unlock_slot()

        response = self.client.post('/levelbooster/fill/', {
            'slot_id': 0,  # resource value
            'char_id': char_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_get(self):
        response = self.client.get('/levelbooster/get/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertTrue(response.data['level_booster']['is_available'])
        self.assertEqual(len(response.data['level_booster']['slots']), constants.LEVEL_BOOSTER_SLOTS)

    def test_unlock_slot(self):
        response = self.unlock_slot()
        self.assertEqual(response.data['unlocked_slots'], 1)

    def test_unlock_not_enough_gems(self):
        self.u.inventory.gems = 0
        self.u.inventory.save()

        response = self.client.post('/levelbooster/unlock/', {
            'value': 1  # resource value
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_fill_slot(self):
        self.fill_slot_with_charid(self.new_char.char_id)
        self.assertEqual(self.u.levelbooster.slots[0], self.new_char.char_id)


    def test_fill_slot_with_already_used_char(self):
        self.fill_slot_with_charid(self.new_char.char_id)

        response = self.client.post('/levelbooster/fill/', {
            'slot_id': 0,  # resource value
            'char_id': self.new_char.char_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_fill_slot_in_cooldown(self):
        self.fill_slot_with_charid(self.new_char.char_id)

        response = self.client.post('/levelbooster/remove/', {
            'value': 0,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIsNotNone(self.u.levelbooster.cooldown_slots[0])

        response = self.client.post('/levelbooster/fill/', {
            'slot_id': 0,  # resource value
            'char_id': self.new_char.char_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        #  Fails because of cooldown
        self.assertFalse(response.data['status'])

    def test_remove_slot(self):
        self.fill_slot_with_charid(self.new_char.char_id)
        self.assertIsNone(self.u.levelbooster.cooldown_slots[0])

        response = self.client.post('/levelbooster/remove/', {
            'value': 0,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIsNotNone(self.u.levelbooster.cooldown_slots[0])

    def test_remove_slot_already_empty(self):
        response = self.client.post('/levelbooster/remove/', {
            'value': 0,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_skip_cooldown(self):
        self.fill_slot_with_charid(self.new_char.char_id)

        self.client.post('/levelbooster/remove/', {
            'value': 0,
        })

        response = self.client.post('/levelbooster/fill/', {
            'slot_id': 0,  # resource value
            'char_id': self.new_char.char_id,
        })

        self.assertFalse(response.data['status'])

        self.u.inventory.gems = 400
        self.u.inventory.save()

        response = self.client.post('/levelbooster/skip/', {
            'value': 0,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/levelbooster/fill/', {
            'slot_id': 0,  # resource value
            'char_id': self.new_char.char_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])


class BoostLevelUpAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        # Need 1 maxed out char to unlock this feature
        self.char1 = Character.objects.create(user=self.u, char_type_id=7, level=240, prestige=5, is_boosted=True)

        # Extra chars to be boosted as well
        self.char2 = Character.objects.create(user=self.u, char_type_id=6, level=240, prestige=5, is_boosted=True)
        self.char3 = Character.objects.create(user=self.u, char_type_id=6, level=240, prestige=5, is_boosted=True)

    def test_levelup(self):
        self.u.inventory.coins = 10000000
        self.u.inventory.dust = 10000000
        self.u.inventory.save()

        response = self.client.post('/levelbooster/levelup/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.get('/inventoryinfo/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for char in response.data['characters']:
            if char['char_id'] in (self.char1.char_id, self.char2.char_id, self.char3.char_id):
                self.assertEqual(char['level'], 241)

    def test_levelup_past_cap(self):
        self.u.inventory.coins = 10000000
        self.u.inventory.dust = 10000000
        self.u.inventory.save()

        self.u.levelbooster.booster_level = level_booster.get_level_cap(self.u)
        response = self.client.post('/levelbooster/levelup/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_levelup_not_enough_coins(self):
        response = self.client.post('/levelbooster/levelup/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
