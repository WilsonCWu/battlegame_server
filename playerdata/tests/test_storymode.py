from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import story_mode
from playerdata.models import User


class StoryModeAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        story_mode.unlock_next_character_pool(self.u)

    def test_get_storymode(self):
        char_id = story_mode.CHARACTER_POOLS[0][1]

        resp = self.client.post('/storymode/start/', {
            'value': char_id,
        })

        resp = self.client.get('/storymode/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['story_id'], char_id)
        self.assertEqual(resp.data['current_lvl'], 0)

    def test_result_storymode(self):
        char_id = story_mode.CHARACTER_POOLS[0][1]

        resp = self.client.post('/storymode/start/', {
            'value': char_id,
        })

        resp = self.client.post('/storymode/result/', {
            'is_loss': False,
            'characters': '{"4": 100}'
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(self.u.storymode.current_lvl, 1)

        resp = self.client.post('/storymode/result/', {
            'is_loss': True,
            'characters': '{"4": 0}'
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(self.u.storymode.current_lvl, 0)
        self.assertEqual(self.u.storymode.num_runs, 1)

    def test_result_finish_story(self):
        char_id = story_mode.CHARACTER_POOLS[0][1]

        resp = self.client.post('/storymode/start/', {
            'value': char_id,
        })

        self.u.storymode.current_lvl = 24
        self.u.storymode.save()

        resp = self.client.post('/storymode/result/', {
            'is_loss': False,
            'characters': '{"4": 10}'
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        self.assertEqual(self.u.storymode.current_lvl, 0)
        self.assertEqual(self.u.storymode.story_id, -1)
        self.assertEqual(self.u.storymode.num_runs, 0)
