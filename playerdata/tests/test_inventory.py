from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, BaseCharacter, Character, BaseItem, Item

class EquipItemAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_equipping_item(self):
        base_bow = BaseItem.objects.get(name="Bow")
        base_archer = BaseCharacter.objects.get(name="Archer")

        owned_bow = Item.objects.create(
            user = self.u,
            item_type = base_bow,
            exp = 0,
        )
        owned_archer = Character.objects.create(
            user = self.u,
            char_type = base_archer,
        )

        response = self.client.post('/equipitem/', {
            'target_slot': 'W',
            'target_char_id': owned_archer.char_id,
            'target_item_id': owned_bow.item_id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owned_archer.refresh_from_db()
        self.assertEqual(owned_archer.weapon, owned_bow)

    def test_bad(self):
        User.objects.get(username='fdslakfjlkdsa')
