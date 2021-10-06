from rest_framework.test import APITestCase

from playerdata.models import User
from playerdata.creatorcode import generate_creator_code


class CreatorCodeTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)
        generate_creator_code(self.u, 'TESTINGCODE')

    def test_get_status(self):
        response = self.client.get('/creatorcode/status/')
        self.assertTrue(response.data['status'])

    def test_bad_set_code_unknowncode(self):
        response = self.client.post('/creatorcode/set/', {
            'value': 'TESTINGCODE'
        })
        self.assertFalse(response.data['status'])

    def test_bad_set_code_owncode(self):
        response = self.client.post('/creatorcode/set/', {
            'value': 'BADCODE'
        })
        self.assertFalse(response.data['status'])

    def test_get_own_code(self):
        response = self.client.get('/creatorcode/get/')
        self.assertTrue(response.data['status'])
        self.assertTrue(response.data['creator_code'] == 'TESTINGCODE')
