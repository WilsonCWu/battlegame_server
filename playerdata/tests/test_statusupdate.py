from django.test import TestCase

from playerdata.statusupdate import calculate_tourney_elo, calculate_elo


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
