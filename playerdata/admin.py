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
from packaging import version

from battlegame.cron import next_round, setup_tournament, end_tourney
from . import constants
from .constants import MAX_PRESTIGE_LEVEL, PRESTIGE_CAP_BY_RARITY
from .daily_dungeon import daily_dungeon_team_gen_cron
from .dungeon import generate_dungeon_stages
from .dungeon_gen import convert_placement_to_json
from .matcher import generate_bots_from_users, generate_bots_bulk
from .models import *
from .purchases import refresh_daily_deals_cronjob, refresh_weekly_deals_cronjob
from .quest import queue_active_weekly_quests, queue_active_daily_quests, refresh_weekly_quests, refresh_daily_quests
from .login import UserRecoveryTokenGenerator


class InventoryAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass

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
    actions = ['generate_stages', 'convert_json']
    raw_id_fields = ("placement",)
    list_display = ('stage', 'dungeon_type')
    list_filter = ('dungeon_type',)

    def generate_stages(self, request, queryset):
        generate_dungeon_stages(queryset)

    def convert_json(self, request, queryset):
        convert_placement_to_json(queryset)


class IPTrackerAdmin(admin.ModelAdmin):
    list_display = ('ip', 'suspicious')
    list_filter = ('suspicious',)


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
    list_display = ('id', 'title', 'type', 'total')
    list_filter = ('type',)


class CumulativeTrackerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'progress', 'type')
    search_fields = ('user__id',)


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


@admin.register(PlayerQuestCumulative2)
class PlayerQuestCumulative2Admin(admin.ModelAdmin, DynamicArrayMixin):
    search_fields = ('user__id',)


class ActiveDealAdmin(admin.ModelAdmin):
    list_display = ('base_deal', 'expiration_date')
    actions = ['refresh_daily_deals', 'refresh_weekly_deals']

    def refresh_daily_deals(self, request, queryset):
        refresh_daily_deals_cronjob()

    def refresh_weekly_deals(self, request, queryset):
        refresh_weekly_deals_cronjob()

class DailyDungeonStageAdmin(admin.ModelAdmin):
    actions = ['refresh_stages']

    def refresh_stages(self, request, queryset):
        daily_dungeon_team_gen_cron()


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


@admin.register(BaseCharacterAbility2)
class BaseCharacterAbility2Admin(admin.ModelAdmin):
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget}
    }
    list_filter = ('char_type', 'version')
    actions = ('generate_next_patch', 'generate_patch_notes')

    def generate_next_patch(self, request, queryset):
        for a in queryset:
            next_patch = ServerStatus.latest_version().split('.')
            next_patch[-1] = str(int(next_patch[-1]) + 1)
            next_patch_str = '.'.join(next_patch)
            
            BaseCharacterAbility2.objects.create(
                char_type = a.char_type,
                version = next_patch_str,
                ability1_specs = a.ability1_specs,
                ability1_desc = a.ability1_desc,
                ability2_specs = a.ability2_specs,
                ability2_desc = a.ability2_desc,
                ability3_specs = a.ability3_specs,
                ability3_desc = a.ability3_desc,
                ultimate_specs = a.ultimate_specs,
                ultimate_desc = a.ultimate_desc,
            )

    def generate_patch_notes(self, request, queryset):
        v = queryset[0].version
        changed = BaseCharacterAbility2.objects.filter(version=v)

        previous = {}
        for a in BaseCharacterAbility2.objects.all():
            if version.parse(a.version) >= version.parse(v):
                continue
            if a.char_type not in previous or version.parse(a.version) > version.parse(previous[a.char_type].version):
                previous[a.char_type] = a

        resp = []
        for a in changed:
            if a.char_type not in previous:
                resp.append('NEW CHARACTER: %s' % a.char_type.name)
            else:
                p = previous[a.char_type]
                char_diff = ['CHANGED CHARACTER: %s\n\n' % a.char_type.name]
                
                for ability_type, ability_name, specs, prev_specs in zip(
                        ['Ability1', 'Ability2', 'Ability3', 'Ultimate'],
                        [a.ability1_desc, a.ability2_desc, a.ability3_desc, a.ultimate_desc],
                        [a.ability1_specs, a.ability2_specs, a.ability3_specs, a.ultimate_specs],
                        [p.ability1_specs, p.ability2_specs, p.ability3_specs, p.ultimate_specs],
                ):
                    if not prev_specs:
                        char_diff.append('NEW %s (%s)' % (ability_type, ability_name))
                        continue

                    # Check if we have any changes before noting that an ability
                    # has diffed.
                    ability_diff = []

                    # Assume that the levels are the same and don't actually
                    # change.
                    for lvl in sorted(specs.keys(), key=lambda x: int(x) if BaseCharacterAbility2.is_num_key(x) else 1000 + int(x.lstrip('prestige-'))):
                        if lvl not in prev_specs:
                            ability_diff.append('LEVEL CHANGES (missing level %s)' % lvl)
                            continue

                        ability_diff.append(lvl)
                        has_changes = False
                        removed_keys = set(prev_specs[lvl]) - set(specs[lvl])
                        if removed_keys:
                            has_changes = True
                            ability_diff.append('REMOVED: %s' % str(removed_keys))

                        new_keys = {k: v for k, v in specs[lvl].items() if k not in prev_specs[lvl]}
                        if new_keys:
                            has_changes = True
                            ability_diff.append('NEW: %s' % str(new_keys))

                        changed_keys = {k: str(v) + ' -> ' + str(prev_specs[lvl][k])
                                        for k, v in specs[lvl].items()
                                        if k in prev_specs[lvl] and v != prev_specs[lvl][k]}
                        if changed_keys:
                            has_changes = True
                            ability_diff.append('CHANGED: %s' % str(changed_keys))

                        if not has_changes: ability_diff.pop()

                    if ability_diff - specs.keys():
                        diff_str = '%s (%s)\n%s\n' % (ability_type, ability_name, '\n'.join(ability_diff))
                        char_diff.append(diff_str)

                # Aggregate all the changes for a character.
                resp.append('\n'.join(char_diff))
        return HttpResponse('\n\n\n'.join(resp), content_type="text/plain")
            

