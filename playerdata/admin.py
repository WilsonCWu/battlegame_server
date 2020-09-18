from django.contrib import admin
from django.contrib import messages
from django.utils.translation import ngettext
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

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


class BaseCodeAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class BaseItemAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class BaseQuestAdmin(admin.ModelAdmin):
    actions = ['propagate_quests']
    list_display = ('title', 'type', 'total')
    list_filter = ('type', )

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


admin.site.register(DungeonStage)
admin.site.register(DungeonProgress)

admin.site.register(BaseCharacter)
admin.site.register(BaseCharacterUsage)
admin.site.register(BaseItem, BaseItemAdmin)
admin.site.register(Character)
admin.site.register(Item)

admin.site.register(Placement)
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

admin.site.register(ActiveCumulativeQuest)
admin.site.register(ActiveDailyQuest)
admin.site.register(ActiveWeeklyQuest)

admin.site.register(BaseCode, BaseCodeAdmin)
admin.site.register(ClaimedCode)

admin.site.register(UserReferral)
admin.site.register(ReferralTracker)

admin.site.register(Tournament)
admin.site.register(TournamentMember)
admin.site.register(TournamentTeam)
admin.site.register(TournamentRegistration)
admin.site.register(TournamentMatch)
