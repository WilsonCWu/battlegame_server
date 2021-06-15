from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import wishlist
from playerdata.models import User, Wishlist


class RelicShopAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        # Init wishlist
        wishlist.init_wishlist(self.u)

    def test_get_shop(self):
        resp = self.client.get('/wishlist/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['legendaries']), wishlist.NUM_SLOTS_PER_RARITY[4])
        self.assertEqual(len(resp.data['epics']), wishlist.NUM_SLOTS_PER_RARITY[3])
        self.assertEqual(len(resp.data['rares']), wishlist.NUM_SLOTS_PER_RARITY[2])

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
        resp = self.client.post('/wishlist/set/', {
            'slot_id': 0,
            'char_id': 10  # Demetra
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.post('/wishlist/set/', {
            'slot_id': 1,
            'char_id': 10  # Demetra
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

    def test_set_wrong_slot(self):
        resp = self.client.post('/wishlist/set/', {
            'slot_id': 1,
            'char_id': 9  # Rozan
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])
