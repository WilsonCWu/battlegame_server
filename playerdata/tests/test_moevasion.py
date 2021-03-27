from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, MoevasionStatus


class MoevasionAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def e2e_flow(self, flow):
        for method, url, body in flow:
            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, body)
            self.assertEqual(response.status_code, status.HTTP_200_OK, url)
            self.assertTrue(response.data['status'])
            
    def test_e2e(self):
        self.e2e_flow([
            ('POST', '/moevasion/start/', {}),
            ('GET', '/moevasion/stage/', {}),
            ('POST', '/moevasion/result/', {'is_loss': False, 'characters': '{"11": 10, "5": 100}'}),
            ('GET', '/moevasion/stage/', {}),
            ('POST', '/moevasion/result/', {'is_loss': False, 'characters': '{"11": 5, "5": 100}'}),
            ('GET', '/moevasion/stage/', {}),
            ('POST', '/moevasion/result/', {'is_loss': True, 'characters': '{"11": 0, "5": 100}'}),
            ('POST', '/moevasion/result/', {'is_loss': False, 'characters': '{"11": 0, "5": 10}'}),
            ('POST', '/moevasion/end/', {}),
        ])
        self.assertEqual(self.u.userinfo.best_moevasion_stage, 3)

        # Can safely restart a status.
        self.e2e_flow([
            ('POST', '/moevasion/start/', {}),
            ('GET', '/moevasion/stage/', {}),
        ])
