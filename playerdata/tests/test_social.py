from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, ClanMember, Clan2


class ClanAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def join_clan(self):
        pass

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

        response = self.client.post('/clan/new/', {
            'clan_name': 'rdkiller',
            'clan_description': 'real ones only'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_join_clan(self):
    #     self.join_clan()


    def test_promote_coleader(self):
        member_id = 2
        target_member = User.objects.get(id=member_id)
        self.client.force_authenticate(user=target_member)
        response = self.client.post('/clan/requests/create/', {
            'value': 'rdkiller',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.u)
        response = self.client.post('/clan/requests/update/', {
            'target_user_id': member_id,
            'accept': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post('/clan/members/updatestatus/', {
            'member_id': member_id,
            'member_status': 'promote'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)


        target_clanmember = ClanMember.objects.get(userinfo_id=member_id)
        # TODO: after 0.2.2 need to promote twice for admin
        self.assertTrue(target_clanmember.is_admin)

    # TODO: uncomment after 0.2.2 for testing elder
    # def test_promote_elder(self):
    #     member_id = 2
    #     response = self.client.post('/clan/members/updatestatus/', {
    #         'member_id': member_id,
    #         'member_status': 'promote'
    #     })
    #
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    #     target_clanmember = ClanMember.objects.get(userinfo_id=member_id)
    #     self.assertTrue(target_clanmember.is_elder)
