from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import chests
from .models import MoevasionStatus
from .serializers import MoevasionResultSerializer


class StartView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        status, _ = MoevasionStatus.objects.get_or_create(user=request.user)
        if not status.is_active():
            status.start()
            status.save()
        return Response({'status': True})


class EndView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': False, 'reason': 'No existing run.'})

        if not status.is_active():
            return Response({'status': False, 'reason': 'No existing run.'})

        status.end()
        status.save()
        return Response({'status': True})


class StageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': False, 'reason': 'No existing run.'})

        if not status.is_active():
            return Response({'status': False, 'reason': 'No existing run.'})

        # TODO: add in actual stage. This probably can just be hard coded
        # here.
        return Response({'status': True, 'stage_id': status.stage,
                         'stage': None})


class StatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': True, 'stage_id': 0})

        return Response({'status': True, 'stage_id': status.stage,
                         'characters': status.character_state,
                         'damage': status.damage})

    
class ResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = MoevasionResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': False, 'reason': 'No existing run.'})

        is_loss = serializer.validated_data['is_loss']
        prev_stage = status.stage
        if is_loss:
            status.end()
        else:
            status.stage += 1

        status.damage += serializer.validated_data['damage']
        status.character_state = serializer.validated_data['characters']
        status.save()

        userinfo = request.user.userinfo
        if userinfo.best_moevasion_stage < status.damage:
            userinfo.best_moevasion_stage = status.damage

        rewards = []
        # either have to beat the stage for the first time to collect
        # or it's stage 10 and haven't collected rewards yet
        if (prev_stage > userinfo.highest_moevasion_reward_collected and not is_loss) or\
                (prev_stage == 10 and userinfo.highest_moevasion_reward_collected < 10):
            # add rewards
            if prev_stage == 5:
                rewards.append(chests.ChestReward('gems', 492))
                rewards.append(chests.ChestReward('char_id', 1))  # award a Moe
            elif prev_stage == 10:
                rewards.append(chests.ChestReward('gems', 2699))
                rewards.append(chests.ChestReward('char_id', 1))  # award a Moe
            else:
                rewards.append(chests.ChestReward('gems', 1))

            userinfo.highest_moevasion_reward_collected = prev_stage

        userinfo.save()

        chests.award_chest_rewards(request.user, rewards)
        reward_schema = chests.ChestRewardSchema(rewards, many=True)

        return Response({'status': True, 'rewards': reward_schema.data})
