from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, Chest

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

    def test_get_chests(self):
        response = self.client.get('/chest/get/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['chests']) == 4)

    def test_unlock_chests(self):
        self.assertIsNone(self.chest1.locked_until)

        response = self.client.post('/chest/unlock/', {
            'value': self.chest1.id,
        })

        self.chest1.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIsNotNone(self.chest1.locked_until)

    # def test_collect_chests(self):
    #     response = self.client.post('/chest/collect/', {
    #         'chest_id': self.chest2.id,
    #         'is_skip': False,
    #     })
    #
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertTrue(response.data['status'])
    #
    # def test_collect_chests_skip(self):
    #     response = self.client.post('/chest/collect/', {
    #         'chest_id': self.chest3.id,
    #         'is_skip': True,
    #     })
    #
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertTrue(response.data['status'])
