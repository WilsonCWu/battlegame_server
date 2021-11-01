import math
from datetime import datetime, timedelta
from typing import List
from functools import lru_cache

from django.contrib.auth.models import User
from django.db.transaction import atomic
from marshmallow import fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema

from playerdata import constants, chests, formulas
from playerdata.models import EloRewardTracker, SeasonReward, UserInfo, ChampBadgeTracker
from playerdata.serializers import IntSerializer

ELO_CAP = 6000
CHAMP_BADGE_CAP = 1000

# Examples:
# {'gems', 1, 50, 100}
# {'char_id', 1, 100, 12}
# {'item_id', 1, 150, 1001}
# {'coins', 1, 200, 10000}
# {'chest', 1, 250, 1 (rarity)}
class EloRewardSchema(Schema):
    id = fields.Int()
    elo = fields.Int()
    reward_type = fields.Str()
    value = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()


class EloReward:
    def __init__(self, reward_id, elo, reward_type, value):
        self.id = reward_id
        self.elo = elo
        self.reward_type = reward_type
        self.value = value


def elo_to_tier(elo: int):
    if elo < constants.Tiers.GRANDMASTER.value * constants.TIER_ELO_INCREMENT:
        return constants.Tiers(math.floor(elo / constants.TIER_ELO_INCREMENT) + 1)
    else:
        return constants.Tiers.GRANDMASTER


#  we peg the rewards to the middle elo of each tier
#  Ex: If you're at Bronze 4 (100-199 elo), the rewards are pegged at 150 elo
def get_tier_reward_elo(tier: int):
    return (tier * constants.TIER_ELO_INCREMENT) - constants.TIER_ELO_INCREMENT / 2


