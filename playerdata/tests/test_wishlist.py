from rest_framework.test import APITestCase
from rest_framework import status

from playerdata import relic_shop
from playerdata.models import User, Character, Wishlist


class RelicShopAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        # Init wishlist


    def test_get_shop(self):
        resp = self.client.get('/wishlist/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(len(resp.data['legendaries']), 1)
        self.assertEqual(len(resp.data['epics']), 2)
        self.assertEqual(len(resp.data['rares']), 2)

    def test_set_slot(self):
        resp = self.client.post('/wishlist/set/', {
            'slot_id': 0,
            'char_id': 9  # Rozan
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        wishlist = Wishlist.objects.filter(user=self.u).first()
        self.assertEqual(wishlist.legendaries[0], 9)

    def test_set_dup(self):
        pass

    def test_set_wrong_rarity(self):
        pass
