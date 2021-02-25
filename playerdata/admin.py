import bulk_admin
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.postgres.fields import JSONField
from django.core import serializers
from django.http import HttpResponse
from django.utils.translation import ngettext
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from django_json_widget.widgets import JSONEditorWidget

from battlegame.cron import next_round, setup_tournament, end_tourney
from . import constants
from .constants import MAX_PRESTIGE_LEVEL, PRESTIGE_CAP_BY_RARITY
from .dungeon import generate_dungeon_stages
from .matcher import generate_bots_from_users, generate_bots_bulk
from .models import ActiveCumulativeQuest
from .models import ActiveDailyQuest
from .models import ActiveDeal
from .models import ActiveWeeklyQuest
from .models import BaseCharacter, Chest
from .models import BaseCharacterAbility
from .models import BaseCharacterUsage
from .models import BaseCode
from .models import BaseDeal
from .models import BaseItem
from .models import BasePrestige
from .models import BaseQuest
from .models import Character
from .models import Chat
from .models import ChatMessage
from .models import ClaimedCode
from .models import Clan
from .models import ClanMember
from .models import ClanRequest
from .models import CumulativeTracker
from .models import DungeonBoss
from .models import DungeonProgress
from .models import DungeonStage
from .models import Friend
from .models import FriendRequest
from .models import InvalidReceipt
from .models import Inventory
from .models import Item
from .models import Match
from .models import Placement
from .models import PlayerQuestCumulative
from .models import PlayerQuestDaily
from .models import PlayerQuestWeekly
from .models import PurchasedTracker
from .models import ReferralTracker
from .models import ServerStatus
from .models import Tournament
from .models import TournamentMatch
from .models import TournamentMember
from .models import TournamentRegistration
from .models import TournamentSelectionCards
from .models import TournamentTeam
from .models import User
from .models import UserInfo
from .models import UserReferral
from .models import UserStats
from .purchases import refresh_daily_deals_cronjob, refresh_weekly_deals_cronjob
from .quest import queue_active_weekly_quests, queue_active_daily_quests, refresh_weekly_quests, refresh_daily_quests
from .login import UserRecoveryTokenGenerator


class BaseCodeAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class BaseItemAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ('rollable', 'name', 'item_type', 'rarity', 'gear_slot', 'cost', 'description')
    list_filter = ('rollable', 'gear_slot', 'rarity', 'cost')


class DungeonStageAdmin(bulk_admin.BulkModelAdmin):
    list_display = ('stage', 'dungeon_type', 'player_exp', 'coins', 'gems')
    raw_id_fields = ("mob",)
    list_filter = ('dungeon_type',)


class DungeonBossAdmin(bulk_admin.BulkModelAdmin):
    actions = ['generate_stages']
    raw_id_fields = ("placement",)
    list_display = ('stage', 'dungeon_type')
    list_filter = ('dungeon_type',)

    def generate_stages(self, request, queryset):
        generate_dungeon_stages(queryset)


class UserInfoAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'elo')
    actions = ('generate_bots_from_users', 'generate_bots_bulk', 'create_otp',
               'inventory_transfer_forward', 'inventory_transfer_reverse')
    search_fields = ('name',)

    def generate_bots_from_users(self, request, queryset):
        generate_bots_from_users(queryset)

    def generate_bots_bulk(self, request, queryset):
        generate_bots_bulk()

    def create_otp(self, request, queryset):
        token_generator = UserRecoveryTokenGenerator()
        res = {}
        for userinfo in queryset:
            res[userinfo.user_id] = '%d-%s' % (userinfo.user_id,
                                               token_generator.make_token(userinfo.user))
        response = HttpResponse(str(res))
        return response

    def inventory_transfer(source_userinfo, target_userinfo):
        original_user_id = source_userinfo.user_id
        original_description = source_userinfo.description

        source_userinfo.description = "[TRANSFERRED] " + original_description
        source_userinfo.save()

        # Fix the new user's placement.
        Placement.objects.filter(user_id = target_userinfo.user_id).delete()
        placement = Placement.objects.create()
        placement.user_id = target_userinfo.user_id
        placement.pos_1 = -1
        placement.char_1 = None
        placement.pos_2 = -1
        placement.char_2 = None
        placement.pos_3 = -1
        placement.char_3 = None
        placement.pos_4 = -1
        placement.char_4 = None
        placement.pos_5 = -1
        placement.char_5 = None
        placement.save()

        # TODO: if this is something that happens frequently, we should consider
        # account deactivation.
        source_userinfo.user = target_userinfo.user
        source_userinfo.description = original_description
        source_userinfo.default_placement = placement
        source_userinfo.save()

        # Fix the new user's inventory.
        old_inventory = Inventory.objects.get(user_id = original_user_id)
        inventory = Inventory.objects.get(user_id = target_userinfo.user_id)
        inventory.coins = old_inventory.coins
        inventory.gems = old_inventory.gems
        inventory.dust = old_inventory.dust
        inventory.essence = old_inventory.essence
        inventory.hero_exp = old_inventory.hero_exp
        inventory.save()

        # Clone dungeon progress.
        old_progress = DungeonProgress.objects.get(user_id=original_user_id)
        progress = DungeonProgress.objects.get(user_id=target_userinfo.user_id)
        progress.campaign_stage = old_progress.campaign_stage
        progress.tower_stage = old_progress.tower_stage
        progress.save()

        Character.objects.filter(user_id = target_userinfo.user_id).delete()
        for c in Character.objects.filter(user_id = original_user_id):
            Character.objects.create(user_id = target_userinfo.user_id,
                                     char_type = c.char_type,
                                     level = c.level,
                                     copies = c.copies,
                                     prestige = c.prestige)
            
        Item.objects.filter(user_id = target_userinfo.user_id).delete()
        for i in Item.objects.filter(user_id = original_user_id):
            Item.objects.create(user_id = target_userinfo.user_id,
                                item_type = i.item_type,
                                exp = i.exp)
        
    def inventory_transfer_forward(self, request, queryset):
        if len(queryset) != 2:
            raise Exception("Can only select 2 users for Inventory Transfer!")

        ordered = queryset.order_by('user_id')
        UserInfoAdmin.inventory_transfer(ordered[0], ordered[1])

    def inventory_transfer_reverse(self, request, queryset):
        if len(queryset) != 2:
            raise Exception("Can only select 2 users for Inventory Transfer!")

        ordered = queryset.order_by('user_id')
        UserInfoAdmin.inventory_transfer(ordered[1], ordered[0])


class PlacementAdmin(admin.ModelAdmin):
    list_display = ('placement_id', 'user', 'pos_1', 'char_1', 'pos_2', 'char_2', 'pos_3', 'char_3', 'pos_4', 'char_4', 'pos_5', 'char_5')
    raw_id_fields = ("char_1", "char_2", "char_3", "char_4", "char_5",)


class BaseQuestAdmin(bulk_admin.BulkModelAdmin):
    actions = ['propagate_quests']
    list_display = ('id', 'title', 'type', 'total')
    list_filter = ('type',)

    def propagate_quests(self, request, queryset):
        bulk_quests = []
        users = User.objects.all()
        for quest in queryset:
            for user in users:
                progress_tracker, _ = CumulativeTracker.objects.get_or_create(user=user, type=quest.type)
                player_quest = PlayerQuestCumulative(base_quest=quest, user=user, progress=progress_tracker)
                if progress_tracker.progress >= quest.total:
                    player_quest.completed = True
                bulk_quests.append(player_quest)

        PlayerQuestCumulative.objects.bulk_create(bulk_quests)
        self.message_user(request, ngettext(
            '%d cumulative BaseQuest successfully propagated.',
            '%d cumulative BaseQuests successfully propagated.',
            len(queryset),
        ) % len(queryset), messages.SUCCESS)

    propagate_quests.short_description = "Propagate cumulative BaseQuest to all Users"


class ActiveCumulativeQuestAdmin(bulk_admin.BulkModelAdmin):
    pass


class ActiveDailyQuestAdmin(bulk_admin.BulkModelAdmin):
    actions = ['add_quests', 'refresh']

    def add_quests(self, request, queryset):
        queue_active_daily_quests()

    def refresh(self, request, queryset):
        refresh_daily_quests()


class ActiveWeeklyQuestAdmin(bulk_admin.BulkModelAdmin):
    actions = ['add_quests', 'refresh']

    def add_quests(self, request, queryset):
        queue_active_weekly_quests()

    def refresh(self, request, queryset):
        refresh_weekly_quests()


class ActiveDealAdmin(admin.ModelAdmin):
    list_display = ('base_deal', 'expiration_date')
    actions = ['refresh_daily_deals', 'refresh_weekly_deals']

    def refresh_daily_deals(self, request, queryset):
        refresh_daily_deals_cronjob()

    def refresh_weekly_deals(self, request, queryset):
        refresh_weekly_deals_cronjob()


class BaseDealAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'deal_type', 'gems', 'coins', 'dust', 'item', 'char_type', 'purchase_id')
    list_filter = ('order', 'deal_type')


class PurchasedTrackerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'purchase_id', 'transaction_id', 'purchase_time')
    search_fields = ('user__id',)


class TournamentRegAdmin(admin.ModelAdmin):
    actions = ['setup_tourney']

    def setup_tourney(self, request, queryset):
        setup_tournament()


