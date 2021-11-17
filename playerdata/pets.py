from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import IntSerializer, StarterPetSerializer


def get_starter_pet_ids():
    return [0, 1, 2]  # Pigeon Cat Dog


class UpdatePetView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pet_id = serializer.validated_data['value']

        if pet_id not in request.user.inventory.pets_unlocked:
            return Response({'status': False, 'reason': "Pet not unlocked!"})

        request.user.inventory.active_pet_id = pet_id
        request.user.inventory.save()

        return Response({'status': True})


class UnlockPetView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pet_id = serializer.validated_data['value']

        if pet_id in request.user.inventory.pets_unlocked:
            return Response({'status': False, 'reason': 'Pet already unlocked!'})

        request.user.inventory.pets_unlocked.append(pet_id)
        request.user.inventory.pets_unlocked.sort()
        request.user.inventory.save()

        return Response({'status': True})


class UnlockStarterPetView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = StarterPetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pet_id = serializer.validated_data['pet_id']
        legacy_unlock = serializer.validated_data['legacy_unlock']

        starter_pet_ids = get_starter_pet_ids()  # Pigeon Cat Dog

        if pet_id not in starter_pet_ids:
            return Response({'status': False, 'reason': 'Invalid starter pet selection'})
        if legacy_unlock and 0 in request.user.inventory.pets_unlocked:
            request.user.inventory.pets_unlocked.remove(0)  # Clean up previous default pigeon unlock
        for id in starter_pet_ids:
            if id in request.user.inventory.pets_unlocked:
                return Response({'status': False, 'reason': 'Starter pet already claimed'})

        request.user.inventory.pets_unlocked.append(pet_id)
        request.user.inventory.pets_unlocked.sort()
        request.user.inventory.save()

        return Response({'status': True})
