from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import tier_system
from playerdata.models import User, EloRewardTracker


class EloRewardAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        EloRewardTracker.objects.create(user=self.u)

    def test_claim_reward(self):
        tier_system.complete_any_elo_rewards(51, self.u.elorewardtracker)

        response = self.client.post('/eloreward/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
