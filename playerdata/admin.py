from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.utils.translation import ngettext
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
import bulk_admin

from battlegame.cron import next_round, setup_tournament, end_tourney
from .dungeon import generate_dungeon_stages
from .models import BaseCharacter
from .models import BaseCharacterUsage
from .models import BaseItem
from .models import Character
from .models import Item
from .models import User
from .models import UserInfo
from .models import Placement
from .models import UserStats
from .models import Inventory
from .models import Chat
from .models import ChatMessage
from .models import Friend
from .models import FriendRequest
from .models import Clan
from .models import ClanMember
from .models import ClanRequest
from .models import DungeonStage
from .models import DungeonProgress
from .models import DungeonBoss
from .models import BaseQuest
from .models import PlayerQuestCumulative
from .models import PlayerQuestDaily
from .models import PlayerQuestWeekly
from .models import ActiveDailyQuest
from .models import ActiveWeeklyQuest
from .models import ActiveCumulativeQuest
from .models import CumulativeTracker
from .models import BaseCode
from .models import ClaimedCode
from .models import UserReferral
from .models import ReferralTracker
from .models import Tournament
from .models import TournamentMember
from .models import TournamentTeam
from .models import TournamentRegistration
from .models import TournamentMatch
from .models import TournamentSelectionCards
from .models import InvalidReceipt
from .models import ServerStatus


class BaseCodeAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class BaseItemAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ('name', 'item_type', 'rarity', 'gear_slot', 'cost', 'description')
    list_filter = ('gear_slot', 'rarity', 'cost')


class DungeonStageAdmin(bulk_admin.BulkModelAdmin):
    list_display = ('stage', 'player_exp', 'coins', 'gems')
    raw_id_fields = ("mob",)


class DungeonBossAdmin(bulk_admin.BulkModelAdmin):
    actions = ['generate_stages']
    raw_id_fields = ("placement",)

    def generate_stages(self, request, queryset):
        generate_dungeon_stages(queryset)


class PlacementAdmin(admin.ModelAdmin):
    list_display = ('placement_id', 'user', 'pos_1', 'char_1', 'pos_2', 'char_2', 'pos_3', 'char_3', 'pos_4', 'char_4', 'pos_5', 'char_5')
    raw_id_fields = ("char_1", "char_2", "char_3", "char_4", "char_5",)


class BaseQuestAdmin(bulk_admin.BulkModelAdmin):
    actions = ['propagate_quests']
    list_display = ('title', 'type', 'total')
    list_filter = ('type',)

    def propagate_quests(self, request, queryset):
        bulk_quests = []
        users = User.objects.all()
        for quest in queryset:
            for user in users:
                progress_tracker, _ = CumulativeTracker.objects.get_or_create(user=user, type=quest.type)
                player_quest = PlayerQuestCumulative(base_quest=quest, user=user, progress=progress_tracker)
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
    pass


class ActiveWeeklyQuestAdmin(bulk_admin.BulkModelAdmin):
    pass


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


admin.site.register(DungeonStage, DungeonStageAdmin)
admin.site.register(DungeonProgress)
admin.site.register(DungeonBoss, DungeonBossAdmin)

admin.site.register(BaseCharacter)
admin.site.register(BaseCharacterUsage)
admin.site.register(BaseItem, BaseItemAdmin)
admin.site.register(Character)
admin.site.register(Item)

admin.site.register(Placement, PlacementAdmin)
admin.site.register(UserInfo)
admin.site.register(UserStats)
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
admin.site.register(ServerStatus)
admin.site.register(LogEntry, LogEntryAdmin)
