from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import regal_rewards
from playerdata.models import User


class RegalRewardsAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        self.u.regalrewards.is_premium = True
        self.u.regalrewards.save()

    def test_get_regal_rewards(self):
        response = self.client.get('/regalrewards/get/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertEqual(len(response.data['rewards']), 25)

    def test_claim_reward(self):
        regal_rewards.complete_regal_rewards(1, self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_claim_reward_inactive_purchase(self):
        response = self.client.post('/regalrewards/claim/', {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_premium(self):
        regal_rewards.complete_regal_rewards(801, self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_not_premium(self):
        self.u.regalrewards.is_premium = False
        self.u.regalrewards.save()

        regal_rewards.complete_regal_rewards(801, self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_not_premium_then_premium(self):
        self.u.regalrewards.is_premium = False
        self.u.regalrewards.save()

        regal_rewards.complete_regal_rewards(801, self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

        self.u.regalrewards.is_premium = True
        self.u.regalrewards.save()

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
