"""battlegame URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include
from django.contrib import admin
from django.urls import path
from playerdata import login
from playerdata import base
from playerdata import matcher
from playerdata import statusupdate
from playerdata import purchases
from playerdata import social
from playerdata import dungeon
from playerdata import quest
from playerdata import redemptioncodes
from playerdata import referral
from playerdata import tournament
from playerdata import inventory
from playerdata import legal
from playerdata import server

urlpatterns = [
    path('tournament/matchhistory', tournament.TournamentMatchHistory.as_view()),
    path('tournament/self', tournament.TournamentSelfView.as_view()),
    path('tournament/getfights', tournament.TournamentFightsView.as_view()),
    path('tournament/setdefense', tournament.SetDefense.as_view()),
    path('tournament/selectcards', tournament.SelectCardsView.as_view()),
    path('tournament/getcards', tournament.GetCardsView.as_view()),
    path('tournament/register', tournament.TournamentRegView.as_view()),
    path('tournament/get', tournament.TournamentView.as_view()),
    path('referral', referral.ReferralView.as_view()),
    path('redeemcode', redemptioncodes.RedeemCodeView.as_view()),
    path('quest/get', quest.QuestView.as_view()),
    path('quest/claim/cumulative', quest.ClaimQuestCumulativeView.as_view()),
    path('quest/claim/weekly', quest.ClaimQuestWeeklyView.as_view()),
    path('quest/claim/daily', quest.ClaimQuestDailyView.as_view()),
    path('quest/discord', quest.CompleteDiscordView.as_view()),
    path('quest/linkaccount', quest.LinkAccountView.as_view()),
    path('friendrequest/accept/', social.AcceptFriendRequestView.as_view()),
    path('profilepicture/update/', social.UpdateProfilePictureView.as_view()),
    path('friendrequest/create/', social.CreateFriendRequestView.as_view()),
    path('friendrequest/get/', social.FriendRequestView.as_view()),
    path('clan/search/', social.GetClanSearchResultsView.as_view()),
    path('clan/get/', social.GetClanView.as_view()),
    path('clan/editdescription/', social.EditClanDescriptionView.as_view()),
    path('clan/members/updatestatus/', social.ChangeMemberStatusView.as_view()),
    path('clan/new/', social.NewClanView.as_view()),
    path('clan/requests/get/', social.GetClanRequestsView.as_view()),
    path('clan/requests/update/', social.UpdateClanRequestView.as_view()),
    path('clan/requests/create/', social.CreateClanRequestView.as_view()),
    path('clan/profilepicture/update/', social.UpdateClanProfilePictureView.as_view()),
    path('friends/delete/', social.DeleteFriendView.as_view()),
    path('friends/get/', social.FriendsView.as_view()),
    path('leaderboards/', social.GetLeaderboardView.as_view()),
    path('getchatid/', social.GetChatIdView.as_view()),
    path('getallchats/', social.GetAllChatsView.as_view()),
    path('validate/', purchases.ValidateView.as_view()),
    path('purchaseitem/', purchases.PurchaseItemView.as_view()),
    path('purchase/', purchases.PurchaseView.as_view()),
    path('levelup/', inventory.TryLevelView.as_view()),
    path('uploadresult/', statusupdate.UploadResultView.as_view()),
    path('opponents/', matcher.GetOpponentsView.as_view()),
    path('user/', matcher.GetUserView.as_view()),
    path('matcher/', matcher.MatcherView.as_view()),
    path('placements/', matcher.PlacementsView.as_view()),
    path('inventoryinfo/', inventory.InventoryView.as_view()),
    path('inventoryheader/', inventory.InventoryHeaderView.as_view()),
    path('inventory/equipitem/', inventory.EquipItemView.as_view()),
    path('inventory/unequipitem/', inventory.UnequipItemView.as_view()),
    path('baseinfo/', base.BaseInfoView.as_view()),
    path('test/', login.HelloView.as_view()),
    path('login/', login.ObtainAuthToken.as_view()),
    path('createnewuser/', login.CreateNewUser.as_view()),
    path('changename/', login.ChangeName.as_view()),
    path('dungeon/stage', dungeon.DungeonStageView.as_view()),
    path('dungeon/setprogress', dungeon.DungeonSetProgressView.as_view()),
    path('status/', server.ServerStatusView.as_view()),
    path('privacy/', legal.privacy),
    path('terms/', legal.terms),
    path('chat/', include('chat.urls')),
    path('admin/', admin.site.urls),
    path('', legal.install),
]
