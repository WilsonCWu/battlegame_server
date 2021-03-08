from rest_framework import status
from rest_framework.test import APITestCase
import playerdata.constants

from playerdata.models import User, DailyDungeonStatus


class DailyDungeonStartAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_start(self):
        self.u.inventory.daily_dungeon_ticket += 1
        self.u.inventory.save()

        response = self.client.post('/dailydungeon/start/', {
            'is_golden': False,
            'characters': '{"11": 1}',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_start_no_ticket(self):
        response = self.client.post('/dailydungeon/start/', {
            'is_golden': False,
            'characters': '{"11": 1}',
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
        self.assertEqual(response.data['status'], None)

    def test_inactive_status(self):
        DailyDungeonStatus.objects.create(user=self.u, stage=0)

        response = self.client.get('/dailydungeon/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], None)

    def test_existing_status(self):
        DailyDungeonStatus.objects.create(user=self.u, stage=11)

        response = self.client.get('/dailydungeon/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status']['stage'], 11)


class DailyDungeonResultAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

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
