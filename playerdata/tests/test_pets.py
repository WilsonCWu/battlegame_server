from rest_framework.test import APITestCase
from playerdata.models import User


class UpdatePetsTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

    def test_ok_pet_change(self):
        self.u.inventory.active_pet_id = 0
        self.u.inventory.pets_unlocked = [0, 1]
        response = self.client.post('/pet/update/', {
            'value': '1'
        })
        self.assertTrue(response.data['status'])

    def test_bad_pet_change(self):
        self.u.inventory.active_pet_id = 0
        self.u.inventory.pets_unlocked = [0, 1]
        response = self.client.post('/pet/update/', {
            'value': '2'
        })
        self.assertFalse(response.data['status'])


class UnlockPetsTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

    def test_ok_pet_unlock(self):
        self.u.inventory.active_pet_id = 0
        self.u.inventory.pets_unlocked = [0, 1]
        response = self.client.post('/pet/unlock/master/', {
            'value': '2'
        })
        self.assertTrue(response.data['status'])

    def test_bad_pet_unlock(self):
        self.u.inventory.active_pet_id = 0
        self.u.inventory.pets_unlocked = [0, 1]
        response = self.client.post('/pet/unlock/master/', {
            'value': '1'
        })
        self.assertFalse(response.data['status'])


class UnlockStarterPetsTestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='testWilson')
        self.client.force_authenticate(user=self.u)

    def test_ok_pet_unlock(self):
        self.u.inventory.active_pet_id = 0
        self.u.inventory.pets_unlocked = [0]
        response = self.client.post('/pet/unlock/starter/', {
            'pet_id': '1',
            'legacy_unlock': 'True'
        })
        self.assertTrue(response.data['status'])
        response = self.client.post('/pet/update/', {
            'value': '0'
        })
        self.assertFalse(response.data['status'])
        response = self.client.post('/pet/update/', {
            'value': '1'
        })
        self.assertFalse(response.data['status'])

    def test_bad_pet_unlock(self):
        self.u.inventory.active_pet_id = 0
        self.u.inventory.pets_unlocked = [0]
        response = self.client.post('/pet/unlock/starter/', {
            'pet_id': '1',
            'legacy_unlock': 'False'
        })
        self.assertFalse(response.data['status'])
