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
        self.u.afkreward.last_collected_time = d1
        self.u.afkreward.save()

        response = self.client.get('/afkrewards/get')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.afkreward.refresh_from_db()
        self.assertEqual(self.u.afkreward.reward_ticks, 0)
        self.assertEqual(self.u.afkreward.runes_left, 0)

    def test_collect_afk(self):
        d1 = datetime.today().replace(tzinfo=timezone.utc) - timedelta(days=1)

        self.u.afkreward.runes_left = 3000
        self.u.afkreward.last_eval_time = d1
        self.u.afkreward.last_collected_time = d1
        self.u.afkreward.save()

        orginal_coins = self.u.inventory.coins

        response = self.client.get('/afkrewards/get')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/afkrewards/collect')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.afkreward.refresh_from_db()
        self.u.inventory.refresh_from_db()
        self.assertTrue(self.u.inventory.coins > orginal_coins)


class FastRewardsAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_collect_dust(self):
        original_dust = self.u.inventory.dust
        self.u.inventory.dust_fast_reward_hours = 12
        self.u.inventory.save()

        response = self.client.post('/fastrewards/collect/', {
            'dust_hours': 12,
            'coin_hours': 0
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.inventory.refresh_from_db()
        self.assertGreater(self.u.inventory.dust, original_dust)

    def test_collect_not_enough(self):
        response = self.client.post('/fastrewards/collect/', {
            'dust_hours': 12,
            'coin_hours': 12
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_collect_dust_and_coins(self):
        original_dust = self.u.inventory.dust
        original_coins = self.u.inventory.coins
        self.u.inventory.dust_fast_reward_hours = 12
        self.u.inventory.coins_fast_reward_hours = 12
        self.u.inventory.save()

        response = self.client.post('/fastrewards/collect/', {
            'dust_hours': 8,
            'coin_hours': 8
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.u.inventory.refresh_from_db()
        self.assertGreater(self.u.inventory.dust, original_dust)
        self.assertGreater(self.u.inventory.coins, original_coins)
