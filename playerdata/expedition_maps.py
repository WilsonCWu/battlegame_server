from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import ExpeditionMap
from playerdata.serializers import ExpeditionMapSerializer


class ExpeditionMapSchema(Schema):
    mapkey = fields.Str()
    version = fields.Str()
    map_json = fields.Str()


class GetExpeditionMapView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = ExpeditionMapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game_mode = serializer.validated_data['game']
        mapkey = serializer.validated_data['mapkey']

        latest_map = ExpeditionMap.objects.filter(mapkey=mapkey, game_mode=game_mode).order_by('-version').first()
        if latest_map is None:
            return Response({'status': False, 'reason': 'no map found'})

        map_schema = ExpeditionMapSchema(latest_map)
        return Response({'status': True, 'latest_map': map_schema.data})
