from rest_framework.test import APITestCase
from rest_framework import status

from playerdata import relic_shop
from playerdata.models import User, Character


class RelicShopAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_get_shop(self):
        resp = self.client.get('/relicshop/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(len(resp.data['relics']), 6)  # number of relics returned
        self.assertEqual(len(resp.data['purchased_relics']), 0)

    def test_purchase(self):
        self.u.inventory.relic_stones = relic_shop.EPIC_COST
        self.u.inventory.save()

        relics_for_sale = relic_shop.get_relics(1)

        resp = self.client.post('/relicshop/buy/', {
            'value': relics_for_sale[0]
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        char = Character.objects.filter(user=self.u, char_type_id=relics_for_sale[0]).first()
        self.assertEqual(char.copies, 2)

    def test_purchase_duplicate(self):
        self.u.inventory.relic_stones = relic_shop.EPIC_COST
        self.u.inventory.save()

        relics_for_sale = relic_shop.get_relics(1)

        resp = self.client.post('/relicshop/buy/', {
            'value': relics_for_sale[0]
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/relicshop/buy/', {
            'value': relics_for_sale[0]
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

    def test_purchase_not_for_sale_char(self):
        self.u.inventory.relic_stones = 120
        self.u.inventory.save()

        resp = self.client.post('/relicshop/buy/', {
            'value': 14  # Skeleton
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])
