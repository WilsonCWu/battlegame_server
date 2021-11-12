from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, GrassEvent


class GrassEventAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        GrassEvent.objects.create(user=self.u)

    def test_get(self):
        resp = self.client.get('/event/grass/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(resp.data['grass_event']['cur_floor'], 0)
        self.assertEqual(resp.data['grass_event']['tickets_left'], 0)
        self.assertEqual(resp.data['grass_event']['grass_cuts_left'], 0)

    def test_start_run_no_ticket(self):
        response = self.client.post('/event/grass/startrun/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_start_run_with_ticket(self):
        event = GrassEvent.objects.get(user=self.u)
        event.tickets_left = 1
        event.save()

        response = self.client.post('/event/grass/startrun/', {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_finish_run(self):
        response = self.client.post('/event/grass/finishrun/', {
            'value': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
