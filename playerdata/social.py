import random
import re

from better_profanity import profanity
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_404_NOT_FOUND,
)
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import server
from playerdata.models import Chat
from playerdata.models import Clan2
from playerdata.models import ClanMember
from playerdata.models import ClanRequest
from playerdata.models import Friend
from playerdata.models import FriendRequest
from . import constants, clan_pve
from .matcher import UserInfoSchema, LightUserInfoSchema
from .questupdater import QuestUpdater
from .serializers import AcceptFriendRequestSerializer
from .serializers import GetUserSerializer
from .serializers import NewClanSerializer
from .serializers import NullableValueSerializer
from .serializers import UpdateClanMemberStatusSerializer
from .serializers import UpdateClanRequestSerializer
from .serializers import ValueSerializer

MAX_DESCRIPTION_LENGTH = 96


def sortUsers(user1, user2):
    if user1.id < user2.id:
        return user1, user2
    return user2, user1


def getGlobalChats():
    global1 = {
        'chat_id': 1,
        'chat_name': 'Global'
    }
    feedback = {
        'chat_id': 2,
        'chat_name': 'Feedback'
    }

    return [global1, feedback]


def isTextSanitized(text, allowBackslash, allowNewline, allowNonAscii):  # TODO: Move to a helper class if one is made
    if((not allowBackslash) and re.search(r'\\', text)):
        return False
    if((not allowNewline) and re.search(r'\n|\r', text)):
        return False
    if((not allowNonAscii) and re.search(r'[^\x20-\x7E]+', text)):  # only printable ascii are allowed
        return False
    return True


class FriendSchema(Schema):
    user_1_id = fields.Int(attribute='user_1_id')
    user_2_id = fields.Int(attribute='user_2_id')
    light_user_1_info = fields.Nested(LightUserInfoSchema, attribute='user_1.userinfo')
    light_user_2_info = fields.Nested(LightUserInfoSchema, attribute='user_2.userinfo')
    chat_id = fields.Int(attribute='chat_id')


class FriendRequestSchema(Schema):
    request_id = fields.Int(attribute='id')
    userinfo = fields.Nested(LightUserInfoSchema, attribute='user.userinfo')
    user_id = fields.Int(attribute='user_id')
    target_id = fields.Int(attribute='target_id')


class ChatListSchema(Schema):
    chat_id = fields.Int(attribute='chat_id')
    chat_name = fields.Str(attribute='chat_name')


class FriendRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        requestQuery = FriendRequest.objects.filter(target=request.user).select_related('user__userinfo')
        requestSchema = FriendRequestSchema(requestQuery, many=True)

        return Response({'status': True, 'friend_requests': requestSchema.data})


class AcceptFriendRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = AcceptFriendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_fr_id = serializer.validated_data['target_id']
        accept = serializer.validated_data['accept']

        try:
            friend_request = FriendRequest.objects.get(id=target_fr_id)
        except FriendRequest.DoesNotExist:
            return Response({'status': False, 'reason': "friend request does not exist"})

        if friend_request.target != request.user:
            return Response({'status': False, 'reason': "friend request not for target user"})

        if not accept:
            friend_request.delete()
            return Response({'status': True})

        chat = Chat.objects.create()
        friend = Friend.objects.create(user_1=friend_request.user, user_2=friend_request.target, chat=chat)

        friend_request.delete()

        QuestUpdater.add_progress_by_type(request.user, constants.MAKE_A_FRIEND, 1)
        QuestUpdater.add_progress_by_type(friend_request.user, constants.MAKE_A_FRIEND, 1)

        return Response({'status': True})


class CreateFriendRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['value']

        if not target_user_id.isnumeric():
            return Response({'status': False, 'reason': "user id should be numeric"})

        target_user = get_user_model().objects.filter(id=target_user_id).first()
        if target_user is None:
            return Response({'status': False, 'reason': "user id doesn't exist"})

        request_set1 = FriendRequest.objects.filter(user=request.user, target=target_user)
        request_set2 = FriendRequest.objects.filter(user=target_user, target=request.user)
        request_set = request_set1 | request_set2

        if request_set:
            return Response({'status': False, 'reason': "friend request already exists"})

        friends1 = Friend.objects.filter(user_1=request.user, user_2=target_user)
        friends2 = Friend.objects.filter(user_1=target_user, user_2=request.user)
        friends_set = friends1 | friends2
        if friends_set:
            return Response({'status': False, 'reason': "you are already friends"})

        FriendRequest.objects.create(user=request.user, target=target_user)

        return Response({'status': True})