class TournamentAdmin(admin.ModelAdmin):
    # manual overrides for tourney rounds
    actions = ['next_round', 'end_tourney']

    def next_round(self, request, queryset):
        next_round()

    def end_tourney(self, request, queryset):
        end_tourney()


class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'action_time'

    readonly_fields = [
        'action_time',
        'action_flag',
        'user',
        'content_type',
        'object_id',
        'object_link',
        'object_repr',
        'change_message',
    ]

    list_filter = [
        'user',
        'content_type',
        'action_flag'
    ]

    search_fields = [
        'object_repr',
        'change_message'
    ]

    list_display = [
        'action_time',
        'user',
        'content_type',
        'object_link',
        'action_flag_',
        'change_message',
    ]

    def action_flag_(self, obj):
        flags = {
            1: "Addition",
            2: "Changed",
            3: "Deleted",
        }
        return flags[obj.action_flag]

    def object_link(self, obj):
        return '{type}_id {id}: {obj}'.format(
            type=obj.content_type.model,
            id=obj.object_id,
            obj=obj.object_repr,
        )

    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'Modified Object'


@admin.register(BaseCharacterAbility)
class BaseCharacterAbilityAdmin(admin.ModelAdmin):
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget}
    }


@admin.register(BaseCharacter)
class BaseCharacterAdmin(admin.ModelAdmin):
    actions = ('generate_usage_and_prestige',)
    list_display = ('char_type', 'name', 'rollable', 'rarity')
    list_filter = ('rollable', 'rarity')

    def generate_usage_and_prestige(self, request, queryset):
        for base_char in queryset:
            # Create BaseCharacterUsage for characters that currently
            # don't have it.
            if not hasattr(base_char, "basecharacterusage"):
                BaseCharacterUsage.objects.create(char_type=base_char)

            # Create BasePrestige for characters that currently don't have
            # any.
            if not BasePrestige.objects.filter(char_type=base_char).exists():
                for i in range(PRESTIGE_CAP_BY_RARITY[base_char.rarity] + 1):
                    # Don't need to backfill for common characters.
                    if base_char.rarity == 1 and i == 0: continue

                    levels_to_backfill = MAX_PRESTIGE_LEVEL - PRESTIGE_CAP_BY_RARITY[base_char.rarity]
                    star_level = i + levels_to_backfill
                    BasePrestige.objects.create(
                        char_type=base_char,
                        level=i,
                        attack_mult=(1.07 ** star_level),
                        ability_mult=(1.07 ** star_level),
                        ar_mult=(1.07 ** star_level),
                        mr_mult=(1.07 ** star_level),
                        max_health_mult=(1.07 ** star_level),
                    )


admin.site.register(DungeonStage, DungeonStageAdmin)
admin.site.register(DungeonProgress)
admin.site.register(DungeonBoss, DungeonBossAdmin)

admin.site.register(BaseCharacterUsage)
admin.site.register(BaseItem, BaseItemAdmin)
admin.site.register(BasePrestige)
admin.site.register(Character)
admin.site.register(Item)

admin.site.register(Placement, PlacementAdmin)
admin.site.register(UserInfo, UserInfoAdmin)
admin.site.register(UserStats)
admin.site.register(Match)
admin.site.register(Inventory)

admin.site.register(Chat)
admin.site.register(ChatMessage)
admin.site.register(Friend)
admin.site.register(FriendRequest)
admin.site.register(Clan)
admin.site.register(ClanMember)
admin.site.register(ClanRequest)

admin.site.register(BaseQuest, BaseQuestAdmin)
admin.site.register(PlayerQuestCumulative)
admin.site.register(PlayerQuestDaily)
admin.site.register(PlayerQuestWeekly)
admin.site.register(CumulativeTracker)

admin.site.register(ActiveCumulativeQuest, ActiveCumulativeQuestAdmin)
admin.site.register(ActiveDailyQuest, ActiveDailyQuestAdmin)
admin.site.register(ActiveWeeklyQuest, ActiveWeeklyQuestAdmin)

admin.site.register(BaseCode, BaseCodeAdmin)
admin.site.register(ClaimedCode)

admin.site.register(UserReferral)
admin.site.register(ReferralTracker)

admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentMember)
admin.site.register(TournamentTeam)
admin.site.register(TournamentRegistration, TournamentRegAdmin)
admin.site.register(TournamentMatch)
admin.site.register(TournamentSelectionCards)

admin.site.register(InvalidReceipt)
admin.site.register(BaseDeal, BaseDealAdmin)
admin.site.register(ActiveDeal, ActiveDealAdmin)
admin.site.register(PurchasedTracker, PurchasedTrackerAdmin)
admin.site.register(ServerStatus)
admin.site.register(LogEntry, LogEntryAdmin)

admin.site.register(Chest)
