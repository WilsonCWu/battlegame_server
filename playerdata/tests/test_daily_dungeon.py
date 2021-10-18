from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone

from playerdata import constants
from playerdata.models import User, DailyDungeonStatus, ServerStatus, BaseItem


class DailyDungeonStartAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_start(self):
        response = self.client.post('/dailydungeon/start/', {
            'is_golden': False,
            'characters': '{"11": 1}',
            'tier': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_no_ticket(self):
        self.u.inventory.daily_dungeon_ticket = 0
        self.u.inventory.save()

        response = self.client.post('/dailydungeon/start/', {
            'is_golden': False,
            'characters': '{"11": 1}',
            'tier': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_start_ingame(self):
        self.u.inventory.daily_dungeon_ticket += 1
        self.u.inventory.save()
        DailyDungeonStatus.objects.create(user=self.u, stage=1)
        
        response = self.client.post('/dailydungeon/start/', {
            'is_golden': False,
            'characters': '{"11": 1}',
            'tier': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])


class DailyDungeonStatusAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_missing_status(self):
        response = self.client.get('/dailydungeon/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dungeon'], None)

    def test_existing_status(self):
        DailyDungeonStatus.objects.create(user=self.u, stage=11)

        response = self.client.get('/dailydungeon/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dungeon']['stage'], 11)


class DailyDungeonResultAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        BaseItem.objects.create(name="Bow0", rarity=0, gear_slot='W', item_type=1001, cost=100, rollable=True)

    def test_win(self):
        dd_status = DailyDungeonStatus.objects.create(user=self.u, stage=11)
        response = self.client.post('/dailydungeon/result/', {
            'is_loss': False,
            'characters': '{"11": 1}',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dd_status.refresh_from_db()
        self.assertEqual(dd_status.stage, 12)

    def test_loss(self):
        dd_status = DailyDungeonStatus.objects.create(user=self.u, stage=11)
        response = self.client.post('/dailydungeon/result/', {
            'is_loss': True,
            'characters': '{"11": 1}',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dd_status.refresh_from_db()
        self.assertEqual(dd_status.stage, 0)

    def test_win_version_1_0_0(self):
        ServerStatus.objects.create(
            event_type='V',
            version_number='1.0.0',  # important thing is that it's > 0.5.0
            creation_time=timezone.now()
        )
        dd_status = DailyDungeonStatus.objects.create(user=self.u, stage=20)
        response = self.client.post('/dailydungeon/result/', {
            'is_loss': False,
            'characters': '{"11": 1}',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['rewards']), 3)  # num rewards for a depth of 20
        dd_status.refresh_from_db()
        self.assertEqual(dd_status.stage, 0)


class DailyDungeonForfeitAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_forfeit(self):
        dd_status = DailyDungeonStatus.objects.create(user=self.u, stage=11)
        response = self.client.get('/dailydungeon/forfeit/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        dd_status.refresh_from_db()
        self.assertEqual(dd_status.stage, 0)

    def test_invalid_forfeit(self):
        dd_status = DailyDungeonStatus.objects.create(user=self.u, stage=0)
        response = self.client.get('/dailydungeon/forfeit/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
        dd_status.refresh_from_db()
        self.assertEqual(dd_status.stage, 0)