@admin.register(BaseCharacterStats)
class BaseCharacterStatsAdmin(admin.ModelAdmin):
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget}
    }
    list_filter = ('char_type', 'version')
    actions = ('generate_next_patch', 'generate_patch_notes')

    def generate_next_patch(self, request, queryset):
        for a in queryset:
            next_patch = ServerStatus.latest_version().split('.')
            next_patch[-1] = str(int(next_patch[-1]) + 1)
            next_patch_str = '.'.join(next_patch)
            
            BaseCharacterStats.objects.create(
                char_type = a.char_type,
                version = next_patch_str,
                health = a.health,
                starting_mana = a.starting_mana,
                mana = a.mana,
                speed = a.speed,
                attack_damage = a.attack_damage,
                ability_damage = a.ability_damage,
                attack_speed = a.attack_speed,
                ar = a.ar,
                mr = a.mr,
                attack_range = a.attack_range,
                crit_chance = a.crit_chance,
                health_scale = a.health_scale,
                attack_scale = a.attack_scale,
                ability_scale = a.ability_scale,
                ar_scale = a.ar_scale,
                mr_scale = a.mr_scale,
            )

    def generate_patch_notes(self, request, queryset):
        v = queryset[0].version
        changed = BaseCharacterStats.objects.filter(version=v)

        previous = {}
        for a in BaseCharacterStats.objects.all():
            if version.parse(a.version) >= version.parse(v):
                continue
            if a.char_type not in previous or version.parse(a.version) > version.parse(previous[a.char_type].version):
                previous[a.char_type] = a

        resp = []
        for a in changed:
            if a.char_type not in previous:
                resp.append('NEW CHARACTER: %s' % a.char_type.name)
            else:
                p = previous[a.char_type]
                char_diff = ['CHANGED CHARACTER: %s\n\n' % a.char_type.name]

                # Get ready for the if-statements baby.
                if p.health != a.health:
                    char_diff.append('HEALTH: %s -> %s' % (p.health, a.health))
                if p.starting_mana != a.starting_mana:
                    char_diff.append('STARTING MANA: %s -> %s' % (p.starting_mana, a.starting_mana))
                if p.mana != a.mana:
                    char_diff.append('MANA: %s -> %s' % (p.mana, a.mana))
                if p.speed != a.speed:
                    char_diff.append('SPEED: %s -> %s' % (p.speed, a.speed))
                if p.attack_damage != a.attack_damage:
                    char_diff.append('AD: %s -> %s' % (p.attack_damage, a.attack_damage))
                if p.ability_damage != a.ability_damage:
                    char_diff.append('AP: %s -> %s' % (p.ability_damage, a.ability_damage))
                if p.attack_speed != a.attack_speed:
                    char_diff.append('AS: %s -> %s' % (p.attack_speed, a.attack_speed))
                if p.ar != a.ar:
                    char_diff.append('AR: %s -> %s' % (p.ar, a.ar))
                if p.mr != a.mr:
                    char_diff.append('MR: %s -> %s' % (p.mr, a.mr))
                if p.attack_range != a.attack_range:
                    char_diff.append('Range: %s -> %s' % (p.attack_range, a.attack_range))
                if p.crit_chance != a.crit_chance:
                    char_diff.append('Crit: %s -> %s' % (p.crit_chance, a.crit_chance))
                if p.health_scale != a.health_scale:
                    char_diff.append('HEALTH Scale: %s -> %s' % (p.health_scale, a.health_scale))
                if p.attack_scale != a.attack_scale:
                    char_diff.append('AD Scale: %s -> %s' % (p.attack_scale, a.attack_scale))
                if p.ability_scale != a.ability_scale:
                    char_diff.append('AP Scale: %s -> %s' % (p.ability_scale, a.ability_scale))
                if p.ar_scale != a.ar_scale:
                    char_diff.append('AR Scale: %s -> %s' % (p.ar_scale, a.ar_scale))
                if p.mr_scale != a.mr_scale:
                    char_diff.append('MR Scale: %s -> %s' % (p.mr_scale, a.mr_scale))
                resp.append('\n'.join(char_diff))

        return HttpResponse('\n\n\n'.join(resp), content_type="text/plain")

