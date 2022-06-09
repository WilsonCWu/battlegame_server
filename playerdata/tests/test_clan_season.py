from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User


class ClanSeasonRewardAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        self.u.clanseasonreward.is_claimed = False
        self.u.clanseasonreward.save()

    def test_claim_reward(self):
        response = self.client.post('/clanseasonreward/claim/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_double_claim(self):
        response = self.client.post('/clanseasonreward/claim/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/clanseasonreward/claim/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
