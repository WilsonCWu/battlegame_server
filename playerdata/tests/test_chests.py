from datetime import datetime, timezone, timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import constants
from playerdata.models import User, Chest, Inventory, BaseItem


class ChestAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        # make some chests
        self.chest1 = Chest.objects.create(user=self.u, rarity=1)
        self.chest2 = Chest.objects.create(user=self.u, rarity=2)
        self.chest3 = Chest.objects.create(user=self.u, rarity=3)
        self.chest4 = Chest.objects.create(user=self.u, rarity=4)

        # TODOMAYBE: if we ever update our fixtures then get rid of this
        BaseItem.objects.create(name="Bow0", rarity=0, gear_slot='W', item_type=constants.COIN_SHOP_ITEMS[0], cost=100, rollable=True)
        BaseItem.objects.create(name="Bow1", rarity=1, gear_slot='W', item_type=constants.COIN_SHOP_ITEMS[1], cost=100, rollable=True)
        BaseItem.objects.create(name="Bow2", rarity=2, gear_slot='W', item_type=constants.COIN_SHOP_ITEMS[2], cost=100, rollable=True)
        BaseItem.objects.create(name="Bow3", rarity=3, gear_slot='W', item_type=constants.COIN_SHOP_ITEMS[3], cost=100, rollable=True)
        BaseItem.objects.create(name="Bow4", rarity=4, gear_slot='W', item_type=constants.COIN_SHOP_ITEMS[4], cost=100, rollable=True)

    def test_unlock_chests(self):
        self.assertIsNone(self.chest1.locked_until)

        response = self.client.post('/chest/unlock/', {
            'value': self.chest1.id,
        })

        self.chest1.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIsNotNone(self.chest1.locked_until)

    def test_collect_chests(self):
        self.chest2.locked_until = datetime.now(timezone.utc) - timedelta(hours=25)
        self.chest2.save()

        response = self.client.post('/chest/collect/', {
            'chest_id': self.chest2.id,
            'is_skip': False,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_collect_chests_skip(self):
        response = self.client.post('/chest/unlock/', {
            'value': self.chest3.id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # test skip with not enough gems
        response = self.client.post('/chest/collect/', {
            'chest_id': self.chest3.id,
            'is_skip': True,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

        # now with enough gems $$$
        inventory = Inventory.objects.get(user=self.u)
        inventory.gems = 10000
        inventory.save()
        self.u.refresh_from_db()

        response = self.client.post('/chest/collect/', {
            'chest_id': self.chest3.id,
            'is_skip': True,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
