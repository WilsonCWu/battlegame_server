from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .serializers import DailyDungeonStartSerializer, DailyDungeonResultSerializer
from .matcher import PlacementSchema
from .models import DailyDungeonStatus, Placement


def daily_dungeon_stage_generator(stage):
    # TODO: generate a proper dungeon stage - this currently just gets a random
    # placement.
    # NOTE: this should seed using the current date.
    return PlacementSchema(Placement.objects.first()).data


class DailyDungeonStartView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = DailyDungeonStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ensure that we don't currently have a daily dungeon run going on.
        # The user needs to end their current run first.
        dd_status_query = DailyDungeonStatus.objects.filter(user=request.user)
        dd_status = dd_status_query[0] if dd_status_query else None

        if dd_status and dd_status.is_active():
            return Response({'status': False, 'reason': 'Existing daily dungeon run.'})

        # Charge the user for their dungeon run.
        inventory = request.user.inventory
        if serializer.validated_data['is_golden']:
            if inventory.daily_dungeon_golden_ticket <= 0:
                return Response({'status': False, 'reason': 'Not enough golden tickets.'})

            inventory.daily_dungeon_golden_ticket -= 1
            inventory.save()
        else:
            if request.user.inventory.daily_dungeon_ticket <= 0:
                return Response({'status': False, 'reason': 'Not enough golden tickets.'})

            inventory.daily_dungeon_ticket -= 1
            inventory.save()

        # Create dungeon status.
        if dd_status:
            dd_status.stage = 1
            dd_status.is_golden = serializer.validated_data['is_golden']
            dd_status.character_state = serializer.validated_data['characters']
            dd_status.save()
        else:
            DailyDungeonStatus.objects.create(user=request.user,
                                              stage=1,
                                              is_golden=serializer.validated_data['is_golden'],
                                              character_state=serializer.validated_data['characters'])

        return Response({'status': True})


class DailyDungeonStatusSchema(Schema):
    is_golden = fields.Bool()
    stage = fields.Int()
    character_state = fields.Str()
 

class DailyDungeonStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # Return status of active dungeon run.
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if dd_status:
            return Response({'status': DailyDungeonStatusSchema(dd_status).data})

        # It is possible that we have uncollected rewards for the user.
        expired_dd_status = DailyDungeonStatus.get_expired_for_user(request.user)
        if expired_dd_status:
            resp = {
                'status': None,
                'previous_end': expired_dd_status.stage,
                'rewards': daily_dungeon_reward(expired_dd_status.is_golden,
                                                expired_dd_status.sstage)
            }
            # Mark it as collected by resetting it.
            expired_dd_status.stage = 0
            expired_dd_status.save()
            return Response(resp)

        return Response({'status': None})


class DailyDungeonStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dd_status = DailyDungeonStatus.get_active_for_user(request.user)
        if not dd_status:
            return Response({'status': False, 'reason': 'No active dungeon!'})

        return Response({'status': True, 'stage_id': dd_status.stage, 'mob': daily_dungeon_stage_generator(dd_status.user)})


def daily_dungeon_reward(is_golden, stage):
    # TODO: fill out!
    return {'coins': 100}


class DailyDungeonResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = DailyDungeonResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dd_status = DailyDungeonStatus.objects.get(user=request.user)
        if serializer.validated_data['is_loss']:
            last_stage = dd_status.stage
            dd_status.stage = 0
            dd_status.save()
            return Response({'status': True, 'rewards': daily_dungeon_reward(dd_status.is_golden, last_stage)})

        dd_status.stage += 1
        dd_status.save()
        return Response({'status': True})
