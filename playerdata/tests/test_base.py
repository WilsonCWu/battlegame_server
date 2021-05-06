from django.test import TestCase

from playerdata.base import BaseInfoView
from playerdata.models import User, Flag, UserFlag


class BaseFlagTestCase(TestCase):
    fixtures = ['playerdata/tests/fixtures.json']

    def setUp(self):
        self.u = User.objects.get(username='battlegame')
        self.dummy_flag = Flag.objects.create(name='dummy', value=False)

    def test_get_global_flags(self):
        flags = BaseInfoView.flags(self.u)
        self.assertTrue(any(f['name'] == 'dummy' and not f['value'] for f in flags))

    def test_user_override_flags(self):
        self.user_flag = UserFlag.objects.create(flag=self.dummy_flag,
                                                 user=self.u,
                                                 value=True)
        flags = BaseInfoView.flags(self.u)
        self.assertTrue(any(f['name'] == 'dummy' and f['value'] for f in flags))
