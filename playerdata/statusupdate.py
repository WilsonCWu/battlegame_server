from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UploadResultSerializer

from playerdata.models import Character


# r1, r2 ratings of player 1,2. s1 = 1 if win, 0 if loss, 0.5 for tie
def calculate_elo(r1, r2, s1):
    k = 50  # larger for more volatility
    R1 = 10 ** (r1 / 400)
    R2 = 10 ** (r2 / 400)
    E1 = R1 / (R1 + R2)
    new_r1 = r1 + k * (s1 - E1)
    return new_r1


class UploadResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UploadResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        win = serializer.validated_data['win'] == 'true'
        mode = serializer.validated_data['mode']
        opponent = serializer.validated_data['opponent']
        stats = serializer.validated_data['stats']

        # Update stats per hero
        for stat in stats:
            char_id = stat['id']
            hero = Character.objects.get(char_id)
            hero.total_damage_dealt += stat['damage_dealt']
            hero.total_damage_taken += stat['damage_taken']
            hero.total_health_healed += stat['health_healed']
            hero.save()

        response = {}

        if mode == 0:  # quickplay
            other_user = get_user_model().objects.select_related('userinfo').get(id=opponent)
            updated_rating = calculate_elo(request.user.userinfo.elo, other_user.userinfo.elo, win)
            response = {"rating": updated_rating}

        return Response(response)
