import datetime
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, BaseCharacter, Character, ClanPVEResult, ClanPVEStatus, ClanPVEEvent


class ClanPVEResultAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        # Give the user a new clan first.
        resp = self.client.post('/clan/new/', {'clan_name': 'foo', 'clan_description': 'hi'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

    def test_upload_result(self):
        resp = self.client.post('/clanpve/result/', {'boss_type': '1', 'score': 200})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        result = ClanPVEResult.objects.filter(user=self.u, boss='1').first()
        self.assertIsNotNone(result)
        self.assertEqual(result.best_score, 200)

        # Try uploading a separate run for a different boss type.
        resp = self.client.post('/clanpve/result/', {'boss_type': '2', 'score': 100})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        result_2 = ClanPVEResult.objects.filter(user=self.u, boss='2').first()
        self.assertIsNotNone(result_2)
        self.assertEqual(result_2.best_score, 100)
        self.assertEqual(result.best_score, 200)


class ClanPVEEventTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        # Give the user a new clan first.
        resp = self.client.post('/clan/new/', {'clan_name': 'foo', 'clan_description': 'hi'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        # Put someone else in the clan as well.
        self.u2 = User.objects.get(username='testWilson')
        self.u2.userinfo.clanmember.clan2 = self.u.userinfo.clanmember.clan2
        self.u2.userinfo.clanmember.save()

    def test_start_event(self):
        resp = self.client.post('/clanpve/startevent/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        event = ClanPVEEvent.objects.filter(clan=self.u.userinfo.clanmember.clan2,
                                            date=datetime.date.today() + datetime.timedelta(days=1)).first()
        self.assertIsNotNone(event)
        pve_status = ClanPVEStatus.objects.filter(user=self.u, event=event).first()
        self.assertIsNotNone(pve_status)

        # Cannot start another event.
        resp = self.client.post('/clanpve/startevent/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

        # Try to start a boss, should fail since not in time range.
        event.date = datetime.date(2010, 1, 1)
        event.save()
        resp = self.client.post('/clanpve/start/', {'boss_type': '1', 'borrowed_character': 7})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

        # First day event.
        event.date = datetime.datetime.today()
        event.save()
        resp = self.client.post('/clanpve/start/', {'boss_type': '1', 'borrowed_character': 7})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        pve_status.refresh_from_db()
        self.assertEqual(pve_status.tickets_1['1'], 0)

        # Check status.
        resp = self.client.get('/clanpve/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertTrue(resp.data['has_event'])
        self.assertDictEqual(resp.data['tickets'], {'1': 0, '2': 1, '3': 1})
        self.assertEqual(resp.data['current_boss'], '1')

        # Validate that character has been lent.
        pve_status_2 = ClanPVEStatus.objects.get(user=self.u2, event=event)
        self.assertIn(str({'char_id': 7, 'uses_remaining': 8}),
                      [str(c) for c in pve_status_2.character_lending['characters']])

        # Finish a run.
        resp = self.client.post('/clanpve/result/', {'boss_type': '1', 'score': 100})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        pve_status.refresh_from_db()
        self.assertEqual(pve_status.current_boss, -1)
        


class ClanLendingTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        # Give the user a new clan first.
        resp = self.client.post('/clan/new/', {'clan_name': 'foo', 'clan_description': 'hi'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        # Start an event.
        resp = self.client.post('/clanpve/startevent/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.event = ClanPVEEvent.objects.filter(clan=self.u.userinfo.clanmember.clan2,
                                                 date=datetime.date.today() + datetime.timedelta(days=1)).first()
        self.assertIsNotNone(self.event)

    def test_lending(self):
        resp = self.client.get('/clanpve/lending/list/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        # Map the lent characters to a list of IDs.
        lent_characters = [r['character']['char_id'] for r in resp.data['lent_characters']]
        self.assertListEqual([1, 2, 70], lent_characters)

        # Instead lend characters 1, 71, 72.
        resp = self.client.post('/clanpve/lending/set/', {'char_1': 1, 'char_2': 71, 'char_3': 72})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.get('/clanpve/lending/list/')
        lent_characters = [r['character']['char_id'] for r in resp.data['lent_characters']]
        self.assertListEqual([1, 71, 72], lent_characters)
