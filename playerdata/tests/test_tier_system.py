from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import tier_system, constants
from playerdata.models import User, EloRewardTracker


class EloRewardAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_claim_reward(self):
        tier_system.complete_any_elo_rewards(51, self.u.elorewardtracker)

        response = self.client.post('/eloreward/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_claim_reward_out_of_order(self):
        tier_system.complete_any_elo_rewards(151, self.u.elorewardtracker)

        response = self.client.post('/eloreward/claim/', {
            'value': 2
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_in_order(self):
        tier_system.complete_any_elo_rewards(151, self.u.elorewardtracker)

        response = self.client.post('/eloreward/claim/', {
            'value': 0
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/eloreward/claim/', {
            'value': 1
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/eloreward/claim/', {
            'value': 2
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])


class ChampRewardAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_claim_reward(self):
        tier_system.complete_any_champ_rewards(51, self.u.champbadgetracker)

        response = self.client.post('/champbadge/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_claim_reward_out_of_order(self):
        tier_system.complete_any_champ_rewards(151, self.u.champbadgetracker)

        response = self.client.post('/champbadge/claim/', {
            'value': 2
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_in_order(self):
        tier_system.complete_any_champ_rewards(149, self.u.champbadgetracker)

        response = self.client.post('/champbadge/claim/', {
            'value': 0
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/champbadge/claim/', {
            'value': 1
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/champbadge/claim/', {
            'value': 2
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])


class SeasonRewardAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        self.u.seasonreward.is_claimed = False
        self.u.seasonreward.save()

    def test_claim_reward(self):
        response = self.client.post('/seasonreward/claim/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        rewards = tier_system.get_season_reward(constants.Tiers.BRONZE_FIVE.value, self.u)
        self.assertEqual(response.data['rewards'][0]['reward_type'], rewards[0].reward_type)
        self.assertEqual(response.data['rewards'][0]['value'], rewards[0].value)

    def test_double_claim(self):
        response = self.client.post('/seasonreward/claim/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/seasonreward/claim/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
