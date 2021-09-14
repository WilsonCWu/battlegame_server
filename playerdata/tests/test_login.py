from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import constants, level_booster
from playerdata.models import User, Character


class EditTextTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

    def test_bad_name(self):
        response = self.client.post('/changename/',{
            'name' : 'errorName\\'
        })
        self.assertTrue(not response.data['status']) # don't allow backslash.