class DeleteFriendView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['value']

        target_user = get_user_model().objects.get(id=target_user_id)

        query1 = Friend.objects.filter(user_1=request.user, user_2=target_user)
        query2 = Friend.objects.filter(user_2=request.user, user_1=target_user)
        query = query1 | query2

        for friend in query:
            chat = friend.chat
            if chat:
                chat.delete()

        query.delete()
        return Response({'status': True})


class FriendsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query1 = Friend.objects.filter(user_1=request.user).select_related(
            'user_1__userinfo__clanmember').select_related('user_2__userinfo__clanmember')
        query2 = Friend.objects.filter(user_2=request.user).select_related(
            'user_1__userinfo__clanmember').select_related('user_2__userinfo__clanmember')
        query = query1 | query2
        friends = FriendSchema(query, many=True)

        return Response({'status': True, 'friends': friends.data})


class GetChatIdView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = GetUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['target_user']
        target_user = get_user_model().objects.get(id=target_user_id)

        user1, user2 = sortUsers(request.user, target_user)

        friendSet = Friend.objects.filter(user_1=user1, user_2=user2)
        if not friendSet:
            return Response(
                {'status': False, 'detail': 'Friend set with ' + str(user1.id) + ' and ' + str(user2.id) + ' does not exist'},
                status=HTTP_404_NOT_FOUND)

        friendObject = friendSet[0]

        if not friendObject.chat:
            chat = Chat.objects.create(chat_name='dm')
            friendObject.chat = chat
            friendObject.save()

        return Response({'status': True, 'chat_id': friendObject.chat.id})


class GetAllChatsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query1 = Friend.objects.filter(user_1=request.user).select_related(
            'user_2__userinfo')
        query2 = Friend.objects.filter(user_2=request.user).select_related(
            'user_1__userinfo')

        chat_list = []
        chat_list.extend(getGlobalChats())

        for friend_query in query1:
            # TODO: temp until we fix chat
            if '(Titan)' not in friend_query.user_2.userinfo.name:
                continue
            friend_chat = {
                'chat_id': friend_query.chat.id,
                'chat_name': friend_query.user_2.userinfo.name
            }
            chat_list.append(friend_chat)

        for friend_query in query2:
            # TODO: temp until we fix chat
            if '(Titan)' not in friend_query.user_1.userinfo.name:
                continue
            friend_chat = {
                'chat_id': friend_query.chat.id,
                'chat_name': friend_query.user_1.userinfo.name
            }
            chat_list.append(friend_chat)

        # Get clan chat
        clan_member = ClanMember.objects.filter(userinfo=request.user.userinfo).select_related('clan2__chat').first()
        if clan_member.clan2:
            clan_chat = {
                'chat_id': clan_member.clan2.chat.id,
                'chat_name': clan_member.clan2.name
            }
            chat_list.append(clan_chat)

        chat_list_schema = ChatListSchema(many=True)
        return Response({'status': True, 'chats': chat_list_schema.dump(chat_list)})


class GetClanSearchResultsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = NullableValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        search_name = serializer.validated_data['value']

        if not search_name:
            clan_query = Clan2.objects.filter(num_members__gte=15, num_members__lte=29)
            num_shown = min(20, clan_query.count())
            clan_set = random.sample(list(clan_query), num_shown)
        else:
            clan_set = Clan2.objects.filter(name__icontains=search_name)

        clans = ClanSchema(clan_set, many=True)
        return Response({'status': True, 'clans': clans.data})


class NewClanView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = NewClanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clan_name = serializer.validated_data['clan_name']
        clan_description = serializer.validated_data['clan_description']

        if Clan2.objects.filter(name=clan_name):  # if exists already
            return Response({'status': False, 'reason': 'Clan name ' + clan_name + ' already taken!'})

        if profanity.contains_profanity(clan_name) or profanity.contains_profanity(clan_description):
            return Response({'status': False, 'reason': 'Invalid text contains profanity'})

        clan_chat = Chat.objects.create(chat_name=clan_name)

        clan2 = Clan2.objects.create(name=clan_name, chat=clan_chat,
                                     description=clan_description,
                                     num_members=1)

        clan_owner = request.user.userinfo.clanmember
        clan_owner.clan2 = clan2
        clan_owner.is_admin = True
        clan_owner.is_owner = True
        clan_owner.is_elder = True
        clan_owner.save()

        return Response({'status': True})


