from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User


class StoryModeAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_get_storymode(self):
        resp = self.client.get('/storymode/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_result_storymode(self):
        resp = self.client.post('/storymode/start/', {
            'value': 7,
        })

        resp = self.client.post('/storymode/result/', {
            'is_loss': True,
            'characters': '{"11": 0, "5": 0}'
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
