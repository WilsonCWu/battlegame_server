import json

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from playerdata import constants

from playerdata.models import User, ServerStatus, DungeonBoss, DungeonStage, DungeonProgress

# can only use chars from 0-11 in test fixtures
test_comp_str = u'[{"char_id": 0, "position": 6}, {"char_id": 1, "position": 10}, {"char_id": 8, "position": 15}, {"char_id": 10, "position": 16}, {"char_id": 11, "position": 22}]'
test_with_items = u'[{"char_id": 0, "position": 6, "weapon_id": 32}, {"char_id": 1, "position": 10, "hat_id": 10000, "weapon_id": 88}, {"char_id": 8, "position": 15}, {"char_id": 10, "position": 16}, {"char_id": 11, "position": 22}]'

class DungeonStageAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

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

    def test_char_items(self):
        DungeonBoss.objects.create(stage=140, team_comp=json.loads(test_with_items))
        DungeonStage.objects.create(stage=121, dungeon_type=0, player_exp=0, gems=0, coins=0, mob_id=1)

        dungeon_progress = DungeonProgress.objects.get(user=self.u)
        dungeon_progress.campaign_stage = 121
        dungeon_progress.save()

        response = self.client.post('/dungeon/stage', {
            'value': str(constants.DungeonType.CAMPAIGN.value),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        char1 = response.data['mob']['char_1']
        char2 = response.data['mob']['char_2']

        self.assertEqual(char1['weapon']['item_type'], 32)
        self.assertEqual(char2['weapon']['item_type'], 88)
        self.assertEqual(char2['hat']['item_type'], 10000)

    def test_overlevel_carry(self):
        DungeonBoss.objects.create(stage=140, team_comp=json.loads(test_comp_str), carry_id=11)
        DungeonStage.objects.create(stage=121, dungeon_type=0, player_exp=0, gems=0, coins=0, mob_id=1)

        dungeon_progress = DungeonProgress.objects.get(user=self.u)
        dungeon_progress.campaign_stage = 121
        dungeon_progress.save()

        response = self.client.post('/dungeon/stage', {
            'value': str(constants.DungeonType.CAMPAIGN.value),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        # check that char 11 is overlevelled by 10
        char5_level = response.data['mob']['char_5']['level']
        char4_level = response.data['mob']['char_4']['level']

        # overlevel is by 10, stage 121 works well because all
        # chars have the same level pre-overlevelling, so comparing against any works
        self.assertTrue(char5_level - 10 == char4_level)
