from django.utils import timezone
from packaging import version
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import ServerStatus


class MaintenanceSchema(Schema):
    maintenance_start = fields.DateTime()
    expected_end = fields.DateTime()


def is_server_version_higher(version_num):
    latest_version = ServerStatus.objects.filter(event_type='V').latest('creation_time')
    return version.parse(latest_version.version_number) > version.parse(version_num)


class ServerStatusView(APIView):
    def get(self, request):
        latest_version = ServerStatus.objects.filter(event_type='V').latest('creation_time')
        latest_required = ServerStatus.objects.filter(event_type='V', require_update=True).latest('creation_time')
        upcoming_maintenances = ServerStatus.objects.filter(event_type='M').filter(maintenance_start__gte=timezone.now())

        return Response({
            'status': True,
            'version': latest_version.version_number,
            'patch_notes': latest_version.patch_notes,
            'last_required_update_version': latest_required.version_number,
            'upcoming_maintenances': [MaintenanceSchema(m).data for m in upcoming_maintenances],
        })
