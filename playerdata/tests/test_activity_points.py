from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import activity_points
from playerdata.models import User


class ActivityPointsAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        self.u.regalrewards.is_premium = True
        self.u.regalrewards.save()

    def test_claim_reward_daily(self):
        activity_points.ActivityPointsUpdater.try_complete_daily_activity_points(self.u.activitypoints, 20)

        response = self.client.post('/activitypoints/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/activitypoints/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_weekly(self):
        activity_points.ActivityPointsUpdater.try_complete_weekly_activity_points(self.u.activitypoints, 20)

        response = self.client.post('/activitypoints/claim/', {
            'value': 1
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/activitypoints/claim/', {
            'value': 1
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
