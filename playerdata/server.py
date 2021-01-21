from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import ServerStatus


class MaintenanceSchema(Schema):
    maintenance_start = fields.DateTime()
    expected_end = fields.DateTime()


class ServerStatusView(APIView):
    def get(self, request):
        latest_version = ServerStatus.objects.filter(event_type='V').latest('creation_time')
        upcoming_maintenances = ServerStatus.objects.filter(event_type='M').filter(maintenance_start__gte=timezone.now())

        return Response({
            'version': latest_version.version_number,
            'patch_notes': latest_version.patch_notes,
            'upcoming_maintenances': [MaintenanceSchema(m).data for m in upcoming_maintenances],
        })
