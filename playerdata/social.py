from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_200_OK,
)
from django.contrib.auth import authenticate
from django.http import JsonResponse

from rest_marshmallow import Schema, fields
from django.db.models import Prefetch
from django.contrib.auth import get_user_model
from playerdata.models import Friend
from playerdata.models import FriendRequest
from playerdata.models import Chat
from playerdata.models import UserInfo
from playerdata.models import Clan
from playerdata.models import ClanMember
from .matcher import UserInfoSchema
from .serializers import GetUserSerializer
from .serializers import ValueSerializer
from .serializers import NewClanSerializer

def sortUsers(user1, user2):
    if user1.id < user2.id:
        return user1, user2
    return user2, user1

class FriendSchema(Schema):
    user_1_id = fields.Int(attribute='user_1_id')
    user_2_id = fields.Int(attribute='user_2_id')
    user_1_info = fields.Nested(UserInfoSchema, attribute='user_1.userinfo', exclude=('default_placement','team',))
    user_2_info = fields.Nested(UserInfoSchema, attribute='user_2.userinfo', exclude=('default_placement','team',))
    chat_id = fields.Int(attribute='chat_id')

class FriendRequestSchema(Schema):
    request_id = fields.Int(attribute='id')
    userinfo = fields.Nested(UserInfoSchema, attribute='user.userinfo')
    user_id = fields.Int(attribute='user_id')
    target_id = fields.Int(attribute='target_id')

class FriendRequestView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        requestQuery = FriendRequest.objects.filter(target=request.user).select_related('user__userinfo')
        requestSchema = FriendRequestSchema(requestQuery, many=True)

        return Response({'friend_requests':requestSchema.data})

class CreateFriendRequestView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['value']
        
        target_user = get_user_model().objects.get(id=target_user_id)

        oldRequestSet1 = FriendRequest.objects.filter(user=request.user, target=target_user)
        oldRequestSet2 = FriendRequest.objects.filter(user=target_user, target=request.user)
        oldRequestSet = oldRequestSet1 | oldRequestSet2

        if oldRequestSet:
            return Response({'status':False, 'reason':"friend request already exists"})    

        FriendRequest.objects.create(user=request.user, target=target_user)

        return Response({'status':True})

class FriendsView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query1 = Friend.objects.filter(user_1=request.user).select_related('user_1__userinfo__clanmember').select_related('user_2__userinfo__clanmember')
        query2 = Friend.objects.filter(user_2=request.user).select_related('user_1__userinfo__clanmember').select_related('user_2__userinfo__clanmember')
        query = query1 | query2
        friends = FriendSchema(query, many=True)
        return Response({'friends':friends.data})

class GetChatIdView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['target_user']
        target_user = get_user_model().objects.get(id=target_user_id)        
    
        user1, user2 = sortUsers(request.user, target_user)
        
        friendSet = Friend.objects.filter(user_1=user1, user_2=user2)
        if not friendSet:
            return Response({'detail': 'Friend set with ' + str(user_1.id) + ' and ' + str(user_2.id) + ' does not exist'}, status=HTTP_404_NOT_FOUND)

        friendObject = friendSet[0]

        if not friendObject.chat:
            chat = Chat.objects.create(chat_name='dm')
            friendObject.chat = chat
            friendObject.save()

        return Response({'chat_id':friendObject.chat.id})

    
class GetLeaderboardView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leaderboard_type = serializer.validated_data['value']
        
        if leaderboard_type == 'solo_top_100':
            top_player_set = UserInfo.objects.all().order_by('-elo')[:100]
            players = UserInfoSchema(top_player_set, many=True, exclude=('default_placement','team',))
            return Response({'players':players.data})
        else:
            return Response({'detail': 'leaderboard ' + leaderboard_type + ' does not exist'}, status=HTTP_404_NOT_FOUND)

class NewClanView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = NewClanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clan_name = serializer.validated_data['clan_name']
        clan_description = serializer.validated_data['clan_description']

        if Clan.objects.filter(name=clan_name): # if exists already
            return Response({'status': False, 'detail': 'clan name ' + clan_name + ' already taken'}, status=HTTP_404_NOT_FOUND) 

        clan_chat = Chat.objects.create(chat_name=clan_name)
        
        if clan_description:
            clan = Clan.objects.create(name=clan_name, chat = clan_chat, description=clan_description)
        else:
            clan = Clan.objects.create(name=clan_name, chat = clan_chat)
        
        clan_owner = request.user.userinfo.clanmember
        clan_owner.clan = clan
        clan_owner.is_admin=True
        clan_owner.is_owner=True
        clan_owner.save()

        return Response({'status': True})

class ClanMemberSchema(Schema):
    userinfo = fields.Nested(UserInfoSchema, exclude=('default_placement','team',))
    clan_id = fields.Str()
    is_admin = fields.Bool()
    is_owner = fields.Bool() 

class ClanSchema(Schema):
    name = fields.Str()
    description = fields.Str()
    chat_id = fields.Int()
    time_started = fields.DateTime()
    elo = fields.Int()
    clan_members = fields.Nested(ClanMemberSchema, attribute='clan_members', many=True)

class GetClanView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clanName = serializer.validated_data['value']
        clanQuery = Clan.objects.filter(name=clanName).prefetch_related(Prefetch(\
            'clanmember_set', to_attr='clan_members', queryset=ClanMember.objects.select_related('userinfo').order_by('-userinfo__elo')))   
        
        if not clanQuery:
            return Response({'status':False})

        clanSchema = ClanSchema(clanQuery[0])
        return Response({'status':True, 'clan':clanSchema.data})
