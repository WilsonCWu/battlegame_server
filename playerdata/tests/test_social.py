from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, ClanMember


class ClanAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def join_clan(self, member_id):
        target_member = User.objects.get(id=member_id)
        self.client.force_authenticate(user=target_member)
        response = self.client.post('/clan/requests/create/', {
            'value': 'rdkiller',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        self.client.force_authenticate(user=self.u)
        response = self.client.post('/clan/requests/update/', {
            'target_user_id': member_id,
            'accept': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

        response = self.client.post('/clan/new/', {
            'clan_name': 'rdkiller',
            'clan_description': 'real ones only'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

    def test_join_clan(self):
        self.join_clan(member_id=2)

    def test_promote_coleader(self):
        member_id = 2
        self.join_clan(member_id)

        response = self.client.post('/clan/members/updatestatus/', {
            'member_id': member_id,
            'member_status': 'promote'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        response = self.client.post('/clan/members/updatestatus/', {
            'member_id': member_id,
            'member_status': 'promote'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        target_clanmember = ClanMember.objects.get(userinfo_id=member_id)
        self.assertTrue(target_clanmember.is_admin)

    def test_promote_elder(self):
        member_id = 2
        self.join_clan(member_id)

        response = self.client.post('/clan/members/updatestatus/', {
            'member_id': member_id,
            'member_status': 'promote'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        target_clanmember = ClanMember.objects.get(userinfo_id=member_id)
        self.assertTrue(target_clanmember.is_elder)
