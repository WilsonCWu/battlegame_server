from rest_framework import status
from rest_framework.test import APITestCase

from playerdata import shards
from playerdata.models import User, Character


def get_num_copies_of_rarity(user, rarity: int):
    chars = Character.objects.filter(user=user, char_type__rarity=rarity)
    return sum([c.copies + 1 for c in chars])  # plus 1 for the 0th copy


class ShardsAPITestCase(APITestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.client.force_authenticate(user=self.u)

    def run_summons(self, num_summons, rarity):
        org_num = get_num_copies_of_rarity(self.u, rarity)

        response = self.client.post('/shards/summons/', {
            'num_chars': num_summons,
            'rarity': rarity
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])

        copy_total = get_num_copies_of_rarity(self.u, rarity)
        self.assertEqual(org_num + num_summons, copy_total)

    def test_summon1(self):
        num_summons = 1
        rarity = 2
        self.u.inventory.rare_shards = shards.SHARD_SUMMON_COST * num_summons
        self.u.inventory.save()

        self.run_summons(num_summons, rarity)

    def test_summon5(self):
        num_summons = 5
        rarity = 3

        self.u.inventory.epic_shards = shards.SHARD_SUMMON_COST * num_summons
        self.u.inventory.save()

        self.run_summons(num_summons, rarity)

    def test_summon10(self):
        num_summons = 10
        rarity = 4

        self.u.inventory.legendary_shards = shards.SHARD_SUMMON_COST * num_summons
        self.u.inventory.save()

        self.run_summons(num_summons, rarity)

    def test_no_enough_shards(self):
        num_summons = 10
        rarity = 4

        response = self.client.post('/shards/summons/', {
            'num_chars': num_summons,
            'rarity': rarity
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])

    def test_negative_num_chars(self):
        num_summons = -1
        rarity = 3

        self.u.inventory.epic_shards = shards.SHARD_SUMMON_COST * 10
        self.u.inventory.save()

        response = self.client.post('/shards/summons/', {
            'num_chars': num_summons,
            'rarity': rarity
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['status'])
