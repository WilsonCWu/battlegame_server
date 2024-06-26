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
from playerdata.models import ChapterRewardPack, SeasonReward, UserInfo, ChampBadgeTracker
from playerdata.serializers import IntSerializer


class ChapterRewardSchema(Schema):
    id = fields.Int()
    world = fields.Int()
    reward_type = fields.Str()
    value = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()


class ChapterReward:
    def __init__(self, chapter_id, world, reward_type, value):
        self.id = chapter_id
        self.world = world
        self.reward_type = reward_type
        self.value = value

    def to_chest_reward(self):
        return chests.ChestReward(self.reward_type, self.value)


# TODO: Currently supports just Advancement Rewards I, which is 1-19
#  Added a `type` just in case we want to do II, III like AFK did
@lru_cache()
def get_chapter_rewards_list() -> List[ChapterReward]:
    rewards = []

    chapter_id = 0
    for world in range(1, 20, 2):
        if world <= 7:
            gems = 2700
        elif world <= 11:
            gems = 3600
        elif world <= 15:
            gems = 5400
        else:
            gems = 8100

        rewards.append(ChapterReward(chapter_id, world, "gems", gems))
        chapter_id += 1

    return rewards


def complete_chapter_rewards(world: int, tracker: ChapterRewardPack):
    for reward in get_chapter_rewards_list():
        if reward.world > world:
            break
        tracker.last_completed = max(reward.id, tracker.last_completed)

    tracker.save()


def refund_chapter_pack(user):
    total = 0
    for reward in get_chapter_rewards_list():
        if reward.world <= user.chapterrewardpack.last_claimed:
            total += reward.value

    user.inventory.gems -= total
    user.inventory.save()

    user.chapterrewardpack.is_active = False
    user.chapterrewardpack.last_completed = -1
    user.chapterrewardpack.last_claimed = -1
    user.chapterrewardpack.save()


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
                         'last_claimed': request.user.chapterrewardpack.last_claimed,
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
