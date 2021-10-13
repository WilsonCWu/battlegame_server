from freezegun import freeze_time
from rest_framework.test import APITestCase

from playerdata.models import User


class EventRewardsTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

    @freeze_time("2022-01-01")
    def test_event_get(self):
        self.u.eventrewards.last_claimed_reward = -1
        response = self.client.get('/eventreward/get/')
        self.assertTrue(response.data['highest_unlocked'] > 5)

    @freeze_time("2020-01-01")
    def test_early_event_get(self):
        self.u.eventrewards.last_claimed_reward = -1
        response = self.client.get('/eventreward/get/')
        self.assertTrue(response.data['highest_unlocked'] < 1)

    @freeze_time("2021-10-15")  # Day two
    def test_ok_mid_event_get(self):
        self.u.eventrewards.last_claimed_reward = -1
        response = self.client.get('/eventreward/get/')
        self.assertTrue(response.data['highest_unlocked'] == 1)

    @freeze_time("2021-10-16")  # Day three
    def test_bad_mid_event_get(self):
        self.u.eventrewards.last_claimed_reward = -1
        response = self.client.get('/eventreward/get/')
        self.assertFalse(response.data['highest_unlocked'] == 3)

    # We don't test an OK claim because the characters aren't in the lightweight db yet.
    @freeze_time("2022-01-01")
    def test_bad_event_claim(self):
        self.u.eventrewards.last_claimed_reward = -1
        response = self.client.post('/eventreward/claim/', {
            'value': 1
        })
        self.assertFalse(response.data['status'])  # Fails because claim is out of order.
