from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from playerdata.models import ServerStatus

class MatcherAPITestCase(APITestCase):
    def test_server_status(self):
        # Create two versions, one outdated.
        ServerStatus.objects.create(
            event_type = 'V',
            version_number = '1.0.0a',
            creation_time = timezone.now() - timedelta(days=1),
        )
        ServerStatus.objects.create(
            event_type = 'V',
            version_number = '1.0.1a',
        )
        # Create two migrations, one in the past and one upcoming.
        ServerStatus.objects.create(
            event_type = 'M',
            maintenance_start = timezone.now() - timedelta(days=1),
        )
        ServerStatus.objects.create(
            event_type = 'M',
            maintenance_start = timezone.now() + timedelta(days=1),
            expected_end = timezone.now() + timedelta(days=2),
        )

        response = self.client.get('/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['version'], '1.0.1a')
        self.assertEqual(len(response.data['upcoming_maintenances']), 1)
