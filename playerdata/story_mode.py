from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import chests, constants
from playerdata.models import StoryQuest
from playerdata.serializers import IntSerializer, CharStateResultSerializer

CHARACTER_POOLS = [[1, 4, 12]]  # TODO: more on the way as etilon works on dialogue
CHAR_POOL_CAMPAIGN_STAGE_UNLOCK = [60]  # stage that unlocks the respective character pool tiers
MAX_NUM_QUESTS = 5

# Pregame Buff ID Constants
STARTING_LEVEL = 1


class StoryModeSchema(Schema):
    available_stories = fields.List(fields.Int())
    completed_stories = fields.List(fields.Int())
    buff_points = fields.Int()
    current_tier = fields.Int()

    # Current Story progress fields
    last_complete_quest = fields.Int()
    last_quest_reward_claimed = fields.Int()
    story_id = fields.Int()

    character_state = fields.Str()
    boons = fields.Str()


class StoryQuestSchema(Schema):
    char_type = fields.Int(attribute='char_type.char_type_id')
    order = fields.Int()
    title = fields.Str()
    description = fields.Str()
    char_dialogs = fields.Str()
    is_completed = fields.Method('get_is_completed')
    is_claimed = fields.Method('get_is_claimed')
    rewards = fields.Method('get_quest_rewards')

    def get_is_completed(self, story_quest):
        return story_quest.order <= self.context['last_complete_quest']

    def get_is_claimed(self, story_quest):
        return story_quest.order <= self.context['last_quest_reward_claimed']

    def get_quest_rewards(self, story_quest):
        rewards = story_rewards(self.context['story_id'], self.context['current_tier'], story_quest.order)
        return chests.ChestRewardSchema(rewards, many=True).data


# does automatic backfilling for us whenever we add new batches
def unlock_next_character_pool(user, dungeon_stage):
    # checks the expected tier, and if it's less than the current_tier then we backfill
    target_tier = len(CHAR_POOL_CAMPAIGN_STAGE_UNLOCK) - 1
    while target_tier >= 0 and dungeon_stage < CHAR_POOL_CAMPAIGN_STAGE_UNLOCK[target_tier]:
        target_tier -= 1

    if user.storymode.current_tier >= target_tier:
        return

    # add all char pools from [current_tier + 1, target_tier] inclusive
    for tier in range(user.storymode.current_tier, target_tier):
        user.storymode.available_stories.extend(CHARACTER_POOLS[tier + 1])

    user.storymode.current_tier = target_tier
    user.storymode.save()


class GetStoryModeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        story_json = StoryModeSchema(request.user.storymode).data
        char_pool = [{'chars': pool} for pool in CHARACTER_POOLS]  # format json nested list

        story_quests = StoryQuest.objects.filter(char_type_id=request.user.storymode.story_id).order_by('order')
        quests_schema = StoryQuestSchema(story_quests, many=True)
        quests_schema.context = story_json

        return Response({'status': True,
                         'story_mode': story_json,
                         'char_pool': char_pool,
                         'story_quests': quests_schema.data
                         })


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
        request.user.storymode.last_complete_quest += 1

        # reset story mode
        if request.user.storymode.last_complete_quest == MAX_NUM_QUESTS:
            request.user.storymode.available_stories.remove(request.user.storymode.story_id)
            request.user.storymode.completed_stories.append(request.user.storymode.story_id)
            request.user.storymode.last_complete_quest = -1
            request.user.storymode.last_quest_reward_claimed = -1
            request.user.storymode.story_id = -1
            request.user.storymode.cur_character_state = ""

        request.user.storymode.save()

        return Response({'status': True})


# TODO: scale based on story_tier once we add more batches
def story_rewards(story_id, story_tier: int, quest_num: int):
    rewards = []

    if quest_num < 2:
        gems = 300 + quest_num * 200
        rewards.append(chests.ChestReward(constants.RewardType.GEMS.value, gems))
    elif quest_num < 4:
        epic_shards = 50 + quest_num * 80
        relic_stones = 200 + quest_num * 200
        rewards.append(chests.ChestReward(constants.RewardType.RELIC_STONES.value, relic_stones))
        rewards.append(chests.ChestReward(constants.RewardType.EPIC_SHARDS.value, epic_shards))
    else:
        dust_fast_rewards = 24
        ember = 250
        rewards.append(chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, dust_fast_rewards))
        rewards.append(chests.ChestReward(constants.RewardType.EMBER.value, ember))

        # for april fools 2022, we drop them another Moe
        if story_id == 1:
            rewards.append(chests.ChestReward(constants.RewardType.CHAR_ID.value, 1))

    return rewards


class ClaimStoryQuestReward(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        if request.user.storymode.last_quest_reward_claimed >= request.user.storymode.last_complete_quest:
            return Response({'status': False, 'reason': 'cannot claim incomplete quest'})

        rewards = story_rewards(request.user.storymode.story_id, request.user.storymode.current_tier, request.user.storymode.last_quest_reward_claimed + 1)
        request.user.storymode.last_quest_reward_claimed += 1
        request.user.storymode.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


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