@admin.register(BaseCharacter)
class BaseCharacterAdmin(admin.ModelAdmin):
    actions = ('generate_deps',)
    list_display = ('char_type', 'name', 'rollable', 'rarity')
    list_filter = ('rollable', 'rarity')

    def generate_deps(self, request, queryset):
        for base_char in queryset:
            # Create BaseCharacterUsage for characters that currently
            # don't have it.
            if not BaseCharacterUsage.objects.filter(char_type=base_char).exists():
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

            # Create BaseCharacterStats if need. Defaults to base stats of
            # Haldor.
            if not BaseCharacterStats.objects.filter(char_type=base_char).exists():
                BaseCharacterStats.objects.create(
                    char_type=base_char,
                    version='0.0.0',
                    health=700,
                    starting_mana=0,
                    mana=120,
                    speed=100,
                    attack_damage=100,
                    ability_damage=100,
                    attack_speed=1.0,
                    ar=20,
                    mr=20,
                    attack_range=1,
                    crit_chance=10,
                    health_scale=100,
                    attack_scale=100,
                    ability_scale=100,
                    ar_scale=30,
                    mr_scale=30,
                )

            # Create an easy to fill BaseCharacterAbility2.
            if not BaseCharacterAbility2.objects.filter(char_type=base_char).exists():
                sl = PRESTIGE_CAP_BY_RARITY[base_char.rarity] - 5
                BaseCharacterAbility2.objects.create(
                    char_type=base_char,
                    version='0.0.0',
                    ability1_specs={"21": {}, "101": {}, "181": {}, "prestige-%d" % (1 + sl): {}},
                    ability2_specs={"41": {}, "121": {}, "201": {}, "prestige-%d" % (2 + sl): {}},
                    ability3_specs={"61": {}, "141": {}, "221": {}, "prestige-%d" % (4 + sl): {}},
                    ultimate_specs={"1": {}, "81": {}, "161": {}, "prestige-%d" % (3 + sl): {}, "prestige-%d" % (5 + sl): {}},
                )


@admin.register(MatchReplay)
class MatchReplayAdmin(admin.ModelAdmin):
    raw_id_fields = ('match',)


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
admin.site.register(Inventory, InventoryAdmin)

admin.site.register(Chat)
admin.site.register(ChatMessage)
admin.site.register(Friend)
admin.site.register(FriendRequest)
admin.site.register(Clan2)
admin.site.register(ClanMember)
admin.site.register(ClanRequest)

admin.site.register(BaseQuest, BaseQuestAdmin)
admin.site.register(PlayerQuestDaily)
admin.site.register(PlayerQuestWeekly)
admin.site.register(CumulativeTracker, CumulativeTrackerAdmin)

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
admin.site.register(IPTracker, IPTrackerAdmin)

admin.site.register(Chest)

admin.site.register(DailyDungeonStatus)
admin.site.register(DailyDungeonStage, DailyDungeonStageAdmin)

admin.site.register(MoevasionStatus)

admin.site.register(Flag)
admin.site.register(UserFlag)
admin.site.register(HackerAlert)
