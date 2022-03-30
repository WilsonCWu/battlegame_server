from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import ExpeditionMap
from playerdata.serializers import IntSerializer


class ExpeditionMapSchema(Schema):
    char_type = fields.Int(attribute='char_type_id')
    quest_id = fields.Int()
    version = fields.Str()
    map_json = fields.Str()


class GetExpeditionMapView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quest_id = serializer.validated_data['value']

        story_id = request.user.storymode.story_id

        latest_map = ExpeditionMap.objects.filter(char_type_id=story_id, quest_id=quest_id).order_by('-version').first()
        if latest_map is None:
            return Response({'status': False, 'reason': 'no map found'})

        map_schema = ExpeditionMapSchema(latest_map)
        return Response({'status': True, 'latest_map': map_schema.data})
