from rest_framework.test import APITestCase
from rest_framework import status

from playerdata import constants, resource_shop
from playerdata.models import User, BaseResourceShopItem


class ResourceShopAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        BaseResourceShopItem.objects.create(id=1, reward_type=constants.RewardType.DUST.value, reward_value=250,
                                            cost_type=constants.RewardType.GEMS.value, cost_value=300)

    def test_get_shop(self):
        resp = self.client.get('/resourceshop/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(resp.data['shop_items'][0]['cost_value'], 300)

    def test_purchase(self):
        self.u.inventory.gems = 100000
        self.u.inventory.save()

        resp = self.client.post('/resourceshop/buy/', {
            'value': 1
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

    def test_purchase_duplicate(self):
        self.u.inventory.gems = 200000
        self.u.inventory.save()

        resp = self.client.post('/resourceshop/buy/', {
            'value': 1
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/resourceshop/buy/', {
            'value': 1
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

    def test_reset_shop(self):
        self.u.inventory.gems = 200000
        self.u.inventory.save()

        resp = self.client.post('/resourceshop/buy/', {
            'value': 1
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/resourceshop/refresh/', {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/resourceshop/buy/', {
            'value': 1
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

    def test_triple_reset(self):
        self.u.inventory.gems = resource_shop.refresh_resource_shop_cost() * 2
        self.u.inventory.save()

        resp = self.client.post('/resourceshop/refresh/', {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/resourceshop/refresh/', {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/resourceshop/refresh/', {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])
