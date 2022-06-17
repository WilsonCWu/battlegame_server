from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import chests, tier_system, leaderboards, constants
from playerdata.models import ClanSeasonReward


def get_clan_season_rewards(rank: int):
    rewards = []
    base_relic_stones = 2000
    relic_stones = 0

    if rank == 1:
        dust_hours = 32
        relic_stones = base_relic_stones
        rewards.append(chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, dust_hours))
    elif rank <= 10:
        dust_hours = 24
        relic_stones = base_relic_stones - (50 * rank)
        rewards.append(chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, dust_hours))
    elif rank <= 25:
        dust_hours = 12
        relic_stones = base_relic_stones - 800
        rewards.append(chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, dust_hours))
    elif rank <= 50:
        dust_hours = 8
        relic_stones = base_relic_stones - 1000
        rewards.append(chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, dust_hours))
    elif rank <= 100:
        relic_stones = base_relic_stones - 1400
    else:
        rewards.append(chests.ChestReward(constants.RewardType.RELIC_STONES.value, 160))
        rewards.append(chests.ChestReward(constants.RewardType.GEMS.value, 200))

    rewards.append(chests.ChestReward(constants.RewardType.RELIC_STONES.value, relic_stones))

    return rewards


class GetClanSeasonRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        clan_season_reward = request.user.clanseasonreward

        return Response({'status': True,
                         'is_claimed': clan_season_reward.is_claimed,
                         'rank': clan_season_reward.rank,
                         'expiration_date': tier_system.get_season_expiration_date()})


class ClaimClanSeasonRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        season_reward = request.user.clanseasonreward
        if season_reward.is_claimed:
            return Response({'status': False, 'reason': 'clan season reward already claimed!'})

        rewards = get_clan_season_rewards(season_reward.rank)
        chests.award_chest_rewards(request.user, rewards)

        season_reward.is_claimed = True
        season_reward.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


@atomic()
def clan_season_cron():
    seasons = ClanSeasonReward.objects.select_related('user__userinfo', 'user__userinfo__clanmember').filter(user__userinfo__isnull=False)

    for season in seasons:
        if season.user.userinfo.clanmember.clan2 is not None:
            season.rank = leaderboards.get_clan_rank(season.user.userinfo.clanmember.clan2.name)
            season.is_claimed = False
        else:
            season.rank = -1
            season.is_claimed = True

    ClanSeasonReward.objects.bulk_update(seasons, ['rank', 'is_claimed'])
