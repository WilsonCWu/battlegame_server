from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import grass_event, constants
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
        self.grass_event.tickets_left = 1
        self.grass_event.save()

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

    def test_cut_grass_gems(self):
        self.grass_event.grass_cuts_left = 0
        self.grass_event.save()

        self.u.inventory.gems = 500
        self.u.inventory.save()

        cut_index = 5
        response = self.client.post('/event/grass/cutgrass/', {
            'value': cut_index
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.grass_event.refresh_from_db()
        reward_type = response.data['reward_type']
        self.assertEqual(self.grass_event.rewards_left[reward_type], constants.GRASS_REWARDS_PER_TIER[reward_type] - 1)

    def test_go_to_next_grass_floor(self):
        ladder_tile = 5
        self.grass_event.rewards_left = [0, 0, 0, 0, 1]  # hardcode only the ladder is left
        self.grass_event.grass_cuts_left = 1
        self.grass_event.save()

        # cut/reveal the jackpot tile
        response = self.client.post('/event/grass/cutgrass/', {
            'value': ladder_tile
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # next floor
        response = self.client.post('/event/grass/nextfloor/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # check that the floor is next one and other things are reset properly
        self.grass_event.refresh_from_db()
        self.assertEqual(self.grass_event.cur_floor, 1)
        self.assertEqual(self.grass_event.claimed_tiles, [])
        self.assertEqual(self.grass_event.ladder_index, -1)