# can change to regular @cache if we upgrade python 3.9
@lru_cache()
def get_elo_rewards_list() -> List[EloReward]:
    rewards = []
    last_reward_elo = constants.Tiers.GRANDMASTER.value * constants.TIER_ELO_INCREMENT - (constants.TIER_ELO_INCREMENT // 2)

    reward_id = 0
    for elo in range(50, last_reward_elo, 50):
        counter_offset = reward_id + 1
        if counter_offset % 10 == 0:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.MYTHICAL.value))
        elif counter_offset % 5 == 0:
            rewards.append(EloReward(reward_id, elo, 'gems', 500))
        elif counter_offset % 5 == 4:
            rewards.append(EloReward(reward_id, elo, 'essence', 100 * elo_to_tier(elo).value))
        elif counter_offset % 5 == 3:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.GOLD.value))
        elif counter_offset % 5 == 2:
            rewards.append(EloReward(reward_id, elo, 'coins', 5000 * elo_to_tier(elo).value))
        elif counter_offset % 5 == 1:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.SILVER.value))

        reward_id += 1

    start_elite_season_rewards = last_reward_elo + 50
    for elo in range(start_elite_season_rewards, ELO_CAP + 1, 100):
        counter_offset = reward_id + 1
        if counter_offset % 10 == 0:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.LEGENDARY.value))
        elif counter_offset % 5 == 0:
            # rewards.append(EloReward(reward_id, elo, 'champ_badge', 30))
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.GOLD.value))
        elif counter_offset % 5 == 4:
            rewards.append(EloReward(reward_id, elo, 'gems', 600))
        elif counter_offset % 5 == 3:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.MYTHICAL.value))
        elif counter_offset % 5 == 2:
            rewards.append(EloReward(reward_id, elo, 'relic_stone', (elo // 10) - 20))
        elif counter_offset % 5 == 1:
            # rewards.append(EloReward(reward_id, elo, 'champ_badge', 20))
            rewards.append(EloReward(reward_id, elo, 'gems', 600))

        reward_id += 1

    return rewards


# can change to regular @cache if we upgrade python 3.9
@lru_cache()
def get_champ_rewards_list() -> List[EloReward]:
    rewards = []
    points_range = range(50, CHAMP_BADGE_CAP, 50)

    # TODO: More vanity rewards instead of just profile pics
    for reward_id, points in enumerate(points_range):
        rewards.append(EloReward(reward_id, points, 'profile_pic', reward_id + 15))

    return rewards


# returns a List[ChestReward]
def convert_elo_reward_to_chest_reward(elo_reward: EloReward, user: User):
    if elo_reward.reward_type == 'chest':
        return chests.generate_chest_rewards(elo_reward.value, user)
    else:
        return [chests.ChestReward(elo_reward.reward_type, elo_reward.value)]


class GetEloRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        elo_rewards = get_elo_rewards_list()
        rewards_data = EloRewardSchema(elo_rewards, many=True).data

        for reward in rewards_data:
            reward['claimed'] = reward['id'] <= request.user.elorewardtracker.last_claimed
            reward['completed'] = reward['id'] <= request.user.elorewardtracker.last_completed

        return Response({'status': True, 'rewards': rewards_data, 'expiration_date': get_season_expiration_date()})


class ClaimEloRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward_id = serializer.validated_data['value']

        if reward_id > request.user.elorewardtracker.last_completed:
            return Response({'status': False, 'reason': 'have not reached the elo for this reward'})

        if reward_id != request.user.elorewardtracker.last_claimed + 1:
            return Response({'status': False, 'reason': 'must claim the next reward in order'})

        elo_reward = get_elo_rewards_list()[reward_id]
        rewards = convert_elo_reward_to_chest_reward(elo_reward, request.user)
        chests.award_chest_rewards(request.user, rewards)

        request.user.elorewardtracker.last_claimed = reward_id
        request.user.elorewardtracker.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


def complete_any_elo_rewards(elo: int, tracker: EloRewardTracker):
    for reward in get_elo_rewards_list():
        if reward.elo > elo:
            break
        tracker.last_completed = max(reward.id, tracker.last_completed)

    tracker.save()


class GetSeasonRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        season_reward = request.user.seasonreward

        return Response({'status': True,
                         'is_claimed': season_reward.is_claimed,
                         'tier_rank': season_reward.tier_rank,
                         'expiration_date': get_season_expiration_date()})


class ClaimSeasonRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        season_reward = request.user.seasonreward
        if season_reward.is_claimed:
            return Response({'status': False, 'reason': 'season reward already claimed!'})

        rewards = get_season_reward(season_reward.tier_rank, request.user)
        chests.award_chest_rewards(request.user, rewards)

        season_reward.is_claimed = True
        season_reward.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


# At 0 UTC on the 1st of every month
def get_season_expiration_date():
    today = datetime.today()
    return (datetime(today.year, today.month, 1, 0) + timedelta(days=32)).replace(day=1)


# EndSeasonRewards
@atomic()
def restart_season():
    seasons = SeasonReward.objects.select_related('user__userinfo').all()

    for season in seasons:
        if hasattr(season.user, 'userinfo'):
            season.tier_rank = elo_to_tier(season.user.userinfo.highest_season_elo).value
            season.is_claimed = False

    SeasonReward.objects.bulk_update(seasons, ['tier_rank', 'is_claimed'])

    # Reset all players in Grandmaster to 3k
    grandmaster_elo = constants.TIER_ELO_INCREMENT * (constants.Tiers.GRANDMASTER.value - 1)
    elo_reset_users = UserInfo.objects.filter(highest_season_elo__gte=grandmaster_elo).select_related('user__elorewardtracker')
    elo_trackers = []
    for userinfo in elo_reset_users:
        userinfo.elo = grandmaster_elo
        userinfo.highest_season_elo = userinfo.elo

        # Reset their EloRewardTrackers so they can reclaim the new season rewards
        tracker = userinfo.user.elorewardtracker
        tracker.last_claimed = min(tracker.last_claimed, 59)
        tracker.last_completed = 59
        elo_trackers.append(tracker)

    UserInfo.objects.bulk_update(elo_reset_users, ['elo', 'highest_season_elo'])
    EloRewardTracker.objects.bulk_update(elo_trackers, ['last_claimed', 'last_completed'])


def get_season_reward(tier: int, user):
    rewards = []

    if tier <= constants.Tiers.BRONZE_ONE.value:  # 1-5
        rewards.append(chests.ChestReward('gems', 80 + 20 * tier))  # range here is 100 to 180

    elif tier <= constants.Tiers.SILVER_ONE.value:  # 6-10
        rewards.append(chests.ChestReward('gems', 175 + 25 * (tier - constants.Tiers.BRONZE_ONE.value)))  # range here is 200 to 300

    elif tier <= constants.Tiers.GOLD_ONE.value:  # 11-15
        rewards.append(chests.ChestReward('gems', 290 + 30 * tier))  # range here is 320 to 440

    elif tier <= constants.Tiers.PLAT_ONE.value:  # 16-20
        rewards.append(chests.ChestReward('gems', 450 + 30 * tier))  # range here is 480 to 600

    elif tier <= constants.Tiers.DIAMOND_ONE.value:  # 21-25
        rewards.append(chests.ChestReward('gems', 605 + 35 * tier))  # range here is 640 to 780

    else:
        # MASTER
        rewards.append(chests.ChestReward('gems', 820))

    rewards.append(chests.ChestReward('relic_stone', tier * 55 + 200))  # TODO: lower once we have vanity rewards
    rewards.append(chests.ChestReward('essence', formulas.dust_chest_reward(user, constants.ChestType.GOLD.value, tier) * 2))

    return rewards


class GetChampBadgeRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        rewards = get_champ_rewards_list()
        rewards_data = EloRewardSchema(rewards, many=True).data

        for reward in rewards_data:
            reward['claimed'] = reward['id'] <= request.user.champbadgetracker.last_claimed
            reward['completed'] = reward['id'] <= request.user.champbadgetracker.last_completed

        return Response({'status': True, 'rewards': rewards_data})


def complete_any_champ_rewards(points: int, tracker: ChampBadgeTracker):
    for reward in get_elo_rewards_list():
        if reward.elo > points:
            break
        tracker.last_completed = max(reward.id, tracker.last_completed)

    tracker.save()


class ClaimChampRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward_id = serializer.validated_data['value']

        if reward_id > request.user.champbadgetracker.last_completed:
            return Response({'status': False, 'reason': 'have not reached the points for this reward'})

        if reward_id != request.user.champbadgetracker.last_claimed + 1:
            return Response({'status': False, 'reason': 'must claim the next reward in order'})

        elo_reward = get_champ_rewards_list()[reward_id]
        rewards = convert_elo_reward_to_chest_reward(elo_reward, request.user)
        chests.award_chest_rewards(request.user, rewards)

        request.user.champbadgetracker.last_claimed = reward_id
        request.user.champbadgetracker.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
