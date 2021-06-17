from enum import Enum
from typing import List
from functools import lru_cache

from django.db.transaction import atomic
from marshmallow import fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema

from playerdata import constants, chests
from playerdata.models import EloRewardTracker, SeasonReward, UserInfo, ChampBadgeTracker
from playerdata.serializers import IntSerializer


class ChapterRewardSchema(Schema):
    world_id = fields.Int()
    reward_type = fields.Str()
    value = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()


class ChapterReward:
    def __init__(self, world_id, reward_type, value):
        self.world_id = world_id
        self.reward_type = reward_type
        self.value = value

    def to_chest_reward(self):
        return chests.ChestReward(self.reward_type, self.value)

# TODO: Currently supports just Advancement Rewards I, which is 1-19
#  Added a `type` just in case we want to do II, III like AFK did
@lru_cache()
def get_chapter_rewards_list() -> List[ChapterReward]:
    rewards = []

    for world in range(1, 20, 2):
        if world <= 7:
            gems = 2700
        elif world <= 11:
            gems = 3600
        elif world <= 15:
            gems = 5400
        else:
            gems = 8100

        rewards.append(ChapterReward(world, "gems", gems))

    return rewards


def complete_chapter_rewards(world: int, tracker: ChapterRewardsPack):
    for reward in get_chapter_rewards_list():
        if reward.world_id > world:
            break
        tracker.last_completed = max(reward.world_id, tracker.last_completed)

    tracker.save()


class GetChapterRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        chapter_rewards = get_chapter_rewards_list()
        rewards_data = ChapterRewardSchema(chapter_rewards, many=True).data

        for reward in rewards_data:
            reward['claimed'] = reward['id'] <= request.user.chapterrewardpack.last_claimed
            reward['completed'] = reward['id'] <= request.user.chapterrewardpack.last_completed

        return Response({'status': True,
                         'rewards': rewards_data,
                         'is_active': request.user.chapterrewardpack.is_active,
                         'expiration_date': request.user.chapterrewardpack.expiration_date})


class ClaimChapterRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward_id = serializer.validated_data['value']

        if not request.user.chapterrewardpack.is_active:
            return Response({'status': False, 'reason': 'chapter rewards pack is not activated'})

        if reward_id > request.user.chapterrewardpack.last_completed:
            return Response({'status': False, 'reason': 'have not reached the chapter for this reward'})

        if reward_id != request.user.chapterrewardpack.last_claimed + 1:
            return Response({'status': False, 'reason': 'must claim the next reward in order'})

        chapter_reward = get_chapter_rewards_list()[reward_id]
        rewards = [chapter_reward.to_chest_reward()]
        chests.award_chest_rewards(request.user, rewards)

        request.user.chapterrewardpack.last_claimed = reward_id
        request.user.chapterrewardpack.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
