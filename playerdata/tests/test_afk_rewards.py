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

        self.u.afkreward.runes_left = 3000
        self.u.afkreward.last_eval_time = d1
        self.u.afkreward.save()

        response = self.client.get('/afkrewards/get')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.afkreward.refresh_from_db()
        self.assertEqual(self.u.afkreward.runes_to_be_converted, 0)
        self.assertEqual(self.u.afkreward.runes_left, 0)
