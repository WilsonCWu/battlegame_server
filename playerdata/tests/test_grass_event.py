from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import grass_event
from playerdata.models import User, GrassEvent


class GrassEventAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        self.grass_event = GrassEvent.objects.create(user=self.u)

    def test_get(self):
        resp = self.client.get('/event/grass/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(resp.data['grass_event']['cur_floor'], 0)
        self.assertEqual(resp.data['grass_event']['tickets_left'], 0)
        self.assertEqual(resp.data['grass_event']['grass_cuts_left'], 0)

    def test_start_run_no_ticket(self):
        response = self.client.post('/event/grass/startrun/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_start_run_with_ticket(self):
        event = GrassEvent.objects.get(user=self.u)
        event.tickets_left = 1
        event.save()

        response = self.client.post('/event/grass/startrun/', {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_finish_run(self):
        response = self.client.post('/event/grass/finishrun/', {
            'value': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_cut_grass(self):
        self.grass_event.grass_cuts_left = 1
        self.grass_event.save()

        # Checking that the grass floor map is initialized
        response = self.client.get('/event/grass/get/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        cut_index = 5
        response = self.client.post('/event/grass/cutgrass/', {
            'value': cut_index
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # Cut same place again, invalid tile
        response = self.client.post('/event/grass/cutgrass/', {
            'value': cut_index
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_buy_grass_token(self):
        self.u.inventory.gems = 500
        self.u.inventory.save()

        original_tokens_left = self.grass_event.grass_cuts_left

        response = self.client.post('/event/grass/buytoken/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.grass_event.refresh_from_db()
        self.assertEqual(self.grass_event.grass_cuts_left, original_tokens_left + 1)

    def test_go_to_next_grass_floor(self):
        # set up a hardcoded reward mapgi
        jackpot_tile = 5
        self.grass_event.floor_reward_map = {5: grass_event.GrassRewardType.JACKPOT.value}
        self.grass_event.grass_cuts_left = 1
        self.grass_event.save()

        # cut/reveal the jackpot tile
        response = self.client.post('/event/grass/cutgrass/', {
            'value': jackpot_tile
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # next floor
        response = self.client.post('/event/grass/nextfloor/', {
            'value': jackpot_tile
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # check that the floor is next one and other things are reset properly
        self.grass_event.refresh_from_db()
        self.assertEqual(self.grass_event.cur_floor, 1)
        self.assertEqual(self.grass_event.claimed_tiles, [])
        self.assertEqual(self.grass_event.ladder_index, -1)
