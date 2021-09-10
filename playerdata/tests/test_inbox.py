from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import User, Mail, BaseCode
from datetime import datetime, timedelta, timezone


class InboxAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.sender = User.objects.get(username='battlegame')
        self.receiver = User.objects.get(id=21)
        self.client.force_authenticate(user=self.receiver)

    def test_get_inbox(self):
        mail = Mail.objects.create(sender=self.sender, receiver_id=21, message='hello')
        mail2 = Mail.objects.create(sender=self.sender, receiver_id=21, message='did you read this yet?')
        resp = self.client.get('/inbox/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_inbox_read(self):
        mail = Mail.objects.create(sender=self.sender, receiver_id=21, message='did you read this yet?')
        self.assertFalse(mail.is_read)

        resp = self.client.post('/inbox/read/', {
            'value': mail.id,
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        mail.refresh_from_db()
        self.assertTrue(mail.is_read)

    def test_inbox_send(self):
        self.client.force_authenticate(user=self.sender)
        msg = 'sup dude'
        resp = self.client.post('/inbox/send/', {
            'receiver_id': 21,
            'message': msg
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        self.client.force_authenticate(user=self.receiver)
        resp = self.client.get('/inbox/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['mail'][0]['message'], msg)

    def test_inbox_claim(self):
        curr_time = datetime.now(timezone.utc)
        basecode = BaseCode.objects.create(gems=100, code='100freegems', num_left=1, start_time=curr_time, end_time=curr_time + timedelta(days=2))
        mail = Mail.objects.create(sender=self.sender, receiver_id=21, message='free 100 gems', code=basecode)

        receiver_gems = self.receiver.inventory.gems

        resp = self.client.post('/inbox/claim/', {
            'value': mail.id
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['gems'], 100)
        self.receiver.inventory.refresh_from_db()
        self.assertEqual(self.receiver.inventory.gems, receiver_gems + 100)

        resp = self.client.post('/inbox/claim/', {
            'value': mail.id
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['status'])

    def test_delete_mail(self):
        mail = Mail.objects.create(sender=self.sender, receiver_id=21, message='hello')
        mail2 = Mail.objects.create(sender=self.sender, receiver_id=21, message='did you read this yet?')
        resp = self.client.get('/inbox/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

        resp = self.client.post('/inbox/delete/', {
            'value': mail.id
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])

        resp = self.client.get('/inbox/get/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['mail']), 1)
