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
from playerdata import datagetter
from playerdata import matcher
from playerdata import statusupdate
from playerdata import purchases
from playerdata import social

urlpatterns = [
    path('friendrequest/accept/', social.AcceptFriendRequestView.as_view()),
    path('friendrequest/create/', social.CreateFriendRequestView.as_view()),
    path('friendrequest/get/', social.FriendRequestView.as_view()),
    path('getclan/', social.GetClanView.as_view()),
    path('newclan/', social.NewClanView.as_view()),
    path('friends/', social.FriendsView.as_view()),
    path('leaderboards/', social.GetLeaderboardView.as_view()),
    path('getchatid/', social.GetChatIdView.as_view()),
    path('purchaseitem/', purchases.PurchaseItemView.as_view()),
    path('purchase/', purchases.PurchaseView.as_view()),
    path('levelup/', datagetter.TryLevelView.as_view()),
    path('uploadresult/', statusupdate.UploadResultView.as_view()),
    path('opponents/', matcher.GetOpponentsView.as_view()),
    path('user/', matcher.GetUserView.as_view()),
    path('matcher/', matcher.MatcherView.as_view()),
    path('inventoryinfo/', datagetter.InventoryView.as_view()),
    path('baseinfo/', datagetter.BaseInfoView.as_view()),
    path('test/', login.HelloView.as_view()),
    path('login/', login.ObtainAuthToken.as_view()),
    path('createnewuser/', login.CreateNewUser.as_view()),
    path('chat/', include('chat.urls')),
    path('admin/', admin.site.urls),
]

