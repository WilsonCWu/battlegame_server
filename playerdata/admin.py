from django.contrib import admin

from .models import BaseCharacter
from .models import BaseCharacterUsage
from .models import BaseItem
from .models import Character
from .models import Item
from .models import UserInfo
from .models import Placement
from .models import Team
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

admin.site.register(DungeonStage)
admin.site.register(DungeonProgress)

admin.site.register(BaseCharacter)
admin.site.register(BaseCharacterUsage)
admin.site.register(BaseItem)
admin.site.register(Character)
admin.site.register(Item)

admin.site.register(Placement)
admin.site.register(Team)
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

admin.site.register(BaseQuest)
admin.site.register(PlayerQuestCumulative)
admin.site.register(PlayerQuestDaily)
admin.site.register(PlayerQuestWeekly)

admin.site.register(ActiveCumulativeQuest)
admin.site.register(ActiveDailyQuest)
admin.site.register(ActiveWeeklyQuest)
