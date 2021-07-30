from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User


class RotatingModeAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    # TODO
    def test_get(self):
        pass

    # TODO
    def test_result(self):
        pass

    # TODO
    def test_claim(self):
        pass
