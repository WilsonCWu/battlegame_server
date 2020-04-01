from django.contrib import admin
from .models import BaseCharacter
from .models import BaseItem

admin.site.register(BaseCharacter)
admin.site.register(BaseItem)
