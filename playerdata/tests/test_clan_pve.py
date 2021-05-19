from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, ClanPVEResult


class ClanPVEResultAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

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

