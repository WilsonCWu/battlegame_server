
from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, DungeonProgress, DungeonStage, UserMatchState
import playerdata.constants as consts


class DungeonProgressAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.match_state, _ = UserMatchState.objects.get_or_create(user=self.u)
        # Clear existing match states.
        self.match_state.campaign_state = None
        self.match_state.save()

        self.client.force_authenticate(user=self.u)

    def test_dungeon_progress(self):
        progress = DungeonProgress.objects.get(user=self.u).campaign_stage
        # Add in dungeon stages to ensure that rewards exist.
        DungeonStage.objects.create(
            stage=progress,
            dungeon_type=consts.DungeonType.CAMPAIGN.value,
            coins=1,
            gems=1,
            player_exp=1,
            mob_id=1,
        )
        
        response = self.client.post('/dungeon/setprogress/stage/', {
            'is_win': True,
            'dungeon_type': consts.DungeonType.CAMPAIGN.value,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertEqual(progress, DungeonProgress.objects.get(user=self.u).campaign_stage)

        token = response.data['token']
        response = self.client.post('/dungeon/setprogress/commit/', {
            'is_win': True,
            'dungeon_type': consts.DungeonType.CAMPAIGN.value,
            'token': token,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertEqual(progress + 1, DungeonProgress.objects.get(user=self.u).campaign_stage)
        
    def test_dungeon_progress_no_stage(self):
        # Cannot complete a dungeon without having staged results.
        response = self.client.post('/dungeon/setprogress/commit/', {
            'is_win': True,
            'dungeon_type': consts.DungeonType.CAMPAIGN.value,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
