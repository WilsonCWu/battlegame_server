from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import Character
from playerdata.serializers import IntSerializer, CharStateResultSerializer

CHARACTER_POOLS = [[13, 4, 24, 11], []]


class StoryModeSchema(Schema):
    available_stories = fields.List(fields.Int())
    completed_stories = fields.List(fields.Int())
    buff_points = fields.Int()
    current_tier = fields.Int()

    # Current Story progress fields
    current_lvl = fields.Int()
    num_runs = fields.Int()
    story_id = fields.Int()

    character_state = fields.Str()


def unlock_next_character_pool(user):
    user.storymode.current_tier += 1
    user.storymode.available_stories = CHARACTER_POOLS[user.storymode.current_tier]

    user.storymode.save()


class GetStoryModeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        schema = StoryModeSchema(request.user.storymode)
        return Response(schema.data)


class StartNewStoryView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        story_id = serializer.validated_data['value']

        reset_story(request.user, story_id)

        story_mode = request.user.storymode
        story_mode.story_id = story_id
        story_mode.save()

        return Response({'status': True})


def reset_story(user, story_id):
    Character.objects.filter(user=user, is_story=True).delete()

    # TODO: get this from where we story pre-game buffs
    starting_level = 21
    starting_prestige = 0

    Character.objects.create(user=user, char_type_id=story_id, level=starting_level, prestige=starting_prestige)

    user.storymode.cur_character_state = ""
    user.storymode.current_lvl = 0
    user.storymode.save()


class StoryResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = CharStateResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_loss = serializer.validated_data['is_loss']
        characters = serializer.validated_data['characters']

        if is_loss:
            reset_story(request.user, request.user.storymode.story_id)
            return Response({'status': True})

        request.user.storymode.cur_character_state = characters
        request.user.storymode.current_lvl += 1
        request.user.storymode.save()

        return Response({'status': True})
