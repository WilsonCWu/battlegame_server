import datetime
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, ClanPVEResult, ClanPVEStatus


class ClanPVEResultAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        # Give the user a new clan first.
        resp = self.client.post('/clan/new/', {'clan_name': 'foo', 'clan_description': 'hi'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

    def test_upload_result(self):
        resp = self.client.post('/clanpve/result/', {'boss_type': '1', 'score': 200})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        result = ClanPVEResult.objects.filter(user=self.u, boss='1').first()
        self.assertIsNotNone(result)
        self.assertEqual(result.best_score, 200)

        # Try uploading a separate run for a different boss type.
        resp = self.client.post('/clanpve/result/', {'boss_type': '2', 'score': 100})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        result_2 = ClanPVEResult.objects.filter(user=self.u, boss='2').first()
        self.assertIsNotNone(result_2)
        self.assertEqual(result_2.best_score, 100)
        self.assertEqual(result.best_score, 200)


class ClanPVEStartAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        # Give the user a new clan first.
        resp = self.client.post('/clan/new/', {'clan_name': 'foo', 'clan_description': 'hi'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        # Give the user a ClanPVEStatus, which would be granted by a cron job.
        self.pve_status = ClanPVEStatus.objects.create(user=self.u, day='Fri',
                                                       tickets={'1': 3, '2': 3, '3': 3})

    def test_start_pve(self):
        # Make this a Friday.
        with mock.patch('playerdata.clan_pve.get_date') as mock_date:
            mock_date.return_value = 4
            resp = self.client.post('/clanpve/start/', {'boss_type': '1'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.pve_status.refresh_from_db()
        self.assertEqual(self.pve_status.tickets['1'], 2)
