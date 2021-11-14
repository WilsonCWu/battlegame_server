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
from playerdata import creatorcode, event_times, login, tier_system, level_booster, relic_shop, wishlist, \
    chapter_rewards_pack, inbox, \
    rotating_mode, conquest_event, regal_rewards, activity_points, shards, grass_event
from playerdata import base
from playerdata import daily_dungeon
from playerdata import moevasion
from playerdata import matcher
from playerdata import statusupdate
from playerdata import purchases
from playerdata import social
from playerdata import dungeon
from playerdata import quest
from playerdata import redemptioncodes
from playerdata import referral
from playerdata import tournament
from playerdata import afk_rewards
from playerdata import inventory
from playerdata import web_pages
from playerdata import server
from playerdata import coin_shop
from playerdata import chests
from playerdata import public
from playerdata import antihacking
from playerdata import clan_pve
from playerdata import clan_farm
from playerdata import story_mode
from playerdata import pvp_queue
from playerdata import event_rewards

urlpatterns = [
    path('shards/summons/', shards.SummonShardsView.as_view()),
    path('activitypoints/claim/', activity_points.ClaimActivityPointsView.as_view()),
    path('event/grass/get/', grass_event.GetGrassEventView.as_view()),
    path('event/grass/startrun/', grass_event.StartGrassRunView.as_view()),
    path('event/grass/finishrun/', grass_event.FinishGrassRunView.as_view()),
    path('event/grass/cutgrass/', grass_event.CutGrassView.as_view()),
    path('event/grass/buytoken/', grass_event.BuyGrassTokenView.as_view()),
    path('event/conquest/claim/', conquest_event.ClaimConquestEventRewardView.as_view()),
    path('rotating/claim/', rotating_mode.ClaimRotatingModeRewardView.as_view()),
    path('rotating/result/', rotating_mode.RotatingModeResultView.as_view()),
    path('rotating/stage/', rotating_mode.RotatingModeStageView.as_view()),
    path('rotating/get/', rotating_mode.RotatingModeStatusView.as_view()),
    path('inbox/delete/', inbox.DeleteMailView.as_view()),
    path('inbox/claim/', inbox.ClaimMailView.as_view()),
    path('inbox/send/', inbox.SendInboxView.as_view()),
    path('inbox/read/', inbox.ReadInboxView.as_view()),
    path('inbox/get/', inbox.GetInboxView.as_view()),
    path('storymode/buffs/set/', story_mode.LevelBuffView.as_view()),
    path('storymode/boons/set/', story_mode.ChooseBoonView.as_view()),
    path('storymode/boons/get/', story_mode.GetBoonsView.as_view()),
    path('storymode/get/', story_mode.GetStoryModeView.as_view()),
    path('storymode/start/', story_mode.StartNewStoryView.as_view()),
    path('storymode/result/', story_mode.StoryResultView.as_view()),
    path('regalrewards/claim/', regal_rewards.ClaimRegalRewardView.as_view()),
    path('regalrewards/get/', regal_rewards.GetRegalRewardListView.as_view()),
    path('chapterrewardspack/claim/', chapter_rewards_pack.ClaimChapterRewardView.as_view()),
    path('chapterrewardspack/get/', chapter_rewards_pack.GetChapterRewardListView.as_view()),
    path('wishlist/get/', wishlist.GetWishlistView.as_view()),
    path('wishlist/set/', wishlist.SetWishlistSlotView.as_view()),
    path('clanfarm/status/', clan_farm.ClanFarmingStatus.as_view()),
    path('clanfarm/farm/', clan_farm.ClanFarmingFarm.as_view()),
    path('clanfarm/claim/', clan_farm.ClanFarmingClaim.as_view()),
    path('relicshop/buy/', relic_shop.BuyRelicView.as_view()),
    path('relicshop/get/', relic_shop.GetRelicShopView.as_view()),
    path('clanpve/start/', clan_pve.ClanPVEStartView.as_view()),
    path('clanpve/startevent/', clan_pve.ClanPVEStartEventView.as_view()),
    path('clanpve/status/', clan_pve.ClanPVEStatusView.as_view()),
    path('clanpve/result/', clan_pve.ClanPVEResultView.as_view()),
    path('clanpve/lending/list/', clan_pve.ClanViewLendingView.as_view()),
    path('clanpve/lending/set/', clan_pve.ClanSetLendingView.as_view()),
    path('hacker/report/', antihacking.UserReportView.as_view()),
    path('levelbooster/levelup/', level_booster.LevelUpBooster.as_view()),
    path('levelbooster/get/', level_booster.LevelBoosterView.as_view()),
    path('levelbooster/fill/', level_booster.FillSlotView.as_view()),
    path('levelbooster/remove/', level_booster.RemoveSlotView.as_view()),
    path('levelbooster/skip/', level_booster.SkipCooldownView.as_view()),
    path('levelbooster/unlock/', level_booster.UnlockSlotView.as_view()),
    path('seasonreward/get/', tier_system.GetSeasonRewardView.as_view()),
    path('seasonreward/claim/', tier_system.ClaimSeasonRewardView.as_view()),
    path('champbadge/get/', tier_system.GetChampBadgeRewardListView.as_view()),
    path('champbadge/claim/', tier_system.ClaimChampRewardView.as_view()),
    path('eloreward/get/', tier_system.GetEloRewardListView.as_view()),
    path('eloreward/claim/', tier_system.ClaimEloRewardView.as_view()),
    path('eventreward/get/', event_rewards.GetEventRewardListView.as_view()),
    path('eventreward/claim/', event_rewards.ClaimEventRewardView.as_view()),
    path('event/times/get/', event_times.GetEventTimesView.as_view()),
    path('dailydungeon/start/', daily_dungeon.DailyDungeonStartView.as_view()),
    path('dailydungeon/status/', daily_dungeon.DailyDungeonStatusView.as_view()),
    path('dailydungeon/stage/', daily_dungeon.DailyDungeonStageView.as_view()),
    path('dailydungeon/result/', daily_dungeon.DailyDungeonResultView.as_view()),
    path('dailydungeon/skip/', daily_dungeon.DailyDungeonSkipView.as_view()),
    path('dailydungeon/forfeit/', daily_dungeon.DailyDungeonForfeitView.as_view()),
    path('moevasion/start/', moevasion.StartView.as_view()),
    path('moevasion/end/', moevasion.EndView.as_view()),
    path('moevasion/status/', moevasion.StatusView.as_view()),
    path('moevasion/stage/', moevasion.StageView.as_view()),
    path('moevasion/result/', moevasion.ResultView.as_view()),
    path('coinshop/buyitem/', coin_shop.TryBuyItemView.as_view()),
    path('coinshop/getitems/', coin_shop.GetItemsView.as_view()),
    path('tournament/matchhistory', tournament.TournamentMatchHistory.as_view()),
    path('tournament/self', tournament.TournamentSelfView.as_view()),
    path('tournament/getfights', tournament.TournamentFightsView.as_view()),
    path('tournament/setdefense', tournament.SetDefense.as_view()),
    path('tournament/selectcards', tournament.SelectCardsView.as_view()),
    path('tournament/getcards', tournament.GetCardsView.as_view()),
    path('tournament/register', tournament.TournamentRegView.as_view()),
    path('tournament/get', tournament.TournamentView.as_view()),
    path('referral', referral.ReferralView.as_view()),
    path('creatorcode/get/', creatorcode.CreatorCodeGetView.as_view()),
    path('creatorcode/set/', creatorcode.CreatorCodeChangeView.as_view()),
    path('creatorcode/claim/', creatorcode.CreatorCodeClaimView.as_view()),
    path('redeemcode', redemptioncodes.RedeemCodeView.as_view()),
    path('afkrewards/get', afk_rewards.GetAFKRewardView.as_view()),
    path('afkrewards/collect', afk_rewards.CollectAFKRewardView.as_view()),
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
    path('clanmember/', social.GetClanMember.as_view()),
    path('clan/search/', social.GetClanSearchResultsView.as_view()),
    path('clan/get/', social.GetClanView.as_view()),
    path('clan/editdescription/', social.EditClanDescriptionView.as_view()),
    path('clan/members/updatestatus/', social.ChangeMemberStatusView.as_view()),
    path('clan/new/', social.NewClanView.as_view()),
    path('clan/leave/', social.LeaveClanView.as_view()),
    path('clan/delete/', social.DeleteClanView.as_view()),
    path('clan/requests/get/', social.GetClanRequestsView.as_view()),
    path('clan/requests/update/', social.UpdateClanRequestView.as_view()),
    path('clan/requests/create/', social.CreateClanRequestView.as_view()),
    path('clan/profilepicture/update/', social.UpdateClanProfilePictureView.as_view()),
    path('pet/update/', social.UpdatePetView.as_view()),
    path('pet/unlock/', social.UnlockPetView.as_view()),
    path('profile/editdescription/', social.EditProfileDescriptionView.as_view()),
    path('friends/delete/', social.DeleteFriendView.as_view()),
    path('friends/get/', social.FriendsView.as_view()),
    path('leaderboards/', social.GetLeaderboardView.as_view()),
    path('getchatid/', social.GetChatIdView.as_view()),
    path('getallchats/', social.GetAllChatsView.as_view()),
    path('purchase/collectbonus/', purchases.CollectBonusGems.as_view()),
    path('purchase/cancel/sub/', purchases.CancelSubscriptionView.as_view()),
    path('validate/', purchases.ValidateView.as_view()),
    path('purchaseitem/', purchases.PurchaseItemView.as_view()),
    path('purchase/', purchases.PurchaseView.as_view()),
    path('deals/', purchases.GetDeals.as_view()),
    path('levelup/', inventory.TryLevelView.as_view()),
    path('prestige/', inventory.TryPrestigeView.as_view()),
    path('refund/', inventory.RefundCharacter.as_view()),
    path('retire/', inventory.RetireCharacter.as_view()),
    path('retire/auto/', inventory.SetAutoRetire.as_view()),
    path('uploadresult/quickplay/', statusupdate.UploadQuickplayResultView.as_view()),
    path('uploadresult/tourney/', statusupdate.UploadTourneyResultView.as_view()),
    path('skip/cost/', statusupdate.SkipsLeftView.as_view()),
    path('skip/', statusupdate.SkipView.as_view()),
    path('opponent/', pvp_queue.GetOpponentView.as_view()),
    path('opponents/', matcher.GetOpponentsView.as_view()),
    path('user/', matcher.GetUserView.as_view()),
    path('bots/', matcher.BotsView.as_view()),
    path('bots/uploadresults/', matcher.PostBotResultsView.as_view()),
    path('matcher/', matcher.MatcherView.as_view()),
    path('matchhistory/', matcher.GetMatchHistoryView.as_view()),
    path('matchreplay/', matcher.GetReplayView.as_view()),
    path('placements/', matcher.PlacementsView.as_view()),
    path('inventoryinfo/', inventory.InventoryView.as_view()),
    path('inventoryheader/', inventory.InventoryHeaderView.as_view()),
    path('inventory/equipitem/', inventory.EquipItemView.as_view()),
    path('inventory/unequipitem/', inventory.UnequipItemView.as_view()),
    path('inventory/scrapitems/', inventory.ScrapItemsView.as_view()),
    path('baseinfo/', base.BaseInfoView.as_view()),
    path('baseinfo/<str:version>', base.BaseInfoView.as_view()),
    path('test/', login.HelloView.as_view()),
    path('login/', login.ObtainAuthToken.as_view()),
    path('recover/', login.RecoverAccount.as_view()),
    path('recoverytoken/', login.GetRecoveryToken.as_view()),
    path('createnewuser/', login.CreateNewUser.as_view()),
    path('changename/', login.ChangeName.as_view()),
    path('dungeon/stage', dungeon.DungeonStageView.as_view()),
    path('dungeon/setprogress/stage/', dungeon.DungeonSetProgressStageView.as_view()),
    path('dungeon/setprogress/commit/', dungeon.DungeonSetProgressCommitView.as_view()),
    path('chest/queue/', chests.QueueChestView.as_view()),
    path('chest/unlock/', chests.UnlockChest.as_view()),
    path('chest/collect/', chests.CollectChest.as_view()),
    path('status/', server.ServerStatusView.as_view()),
    path('privacy/', web_pages.privacy),
    path('terms/', web_pages.terms),
    path('beta/', web_pages.beta),
    path('chat/', include('chat.urls')),
    path('admin/', admin.site.urls),
    path('public/stats/', public.PublicStatsView.as_view()),
    path('public/stats/<str:version>', public.PublicStatsView.as_view()),
    path('', web_pages.install),
]
