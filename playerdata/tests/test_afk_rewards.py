from rest_framework import status
from rest_framework.test import APITestCase

from datetime import datetime, timezone, timedelta

from playerdata.models import User, ServerStatus


class AFKRewardsAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        ServerStatus.objects.create(
            event_type='V',
            version_number='1.0.0',
        )

    def test_get_afk_rewards(self):
        d1 = datetime.today().replace(tzinfo=timezone.utc) - timedelta(days=1)
        d2 = d1 + timedelta(hours=1)
        d3 = d2 + timedelta(hours=1)
        d4 = d3 + timedelta(hours=1)

        self.u.afkreward.runes_added = [3600, 3600, 3600, 3600]
        self.u.afkreward.time_added = [d1, d2, d3, d4]
        self.u.afkreward.save()

        response = self.client.get('/afkrewards/get')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.afkreward.refresh_from_db()
        self.assertEqual(len(self.u.afkreward.runes_added), 1)
