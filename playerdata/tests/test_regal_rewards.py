from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import regal_rewards, chests
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
        self.u.regalrewards.points = 1
        self.u.regalrewards.save()

        chests.complete_regal_rewards(self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_claim_reward_inactive_purchase(self):
        response = self.client.post('/regalrewards/claim/', {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_premium(self):
        self.u.regalrewards.points = 801
        self.u.regalrewards.save()

        chests.complete_regal_rewards(self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.assertEqual(self.u.inventory.rare_shards, 240)
        self.assertEqual(self.u.inventory.epic_shards, 80)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.assertEqual(self.u.inventory.rare_shards, 280)
        self.assertEqual(self.u.inventory.epic_shards, 95)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_not_premium(self):
        self.u.regalrewards.is_premium = False
        self.u.regalrewards.points = 801
        self.u.regalrewards.save()

        chests.complete_regal_rewards(self.u.regalrewards)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.assertEqual(self.u.inventory.rare_shards, 240)
        self.assertEqual(self.u.inventory.epic_shards, 0)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.assertEqual(self.u.inventory.rare_shards, 280)
        self.assertEqual(self.u.inventory.epic_shards, 0)

        response = self.client.post('/regalrewards/claim/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_not_premium_then_premium(self):
        self.u.regalrewards.is_premium = False
        self.u.regalrewards.points = 801
        self.u.regalrewards.save()

        chests.complete_regal_rewards(self.u.regalrewards)

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
