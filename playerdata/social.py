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
from playerdata.models import ClanRequest
from .matcher import UserInfoSchema
from .serializers import GetUserSerializer
from .serializers import ValueSerializer
from .serializers import NullableValueSerializer
from .serializers import NewClanSerializer
from .serializers import AcceptFriendRequestSerializer
from .serializers import UpdateClanMemberStatusSerializer
from .serializers import UpdateClanRequestSerializer

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


class AcceptFriendRequestView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = AcceptFriendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_fr_id = serializer.validated_data['target_id']
        accept = serializer.validated_data['accept']

        friend_request = FriendRequest.objects.get(id=target_fr_id)

        if friend_request.target != request.user:
            return Response({'status':False, 'reason':"friend request not for target user"})

        if not accept:
            friend_request.delete()
            return Response({'status':True})
        
        chat = Chat.objects.create()
        friend = Friend.objects.create(user_1=friend_request.user, user_2=friend_request.target, chat=chat)
        
        friend_request.delete()

        return Response({'status':True})

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

class DeleteFriendView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['value']
        
        target_user = get_user_model().objects.get(id=target_user_id)

        query1 = Friend.objects.filter(user_1=request.user, user_2 = target_user)
        query2 = Friend.objects.filter(user_2=request.user, user_1 = target_user)
        query = query1 | query2

        chat = query[0].chat
        if chat:
            chat.delete()

        query.delete()
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
        if leaderboard_type == 'clan_top_100':
            top_clan_set = Clan.objects.all().order_by('-elo')[:100]
            clans = ClanSchema(top_clan_set, many=True)
            return Response({'clans':clans.data})
        else:
            return Response({'detail': 'leaderboard ' + leaderboard_type + ' does not exist'}, status=HTTP_404_NOT_FOUND)

class GetClanSearchResultsView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = NullableValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        search_name = serializer.validated_data['value']
        
        if not search_name:
            clan_set = Clan.objects.filter(num_members__lte=29)[:10]
            clans = ClanSchema(clan_set, many=True)
            return Response({'clans':clans.data})
        else:    
            clan_set = Clan.objects.filter(name=search_name)
            clans = ClanSchema(clan_set, many=True)
            return Response({'clans':clans.data})

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
    num_members = fields.Int()
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

class EditClanDescriptionView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_description = serializer.validated_data['value']
        
        clanmember = request.user.userinfo.clanmember
        
        if not clanmember.clan or not clanmember.is_admin:
            return Response({'status':False, 'reason':'invalid clan permissions'})

        clan = clanmember.clan

        clan.description = new_description
        clan.save()

        return Response({'status':True})
        
class ChangeMemberStatusView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = UpdateClanMemberStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member_id = serializer.validated_data['member_id']
        member_status = serializer.validated_data['member_status']
    
        target_clanmember = ClanMember.objects.get(userinfo_id=member_id)
        clanmember = request.user.userinfo.clanmember
        
        if not (clanmember.clan and clanmember.is_admin and clanmember.clan == target_clanmember.clan and not target_clanmember.is_owner):
            return Response({'status':False, 'reason':'invalid clan permissions'})

        if member_status == 'promote':
            target_clanmember.is_admin = true
        elif member_status == 'demote':
            target_clanmember.is_admin = false
        elif member_status == 'kick':
            clan = target_clanmember.clan
            target_clanmember.clan = None
            clan.num_members -= 1
            clan.save()
        else:
            return Response({'status':False, 'reason':'member status ' + member_status + 'invalid.'})

        target_clanmember.save()

        return Response({'status':True})

class ClanRequestSchema(Schema):
    request_id = fields.Int(attribute='id')
    userinfo = fields.Nested(UserInfoSchema, exclude=('default_placement','team',))
    clan_id = fields.Str()

class CreateClanRequestView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_clan_id = serializer.validated_data['value']
        target_clan = Clan.objects.get(name=target_clan_id)

        userinfo = request.user.userinfo

        if userinfo.clanmember.clan or ClanRequest.objects.filter(clan=target_clan, userinfo=userinfo):
            return Response({'status':False, 'reason':'Clan request already exists'})

        ClanRequest.objects.create(userinfo=userinfo, clan=target_clan)

        return Response({'status':True})

class GetClanRequestsView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        
        clanmember = request.user.userinfo.clanmember
        
        if not clanmember.clan or not clanmember.is_admin:
            return Response({'status':False, 'reason':'invalid clan permissions'})
        
        requestSet = ClanRequest.objects.filter(clan=clanmember.clan)
        requests = ClanRequestSchema(requestSet, many=True)

        return Response({'requests':requests.data})

class UpdateClanRequestView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        
        serializer = UpdateClanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['target_user_id']
        accept = serializer.validated_data['accept']
        
        clanmember = request.user.userinfo.clanmember
        clan = clanmember.clan
        if not clan or not clanmember.is_admin:
            return Response({'status':False, 'reason':'invalid clan permissions'})
        
        target_clanmember = ClanMember.objects.get(userinfo_id=target_user_id)

        if target_clanmember.clan:
            ClanRequest.objects.filter(userinfo=target_clanmember.userinfo).delete()
            return Response({'status':True, 'reason':'already in clan ' + target_clanmember.clan.name})
        
        if not accept:
            ClanRequest.objects.get(userinfo=target_clanmember.userinfo, clan=clan).delete()
            return Response({'status':True})
        
        target_clanmember.clan = clan
        target_clanmember.is_admin = False
        target_clanmember.is_owner = False
        target_clanmember.save()

        clan.num_members+=1
        clan.save()

        ClanRequest.objects.filter(userinfo=target_clanmember.userinfo).delete()

        return Response({'status':True})
