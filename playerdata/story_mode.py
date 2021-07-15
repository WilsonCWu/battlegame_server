from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.serializers import IntSerializer


class StoryModeSchema(Schema):
    available_stories = fields.List(fields.Int())
    completed_stories = fields.List(fields.Int())
    buff_points = fields.Int()
    current_tier = fields.Int()

    # Current Story progress fields
    current_lvl = fields.Int()
    num_runs = fields.Int()
    story_id = fields.Int()

    cur_character_state = fields.Str()
    checkpoint_state = fields.Str()


class GetStoryModeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        schema = StoryModeSchema(request.user.storymode)
        return Response(schema.data)


class StartNewStory(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        story_id = serializer.validated_data['value']
        
        # TODO
        pass


class StoryResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        # TODO
        pass