class LeaveClanView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        clan_member = request.user.userinfo.clanmember

        if clan_member.is_owner:
            return Response({'status': False, 'reason': 'cannot leave clan without transferring ownership!'})

        clan_member.clan2.num_members -= 1
        clan_member.clan2.save()

        clan_member.clan2 = None
        clan_member.is_admin = False
        clan_member.is_owner = False
        clan_member.save()

        return Response({'status': True})


class DeleteClanView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        clan_member = request.user.userinfo.clanmember
        clan_name = clan_member.clan2.name
        if not clan_member.is_owner:
            return Response({'status': False, 'reason': 'invalid clan permissions'})

        clan = Clan2.objects.filter(name=clan_name).prefetch_related(Prefetch(
            'clanmember_set', to_attr='clan_members',
            queryset=ClanMember.objects.select_related('userinfo'))).first()

        clanmembers = clan.clan_members

        for member in clanmembers:
            member.is_elder = False
            member.is_admin = False
            member.is_owner = False

        ClanMember.objects.bulk_update(clanmembers, ['is_elder', 'is_admin', 'is_owner'])
        clan.delete()

        return Response({'status': True})


class ClanMemberSchema(Schema):
    userinfo = fields.Nested(UserInfoSchema, exclude=('default_placement',))
    clan_id = fields.Function(lambda clanmember: clanmember.clan2.name if clanmember.clan2 else '')
    is_admin = fields.Bool()
    is_owner = fields.Bool()
    is_elder = fields.Bool()
    pve_character_lending = fields.List(fields.Int())


class ClanSchema(Schema):
    name = fields.Str()
    description = fields.Str()
    chat_id = fields.Int()
    num_members = fields.Int()
    profile_picture = fields.Int()
    time_started = fields.DateTime()
    elo = fields.Int()
    exp = fields.Int()
    cap = fields.Int()
    clan_members = fields.Nested(ClanMemberSchema, attribute='clan_members', many=True)

    clan_level = fields.Method("get_clan_lvl")

    def get_clan_lvl(self, clan):
        return clan_pve.clan_exp_to_level(clan.exp)


class GetClanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clan_name = serializer.validated_data['value']
        clan_query = Clan2.objects.filter(name=clan_name).prefetch_related(Prefetch(
            'clanmember_set', to_attr='clan_members',
            queryset=ClanMember.objects.select_related('userinfo').order_by('-userinfo__elo')))

        if not clan_query:
            return Response({'status': False})

        clan_schema = ClanSchema(clan_query[0])
        return Response({'status': True, 'clan': clan_schema.data})


class GetClanMember(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        clanmember = ClanMember.objects.get(userinfo=request.user.userinfo)
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'clan_member': ClanMemberSchema(clanmember).data})
        return Response(ClanMemberSchema(clanmember).data)


class EditClanDescriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_description = serializer.validated_data['value']

        clanmember = request.user.userinfo.clanmember

        if not clanmember.clan2 or not clanmember.is_admin:
            return Response({'status': False, 'reason': 'invalid clan permissions'})

        if len(new_description) > MAX_DESCRIPTION_LENGTH:
            return Response({'status': False, 'reason': 'description too long'})

        if not isTextSanitized(new_description, False, False, True):  # No backslash, returns, or newlines
            return Response({'status': False, 'reason': 'description contains invalid characters'})

        if profanity.contains_profanity(new_description):
            return Response({'status': False, 'reason': 'invalid text contains profanity'})

        clan2 = clanmember.clan2
        clan2.description = new_description
        clan2.save()

        return Response({'status': True})


class EditProfileDescriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_description = serializer.validated_data['value']

        if len(new_description) > MAX_DESCRIPTION_LENGTH:
            return Response({'status': False, 'reason': 'description too long'})

        if not isTextSanitized(new_description, False, False, True):  # No backslash, returns, or newlines
            return Response({'status': False, 'reason': 'description contains invalid characters'})

        if profanity.contains_profanity(new_description):
            return Response({'status': False, 'reason': 'invalid text contains profanity'})

        request.user.userinfo.description = new_description
        request.user.userinfo.save()

        return Response({'status': True})


class ChangeMemberStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = UpdateClanMemberStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member_id = serializer.validated_data['member_id']
        member_status = serializer.validated_data['member_status']

        target_clanmember = ClanMember.objects.get(userinfo_id=member_id)
        clanmember = request.user.userinfo.clanmember

        if member_id == request.user.id:
            return Response({'status': False, 'reason': 'cannot ' + member_status + ' yourself'})

        if not (
                clanmember.clan2 and
                clanmember.is_admin and
                clanmember.clan2 == target_clanmember.clan2 and
                not target_clanmember.is_owner):
            return Response({'status': False, 'reason': 'invalid clan permissions'})

        if member_status == 'promote':
            if target_clanmember.is_elder:
                target_clanmember.is_admin = True
            target_clanmember.is_elder = True
        elif member_status == 'demote':
            if not target_clanmember.is_admin:
                target_clanmember.is_elder = False

            target_clanmember.is_admin = False
        elif member_status == 'kick':
            clan2 = target_clanmember.clan2
            target_clanmember.clan2 = None

            clan2.num_members -= 1
            clan2.save()
        elif member_status == 'transfer' and clanmember.is_owner and target_clanmember.is_admin:
            clanmember.is_owner = False
            target_clanmember.is_owner = True
            clanmember.save()
        else:
            return Response({'status': False, 'reason': 'member status ' + member_status + 'invalid.'})

        target_clanmember.save()

        return Response({'status': True})


class ClanRequestSchema(Schema):
    request_id = fields.Int(attribute='id')
    userinfo = fields.Nested(LightUserInfoSchema)
    # NOTE: don't need a null check on this since this clan2 will never be null.
    clan_id = fields.Str(attribute='clan2.name')


class CreateClanRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_clan_id = serializer.validated_data['value']
        # TODO: this in the future should be an ID instead of a name, but to
        # keep the transition simple, we'll leave it as name for now.
        target_clan_query = Clan2.objects.filter(name=target_clan_id)
        if not target_clan_query:
            return Response({'status': False, 'reason': 'Clan does not exist.'})
        target_clan = target_clan_query[0]

        userinfo = request.user.userinfo

        if userinfo.clanmember.clan2:
            return Response({'status': False, 'reason': 'User already part of a clan.'})

        if ClanRequest.objects.filter(userinfo=userinfo, clan2=target_clan).exists():
            return Response({'status': False, 'reason': 'Clan request already exists.'})

        QuestUpdater.add_progress_by_type(request.user, constants.JOIN_GUILD, 1)
        ClanRequest.objects.create(userinfo=userinfo, clan2=target_clan)
        return Response({'status': True})


class GetClanRequestsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        clanmember = request.user.userinfo.clanmember

        if not clanmember.clan2 or not clanmember.is_elder:
            return Response({'status': False, 'reason': 'invalid clan permissions'})

        requestSet = ClanRequest.objects.filter(clan2=clanmember.clan2)
        requests = ClanRequestSchema(requestSet, many=True)

        return Response({'status': True, 'requests': requests.data})


class UpdateClanRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = UpdateClanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['target_user_id']
        accept = serializer.validated_data['accept']

        clanmember = request.user.userinfo.clanmember
        clan2 = clanmember.clan2
        if not clan2 or not clanmember.is_elder:
            return Response({'status': False, 'reason': 'invalid clan permissions'})

        target_clanmember = ClanMember.objects.get(userinfo_id=target_user_id)

        if target_clanmember.clan2:
            ClanRequest.objects.filter(userinfo=target_clanmember.userinfo).delete()
            return Response({'status': True, 'reason': 'already in clan ' + target_clanmember.clan2.name})

        if not accept:
            ClanRequest.objects.filter(userinfo=target_clanmember.userinfo, clan2=clan2).delete()
            return Response({'status': True})

        # TODO: petition to just use a clanmember query to track this instead
        # of updating it everywhere in the model.
        if clan2.num_members + 1 > clan2.cap:
            return Response({'status': False, 'reason': 'clan is full, max capacity reached'})

        target_clanmember.clan2 = clanmember.clan2
        target_clanmember.is_admin = False
        target_clanmember.is_owner = False
        target_clanmember.is_elder = False
        target_clanmember.save()

        clan2.num_members += 1
        clan2.save()

        QuestUpdater.add_progress_by_type(target_clanmember.userinfo.user, constants.JOIN_GUILD, 1)
        ClanRequest.objects.filter(userinfo=target_clanmember.userinfo).delete()

        return Response({'status': True})


class UpdateProfilePictureView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile_picture = serializer.validated_data['value']

        request.user.userinfo.profile_picture = profile_picture
        request.user.userinfo.save()

        return Response({'status': True})


class UpdateClanProfilePictureView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile_picture = serializer.validated_data['value']

        clanmember = request.user.userinfo.clanmember
        clan2 = clanmember.clan2
        if not clan2 or not clanmember.is_admin:
            return Response({'status': False, 'reason': 'invalid clan permissions'})

        clan2.profile_picture = profile_picture
        clan2.save()
        return Response({'status': True})
