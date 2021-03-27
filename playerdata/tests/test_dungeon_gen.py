import json

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from playerdata import constants

from playerdata.models import User, ServerStatus, DungeonBoss, DungeonStage


class DungeonStageAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)
        
        # can only use chars from 0-11 in test fixtures
        test_comp_str = u'[{"char_id": 0, "position": 6}, {"char_id": 1, "position": 10}, {"char_id": 8, "position": 15}, {"char_id": 10, "position": 16}, {"char_id": 11, "position": 22}]'

        ServerStatus.objects.create(
            event_type='V',
            version_number='1.0.0',  # important thing is that it's > 0.3.0 for new dungeon gen
            creation_time=timezone.now(),
        )
        DungeonBoss.objects.create(stage=20, team_comp=json.loads(test_comp_str))
        DungeonStage.objects.create(stage=1, dungeon_type=0, player_exp=0, gems=0, coins=0, mob_id=1)

    def test_stage(self):
        response = self.client.post('/dungeon/stage', {
            'value': str(constants.DungeonType.CAMPAIGN.value),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
