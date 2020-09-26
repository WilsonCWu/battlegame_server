from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, Placement, BaseCharacter, Character

class PlacementsAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

        # Give u:battlegame some characters.
        base_archer = BaseCharacter.objects.get(name="Archer")
        self.archer = Character.objects.create(
            user = self.u,
            char_type = base_archer,
        )

    def _create_placement(self, characters, positions, is_tourney=False):
        return Placement.objects.create(
            user=self.u,
            char_1_id=characters[0],
            char_2_id=characters[1],
            char_3_id=characters[2],
            char_4_id=characters[3],
            char_5_id=characters[4],
            pos_1=positions[0],
            pos_2=positions[1],
            pos_3=positions[2],
            pos_4=positions[3],
            pos_5=positions[4],
            is_tourney=is_tourney,
        )

    def test_getting_placements(self):
        response = self.client.get('/placements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['placements']), 0)

        self._create_placement(
            [self.archer.char_id] + [None] * 4,
            [1] + [-1] * 4,
        )
        self._create_placement(
            [self.archer.char_id] + [None] * 4,
            [2] + [-1] * 4,
        )
        self._create_placement(
            [self.archer.char_id] + [None] * 4,
            [3] + [-1] * 4,
            is_tourney=True,
        )
        response = self.client.get('/placements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['placements']), 2)

    def test_new_placement(self):
        response = self.client.post('/placements/', {
            'characters': [self.archer.char_id] + [-1] * 4,
            'positions': [-1] * 5,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIsNotNone(response.data['placement_id'])
        self.assertEqual(Placement.objects.filter(user=self.u).count(), 1)

        # Give u:battlegame the max amount of placements.
        self._create_placement(
            [self.archer.char_id] + [None] * 4,
            [1] + [-1] * 4,
        )
        self._create_placement(
            [self.archer.char_id] + [None] * 4,
            [2] + [-1] * 4,
        )
        response = self.client.post('/placements/', {
            'characters': [self.archer.char_id] + [-1] * 4,
            'positions': [-1] * 5,
        })
        # TODO(yanke): a lot of our code returns OK for failed requests,
        # we should refactor this later when we get a chance.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_updating_placement(self):
        placement = self._create_placement(
            [self.archer.char_id] + [None] * 4,
            [1] + [-1] * 4,
        )
        response = self.client.post('/placements/', {
            'placement_id': placement.placement_id,
            'characters': [self.archer.char_id] + [-1] * 4,
            'positions': [2] + [-1] * 4,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        placement.refresh_from_db()
        self.assertEqual(placement.pos_1, 2)
