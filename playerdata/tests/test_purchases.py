from rest_framework.test import APITestCase
from rest_framework import status

from playerdata.models import User, Character
from playerdata.purchases import generate_and_insert_characters

class GenerateCharactersTestCase(APITestCase):

    fixtures = ['playerdata/tests/fixtures.json']
    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def test_summon_10(self):
        # first delete default characters
        Character.objects.filter(user=self.u).delete()

        char_map = generate_and_insert_characters(self.u, 10)
        database_chars = Character.objects.filter(user=self.u)

        #assert 10 generated
        self.assertEqual(sum(list(map(lambda x: x[1].count, char_map.items()))), 10)

        #assert database is accurate
        for database_char in database_chars:
            self.assertEqual(char_map[database_char.char_id].count, database_char.copies)
