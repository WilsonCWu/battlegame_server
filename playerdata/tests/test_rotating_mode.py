from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User


class RotatingModeAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    # TODO
    def test_get(self):
        pass

    # TODO
    def test_result(self):
        pass

    # TODO
    def test_claim(self):
        pass


class ConquestEventTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_claim(self):
        start_gems = self.u.inventory.gems

        resp = self.client.post('/event/conquest/claim/', {})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        self.u.inventory.refresh_from_db()
        self.assertTrue(start_gems + 2700 * 3, self.u.inventory.gems)

        resp = self.client.post('/event/conquest/claim/', {})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])
