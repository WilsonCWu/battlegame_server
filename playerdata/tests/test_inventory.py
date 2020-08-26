from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, Character

class EquipItemAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=u)

    def test_equipping_item(self):
        # TODO: let's make this test proper (not just using seemingly magical
        # char and item IDs) once we have a change to make proper test
        # fixtures. Right now we're just using a JSON dump for the
        # current database, but we probably just want something with the base
        # character and items.
        response = self.client.post('/equipitem/', {
            'target_slot': 'W',
            'target_char_id': 11,
            'target_item_id': 11,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        equipped_char = Character.objects.get(char_id=11)
        self.assertEqual(equipped_char.weapon_id, 11)
