from datetime import datetime, timezone

from freezegun import freeze_time
from rest_framework.test import APITestCase

from playerdata import constants
from playerdata.models import User, EventTimeTracker


class EventRewardsTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

        start_time = datetime(2021, 12, 20, tzinfo=timezone.utc)
        end_time = datetime(2021, 12, 30, tzinfo=timezone.utc)

        self.event_time_tracker = EventTimeTracker.objects.create(name=constants.EventType.CHRISTMAS_2021.value, start_time=start_time, end_time=end_time)

    @freeze_time("2021-12-21")
    def test_event_get(self):
        response = self.client.get('/eventreward/get/')
        self.assertEqual(response.data['last_claimed'], -1)
        self.assertEqual(len(response.data['rewards']), 8)

    @freeze_time("2021-12-19")
    def test_early_event_get(self):
        response = self.client.get('/eventreward/get/')
        self.assertListEqual(response.data['rewards'], [])

    @freeze_time("2021-12-21")
    def test_event_claim(self):
        response = self.client.post('/eventreward/claim/', {})
        self.assertTrue(response.data['status'])

        self.assertEqual(self.u.eventrewards.last_claimed_reward, 0)

        response = self.client.post('/eventreward/claim/', {})
        self.assertFalse(response.data['status'])  # Double claim on same day
