from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .serializers import DailyDungeonStartSerializer, DailyDungeonResultSerializer
from .models import DailyDungeonStatus


def daily_dungeon_stage_generator(stage):
    # TODO: generate a proper dungeon stage.
    pass


class DailyDungeonStartView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = DailyDungeonStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ensure that we don't currently have a daily dungeon run going on.
        # The user needs to end their current run first.
        dd_status_query = DailyDungeonStatus.objects.filter(user=request.user)
        dd_status = dd_status_query[0] if dd_status_query else None

        if dd_status and dd_status.stage != 0:
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

        # Return the 1st stage placement. TODO: wrap this in the placement
        # schema once in place.
        return Response({'status': True, 'placement': daily_dungeon_stage_generator(1)})


class DailyDungeonStatusSchema(Schema):
    is_golden = fields.Bool()
    stage = fields.Int()
    character_state = fields.Str()
 

class DailyDungeonStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # Return status of active dungeon run.
        query = DailyDungeonStatus.objects.filter(user=request.user, stage__gt=0)
        if query:
            return Response({'status': DailyDungeonStatusSchema(query[0]).data})
        else:
            return Response({'status': None})


def daily_dungeon_reward(is_golden, stage):
    return {'coins': 100}


class DailyDungeonResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = DailyDungeonResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dd_status = DailyDungeonStatus.objects.get(user=request.user)
        if serializer.validated_data['is_loss']:
            last_stage = dd_status.stage
            dd_status.stage = 0
            dd_status.save()
            return Response(daily_dungeon_reward(dd_status.is_golden, last_stage))

        dd_status.stage += 1
        dd_status.save()
        # TODO: wrap this in the placement schema once in place.
        return Response({'placement': daily_dungeon_stage_generator(dd_status.stage)})
