from django_redis import get_redis_connection
from rest_framework.test import APITestCase
from rest_framework import status

from playerdata import pvp_queue
from playerdata.models import User, Character, ServerStatus


class PVPQueueAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        self.opponent_queue_key = pvp_queue.get_opponent_queue_key(self.u.id)

        ServerStatus.objects.create(version_number="0.5.0", event_type='V')

    def test_get_opponent(self):
        resp = self.client.post('/opponent/')

        user_id = resp.data['user_id']
        self.assertIsNotNone(resp.data)

        resp = self.client.post('/opponent/')
        self.assertEqual(resp.data['user_id'], user_id)

    def test_skip(self):
        r = get_redis_connection("default")
        r.lpush(self.opponent_queue_key, 3, 22)

        resp = self.client.post('/opponent/')
        self.assertEqual(resp.data['user_id'], 22)

        resp = self.client.post('/skip/')

        resp = self.client.post('/opponent/')
        self.assertEqual(resp.data['user_id'], 3)
