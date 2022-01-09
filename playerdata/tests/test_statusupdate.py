from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from playerdata.statusupdate import calculate_tourney_elo, calculate_elo
from playerdata.models import User


class TourneyEloTestCase(TestCase):

    def setUp(self):
        self.r1 = 1200
        self.r2 = 1100

    def test_first_place(self):
        """First place gets 100% of the elo diff"""
        tourney_elo = calculate_tourney_elo(self.r1, self.r2, 0)
        self.assertEqual(tourney_elo, 1236)

    def test_second_place(self):
        """First place gets 75% of the elo diff"""
        tourney_elo = calculate_tourney_elo(self.r1, self.r2, 1)
        self.assertEqual(tourney_elo, 1227)

    def test_second_last_place(self):
        """Second last place gets -75% of the elo diff"""
        tourney_elo = calculate_tourney_elo(self.r1, self.r2, 6)
        self.assertEqual(tourney_elo, 1152)

    def test_last_place(self):
        """Last place gets -75% of the elo diff"""
        tourney_elo = calculate_tourney_elo(self.r1, self.r2, 7)
        self.assertEqual(tourney_elo, 1136)

    def test_below_zero(self):
        tourney_elo = calculate_tourney_elo(10, 2, 7)
        self.assertEqual(tourney_elo, 0)

    def test_elo_delta_consistent(self):
        win_tourney_elo = calculate_tourney_elo(self.r1, self.r2, 0)
        lose_tourney_elo = calculate_tourney_elo(self.r1, self.r2, 7)

        self.assertEqual(win_tourney_elo, round(calculate_elo(self.r1, self.r2, 1, 100)))
        self.assertEqual(lose_tourney_elo, round(calculate_elo(self.r1, self.r2, 0, 100)))


class QuickPlayTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(id=21)
        self.client.force_authenticate(user=self.u)
        self.sample_data = {'win': True, 'mode': 0, 'opponent_id': 1, 'stats': [{'id': 0, 'damage_dealt': 658013, 'damage_taken': 105156, 'health_healed': 0, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 35365, 'damage_taken': 0, 'health_healed': 145196, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 19770, 'damage_taken': 99908, 'health_healed': 0, 'mana_generated': 20}, {'id': 0, 'damage_dealt': 1466422, 'damage_taken': 493748, 'health_healed': 0, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 161370, 'damage_taken': 15346, 'health_healed': 0, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 85374, 'damage_taken': 661445, 'health_healed': 0, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 29880, 'damage_taken': 535173, 'health_healed': 0, 'mana_generated': 60}, {'id': 0, 'damage_dealt': 493748, 'damage_taken': 333021, 'health_healed': 0, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 12786, 'damage_taken': 307501, 'health_healed': 0, 'mana_generated': 0}, {'id': 0, 'damage_dealt': 92370, 'damage_taken': 503800, 'health_healed': 0, 'mana_generated': 0}], 'seed': -241903701, 'attacking_team': {'placement_id': 0, 'pos_1': 4, 'char_1': {'char_id': 113, 'user': 0, 'char_type': 13, 'level': 140, 'prestige': 2, 'copies': 3, 'hat': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'armor': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_2': 12, 'char_2': {'char_id': 21, 'user': 0, 'char_type': 9, 'level': 247, 'prestige': 10, 'copies': 30, 'hat': {'item_id': 28, 'user': 0, 'item_type': 1004, 'exp': 210}, 'armor': {'item_id': 246, 'user': 0, 'item_type': 2000, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 24, 'user': 0, 'item_type': 3030, 'exp': 40}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_3': 19, 'char_3': {'char_id': 14, 'user': 0, 'char_type': 7, 'level': 247, 'prestige': 6, 'copies': 190, 'hat': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'armor': {'item_id': 212, 'user': 0, 'item_type': 2027, 'exp': 40}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_4': 1, 'char_4': {'char_id': 8, 'user': 0, 'char_type': 0, 'level': 247, 'prestige': 11, 'copies': 1, 'hat': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'armor': {'item_id': 29, 'user': 0, 'item_type': 2029, 'exp': 50}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_5': 18, 'char_5': {'char_id': 22, 'user': 0, 'char_type': 10, 'level': 182, 'prestige': 6, 'copies': 24, 'hat': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'armor': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}}, 'defending_team': {'placement_id': 651, 'pos_1': 20, 'char_1': {'char_id': 3022, 'user': 0, 'char_type': 7, 'level': 180, 'prestige': 3, 'copies': 1, 'hat': {'item_id': 50, 'user': 0, 'item_type': 1004, 'exp': 0}, 'armor': {'item_id': 47, 'user': 0, 'item_type': 2008, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_2': 2, 'char_2': {'char_id': 3019, 'user': 0, 'char_type': 13, 'level': 180, 'prestige': 3, 'copies': 2, 'hat': {'item_id': 44, 'user': 0, 'item_type': 1015, 'exp': 0}, 'armor': {'item_id': 52, 'user': 0, 'item_type': 2009, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_3': 24, 'char_3': {'char_id': 3025, 'user': 0, 'char_type': 10, 'level': 180, 'prestige': 4, 'copies': 4, 'hat': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'armor': {'item_id': 42, 'user': 0, 'item_type': 2006, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_4': 3, 'char_4': {'char_id': 3023, 'user': 0, 'char_type': 6, 'level': 180, 'prestige': 3, 'copies': 7, 'hat': {'item_id': 46, 'user': 0, 'item_type': 1023, 'exp': 0}, 'armor': {'item_id': 54, 'user': 0, 'item_type': 2001, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}, 'pos_5': 25, 'char_5': {'char_id': 3024, 'user': 0, 'char_type': 9, 'level': 200, 'prestige': 3, 'copies': 5, 'hat': {'item_id': 45, 'user': 0, 'item_type': 1018, 'exp': 0}, 'armor': {'item_id': 48, 'user': 0, 'item_type': 2028, 'exp': 0}, 'weapon': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'boots': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_1': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'trinket_2': {'item_id': 0, 'user': 0, 'item_type': 0, 'exp': 0}, 'is_tourney': False}}}

    # This is just a safety to make sure we don't break quickplay
    def test_win(self):
        response = self.client.post('/uploadresult/quickplay/', {
            'result': self.sample_data,
        },
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
