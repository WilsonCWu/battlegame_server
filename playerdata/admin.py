from django.contrib import admin

from .models import BaseCharacter
from .models import BaseItem
from .models import Character
from .models import Item
from .models import UserInfo
from .models import Placement
from .models import Team
from .models import UserStats
from .models import Inventory

admin.site.register(BaseCharacter)
admin.site.register(BaseItem)
admin.site.register(Character)
admin.site.register(Item)

admin.site.register(Placement)
admin.site.register(Team)
admin.site.register(UserInfo)
admin.site.register(UserStats)
admin.site.register(Inventory)
