from rest_framework.test import APITestCase
from playerdata.models import User

class ChangeNameTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

    def test_bad_name_backslash(self):
        response = self.client.post('/changename/',{
            'name' : 'errorName\\'
        })
        self.assertFalse(response.data['status']) # don't allow backslash.
    def test_bad_name_newline(self):
        response = self.client.post('/changename/',{
            'name' : 'error\nName'
        })
        self.assertFalse(response.data['status']) # don't allow newline.
    def test_ok_name(self):
        response = self.client.post('/changename/',{
            'name' : 'okName'
        })
        self.assertTrue(response.data['status'])