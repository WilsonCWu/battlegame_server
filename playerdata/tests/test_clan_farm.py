import datetime
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, ClanFarming
from playerdata.clan_farm import last_week


class ClanFarmingTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        # Give the user a new clan first.
        resp = self.client.post('/clan/new/', {'clan_name': 'foo', 'clan_description': 'hi'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

    def test_status(self):
        farm_status = ClanFarming.objects.create(
            clan=self.u.userinfo.clanmember.clan2,
            daily_farms=[{self.u.id: True}, {}, {}, {}, {}, {}, {}],
        ) 
        
        resp = self.client.get('/clanfarm/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        
        # Since the farming status was instantiated with a super old date, we
        # should get some unclaimed rewards, but none for this week.
        self.assertEqual(resp.data['total_farms'], 0)
        self.assertEqual(resp.data['unclaimed_farm_count'], 1)

        # If we re-call this though, the reward would already be applied.
        resp = self.client.get('/clanfarm/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(resp.data['unclaimed_farm_count'], 0)

    def test_anti_clan_hopping(self):
        farm_status = ClanFarming.objects.create(
            clan=self.u.userinfo.clanmember.clan2,
            daily_farms=[{self.u.id: True}, {}, {}, {}, {}, {}, {}],
        ) 

        # Set last collected rewards for the previous week.
        self.u.userinfo.clanmember.last_farm_reward = last_week()
        self.u.userinfo.clanmember.save()
        
        resp = self.client.get('/clanfarm/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(resp.data['unclaimed_farm_count'], 0)
        
    def test_farm(self):
        resp = self.client.post('/clanfarm/farm/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        # Cannot pray again.
        resp = self.client.post('/clanfarm/farm/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

        resp = self.client.get('/clanfarm/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(resp.data['total_farms'], 1)
