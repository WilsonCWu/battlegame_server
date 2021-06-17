from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import chapter_rewards_pack
from playerdata.models import User


class ChapterRewardPackAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        self.u.chapterrewardpack.is_active = True
        self.u.chapterrewardpack.save()

    def test_claim_reward(self):
        chapter_rewards_pack.complete_chapter_rewards(1, self.u.chapterrewardpack)

        response = self.client.post('/chapterrewardspack/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_claim_reward_inactive_purchase(self):
        response = self.client.post('/chapterrewardspack/claim/', {
            'value': 0
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_out_of_order(self):
        chapter_rewards_pack.complete_chapter_rewards(5, self.u.chapterrewardpack)

        response = self.client.post('/chapterrewardspack/claim/', {
            'value': 2
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_claim_reward_in_order(self):
        chapter_rewards_pack.complete_chapter_rewards(3, self.u.chapterrewardpack)

        response = self.client.post('/chapterrewardspack/claim/', {
            'value': 0
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/chapterrewardspack/claim/', {
            'value': 1
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/chapterrewardspack/claim/', {
            'value': 2
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
