from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.serializers import IntSerializer, CharStateResultSerializer

CHARACTER_POOLS = [[1, 2, 3]]  # TODO: more on the way as etilon works on dialogue
MAX_NUM_QUESTS = 5

# Pregame Buff ID Constants
STARTING_LEVEL = 1


class StoryModeSchema(Schema):
    available_stories = fields.List(fields.Int())
    completed_stories = fields.List(fields.Int())
    buff_points = fields.Int()
    current_tier = fields.Int()

    # Current Story progress fields
    current_quest = fields.Int()
    story_id = fields.Int()

    character_state = fields.Str()
    boons = fields.Str()


def unlock_next_character_pool(user):
    user.storymode.current_tier += 1
    user.storymode.available_stories.extend(CHARACTER_POOLS[user.storymode.current_tier])

    user.storymode.save()


class GetStoryModeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        schema = StoryModeSchema(request.user.storymode)
        return Response({'status': True, 'story_mode': schema.data, 'char_pool': CHARACTER_POOLS})


class StartNewStoryView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        story_id = serializer.validated_data['value']

        story_mode = request.user.storymode

        if story_id not in story_mode.available_stories:
            return Response({'status': False, 'reason': 'titan is not available yet'})

        story_mode.story_id = story_id
        story_mode.save()

        return Response({'status': True})


class StoryResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = CharStateResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_loss = serializer.validated_data['is_loss']
        characters = serializer.validated_data['characters']

        # TODO: Currently no impact on losing a quest, potentially make more interesting by changing difficulty or buffs
        if is_loss:
            return Response({'status': True})

        request.user.storymode.cur_character_state = characters
        request.user.storymode.current_quest += 1

        if request.user.storymode.current_quest == MAX_NUM_QUESTS:
            request.user.storymode.available_stories.remove(request.user.storymode.story_id)
            request.user.storymode.completed_stories.append(request.user.storymode.story_id)
            request.user.storymode.current_quest = 0
            request.user.storymode.story_id = -1
            request.user.storymode.cur_character_state = ""

        request.user.storymode.save()

        return Response({'status': True})


class ChooseBoonView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        boon_id = serializer.validated_data['value']

        boons = request.user.storymode.boons
        newboons = get_boons(request.user)
        boon_rarity = -1

        for b in newboons:
            if boon_id == b['id']:
                boon_rarity = b['rarity']

        if boon_rarity == -1:
            return Response({'status': False, 'reason': 'invalid boon selection'})

        # If new boon, we set the rarity, else we just increase the level
        if boon_id in boons:
            boons[boon_id]['level'] += 1
        else:
            boons[boon_id] = {'rarity': boon_rarity, 'level': 1}

        request.user.storymode.save()
        return Response({'status': True})


# TODO: return a list of 3 boons to choose from
# {'id' : <id>, 'rarity': <rarity>}
def get_boons(user):
    # randomized to that user, that run, and that level

    return [{'id': 1, 'rarity': 1}, {'id': 2, 'rarity': 1}, {'id': 3, 'rarity': 1}]


class GetBoonsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        boons = get_boons(request.user)

        return Response({'status': True, 'boons': boons})


# TODO: determine costs for various tiers of buffs
def get_buff_cost(buff_id: int, level: int):
    return 1


# Returns the number of additional start levels this buff gives
def get_start_level_buff(pregame_buffs):
    if STARTING_LEVEL not in pregame_buffs:
        return 0

    return pregame_buffs[STARTING_LEVEL] * 5


class LevelBuffView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        buff_id = serializer.validated_data['value']

        story_mode = request.user.storymode

        if buff_id in story_mode.pregame_buffs:
            story_mode.pregame_buffs[buff_id] += 1
        else:
            story_mode.pregame_buffs[buff_id] = 1

        pts_cost = get_buff_cost(buff_id, story_mode.pregame_buffs[buff_id])
        if story_mode.buff_points < pts_cost:
            return Response({'status': False, 'reason': 'not enough points to level'})

        story_mode.buff_points -= pts_cost
        story_mode.save()
        return Response({'status': True})
