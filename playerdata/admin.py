import bulk_admin
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.models import LogEntry
from django.http import HttpResponse
from django.shortcuts import render
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from django_json_widget.widgets import JSONEditorWidget

from battlegame.cron import next_round, setup_tournament, end_tourney
from battlegame.figures import get_hacker_alert_dataframe, get_table_context, get_base_character_usage_dataframe, get_dungeon_stats_dataframe
from . import purchases
from .daily_dungeon import daily_dungeon_team_gen_cron
from .dungeon_gen import convert_placement_to_json
from .login import UserRecoveryTokenGenerator
from .matcher import generate_bots_from_users
from .models import *
from .quest import queue_active_weekly_quests, queue_active_daily_quests, refresh_weekly_quests, refresh_daily_quests


class InventoryAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ('user_id', 'gems', 'gems_bought')
    search_fields = ('=user__id',)
    raw_id_fields = ("user", "chest_slot_1", "chest_slot_2", "chest_slot_3", "chest_slot_4", "login_chest")


class AFKRewardAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ('user', )
    search_fields = ('=user__id',)
    raw_id_fields = ("user",)


class BaseCodeAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class BaseItemAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ('rollable', 'name', 'item_type', 'rarity', 'gear_slot', 'cost', 'description')
    list_filter = ('rollable', 'gear_slot', 'rarity', 'cost')


class RelicShopAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class WishlistAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


class StoryModeAdmin(admin.ModelAdmin, DynamicArrayMixin):
    raw_id_fields = ("user",)


class DungeonStageAdmin(bulk_admin.BulkModelAdmin):
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget}
    }
    list_display = ('stage', 'dungeon_type', 'player_exp', 'coins', 'gems')
    raw_id_fields = ("mob",)
    list_filter = ('dungeon_type',)


class DungeonBossAdmin(bulk_admin.BulkModelAdmin):
    actions = ['generate_stages', 'convert_json']
    raw_id_fields = ("placement",)
    list_display = ('stage', 'dungeon_type')
    list_filter = ('dungeon_type',)

    def convert_json(self, request, queryset):
        convert_placement_to_json(queryset)


class DungeonStatsAdmin(admin.ModelAdmin):
    actions = ('generate_dungeon_stats_report',)

    def generate_dungeon_stats_report(self, request, queryset):
        start = datetime.utcnow()
        df = get_dungeon_stats_dataframe(queryset)
        df['winrate'] = 100 * df['wins'] / df['games']
        context = get_table_context(df)
        end = datetime.utcnow()
        elapsed = end - start
        context['page_title'] = "Dungeon Stats Report"
        context['other_data'] = [f'Time: {datetime.now()}']
        context['other_data'].append(f'Function runtime: {elapsed}')
        return render(request, 'table.html', context)


class IPTrackerAdmin(admin.ModelAdmin):
    list_display = ('ip', 'suspicious')
    list_filter = ('suspicious',)


class UserInfoAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'elo')
    actions = ('generate_bots_from_users', 'create_otp',
               'inventory_transfer_forward', 'inventory_transfer_reverse',
               'generate_defense_placement_report',)
    search_fields = ('name',)
    raw_id_fields = ("user", "default_placement")

    def generate_bots_from_users(self, request, queryset):
        generate_bots_from_users(queryset)

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

    def generate_defense_placement_report(self, request, queryset):
        start = datetime.utcnow()

        queryset = queryset.select_related('default_placement').select_related('default_placement__char_1') \
            .select_related('default_placement__char_1__char_type') \
            .select_related('default_placement__char_2') \
            .select_related('default_placement__char_2__char_type') \
            .select_related('default_placement__char_3') \
            .select_related('default_placement__char_3__char_type') \
            .select_related('default_placement__char_4') \
            .select_related('default_placement__char_4__char_type') \
            .select_related('default_placement__char_5') \
            .select_related('default_placement__char_5__char_type')

        base_characters = BaseCharacter.objects.all()
        char_names = [''] * base_characters.count()
        char_rarities = [0] * base_characters.count()
        char_usage_count = [0] * base_characters.count()
        placements_analyzed = 0

        # load the names into a list to easily access name by char_id.
        for base_char in base_characters:
            char_names[base_char.char_type] = base_char.name
            char_rarities[base_char.char_type] = base_char.rarity

        # pull usage statistics from the selected users
        for user_info in queryset:
            placement = user_info.default_placement
            if Placement is None:
                continue
            placements_analyzed += 1

            user_defense_chars = [placement.char_1, placement.char_2, placement.char_3, placement.char_4, placement.char_5]
            for char in user_defense_chars:
                if char is None:
                    continue
                char_usage_count[char.char_type.char_type] += 1

        end = datetime.utcnow()

        elapsed = end - start

        # Write report as HTTP page.
        response = HttpResponse()
        response.write(f"<h1>Defense Character Usage Report</h1>")
        response.write(f'<p style="margin:0;"><b>Time:</b> {datetime.now()}</p>')
        response.write(f'<p style="margin:0;"><b>Total Placements:</b> {placements_analyzed}</p>')
        response.write(f'<p style="margin:0;"><b>Function runtime:</b> {elapsed}</p><p></p>')

        for i in range(4, 0, -1):  # To filter by rarity, just go through the data once for each rarity, outputting info only if rarity matches.
            response.write(f'<h3>Rarity {i}:</h3>')
            for j in range(0, base_characters.count()):
                if char_rarities[j] != i or char_usage_count[j] == 0:
                    continue
                usage_count = char_usage_count[j]
                percent_usage_count = "{:.2f}".format(100 * usage_count / placements_analyzed)
                response.write(f'<p style="margin:0;">{char_names[j]} ({j}): {percent_usage_count}% ({usage_count} / {placements_analyzed})</p>')
        return response


class PlacementAdmin(admin.ModelAdmin):
    list_display = ('placement_id', 'user', 'pos_1', 'char_1', 'pos_2', 'char_2', 'pos_3', 'char_3', 'pos_4', 'char_4', 'pos_5', 'char_5')
    raw_id_fields = ("char_1", "char_2", "char_3", "char_4", "char_5",)


class BaseQuestAdmin(bulk_admin.BulkModelAdmin):
    list_display = ('id', 'title', 'type', 'total')
    list_filter = ('type',)


class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'num_games', 'num_wins', 'time_started')
    raw_id_fields = ('user',)
    search_fields = ('=user__id',)


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
    search_fields = ('=user__id',)


class ActiveDealAdmin(admin.ModelAdmin):
    list_display = ('base_deal', 'expiration_date')
    actions = ['refresh_daily_deals', 'refresh_weekly_deals', 'refresh_monthly_deals']

    def refresh_daily_deals(self, request, queryset):
        purchases.refresh_daily_deals_cronjob()

    def refresh_weekly_deals(self, request, queryset):
        purchases.refresh_weekly_deals_cronjob()

    def refresh_monthly_deals(self, request, queryset):
        purchases.refresh_monthly_deals_cronjob()


class DailyDungeonStageAdmin(admin.ModelAdmin):
    actions = ['refresh_stages']

    def refresh_stages(self, request, queryset):
        daily_dungeon_team_gen_cron()


class BaseDealAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'deal_type', 'gems', 'coins', 'dust', 'item', 'char_type', 'purchase_id')
    list_filter = ('order', 'deal_type')


class BlackListPurchasesFilter(SimpleListFilter):
    title = 'blacklist_purchase_id' # or use _('country') for translated title
    parameter_name = 'purchase_id'

    FREE_DEALS_ID = 'BLACKLIST_FREE_DEALS'
    FREE_DEALS = [constants.DEAL_DAILY_0,
                  constants.DEAL_WEEKLY_0,
                  constants.DEAL_MONTHLY_0]

    def lookups(self, request, model_admin):
        products = [(p.purchase_id, p.purchase_id) for p in PurchasedTracker.objects.distinct('purchase_id')]
        # Add a special black list all free deals case
        return products + [(self.FREE_DEALS_ID, self.FREE_DEALS_ID)]

    def queryset(self, request, queryset):
        if self.value() == self.FREE_DEALS_ID:
            return queryset.exclude(purchase_id__in=self.FREE_DEALS)
        if self.value():
            return queryset.exclude(purchase_id=self.value())


class PurchasedTrackerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'purchase_id', 'transaction_id', 'purchase_time')
    list_filter = (BlackListPurchasesFilter, 'purchase_id', 'purchase_time')
    search_fields = ('=user__id',)


class CreatorCodeAdmin(admin.ModelAdmin):
    search_fields = ('=user__id',)
    raw_id_fields = ('user',)


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


class CharacterAdmin(admin.ModelAdmin):
    list_display = ('char_id', 'user', 'char_type', 'level', 'copies', 'prestige')
    raw_id_fields = ('user', 'hat', 'armor', 'weapon', 'boots', 'trinket_1', 'trinket_2')


class MailAdmin(admin.ModelAdmin):
    list_display = ('receiver', 'title', 'message', 'time_send')
    raw_id_fields = ('receiver', 'sender')


class RegalRewardsAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


class ActivityPointsAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


class ClanMemberAdmin(admin.ModelAdmin, DynamicArrayMixin):
    raw_id_fields = ('userinfo', 'clan2')


class BaseResourceShopItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cost_type', 'cost_value', 'reward_type', 'reward_value')


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

    # Old code, see gameanalytics.get_character_changes_view
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

                        changed_keys = {k: str(prev_specs[lvl][k]) + ' -> ' + str(v)
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
                ability_ticks = a.ability_ticks,
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

    # Old code, see gameanalytics.get_character_changes_view
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
                if p.ability_ticks != a.ability_ticks:
                    char_diff.append('ABILITY TICKS: %s -> %s' % (p.ability_ticks, a.ability_ticks))
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
            PRESTIGE_CAP = constants.PRESTIGE_CAP_BY_RARITY_15[base_char.rarity]
            MAX_PRESTIGE = constants.MAX_PRESTIGE_LEVEL_15

            for i in range(PRESTIGE_CAP + 1):
                # Don't need to backfill for common characters.
                if base_char.rarity == 1 and i == 0: continue

                levels_to_backfill = MAX_PRESTIGE - PRESTIGE_CAP
                star_level = i + levels_to_backfill
                prestige_mult = (1.07 ** min(star_level, 10)) * (1.035 ** max(0, star_level - 10))

                if not BasePrestige.objects.filter(char_type=base_char, level=i).exists():
                    BasePrestige.objects.create(
                        char_type=base_char,
                        level=i,
                        attack_mult=prestige_mult,
                        ability_mult=prestige_mult,
                        ar_mult=prestige_mult,
                        mr_mult=prestige_mult,
                        max_health_mult=prestige_mult,
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
                    ability_ticks=3,
                    speed=100,
                    attack_damage=100,
                    ability_damage=100,
                    attack_speed=1.0,
                    ar=20,
                    mr=20,
                    attack_range=1,
                    crit_chance=10,
                    health_scale=1500,
                    attack_scale=100,
                    ability_scale=100,
                    ar_scale=30,
                    mr_scale=30,
                )

            # Create an easy to fill BaseCharacterAbility2.
            if not BaseCharacterAbility2.objects.filter(char_type=base_char).exists():
                sl = PRESTIGE_CAP - 5
                BaseCharacterAbility2.objects.create(
                    char_type=base_char,
                    version='0.0.0',
                    ability1_specs={"21": {}, "101": {}, "181": {}, "prestige-%d" % (1 + sl): {}},
                    ability2_specs={"41": {}, "121": {}, "201": {}, "prestige-%d" % (2 + sl): {}},
                    ability3_specs={"61": {}, "141": {}, "221": {}, "prestige-%d" % (4 + sl): {}},
                    ultimate_specs={"1": {}, "81": {}, "161": {}, "prestige-%d" % (3 + sl): {}, "prestige-%d" % (5 + sl): {}},
                )

            # Give testWilson a copy of the character if it doesn't exist.
            if not Character.objects.filter(user_id=21, char_type=base_char).exists():
                Character.objects.create(user_id=21, char_type=base_char, copies=1)


@admin.register(BaseCharacterUsage)
class BaseCharacterUsageAdmin(admin.ModelAdmin):
    actions = ('reset_to_zero', 'generate_base_character_usage_report',)

    def reset_to_zero(self, request, queryset):
        now = datetime.utcnow()
        queryset.update(num_games_buckets=default_base_character_usage_array(),
                        num_wins_buckets=default_base_character_usage_array(),
                        num_defense_games_buckets=default_base_character_usage_array(),
                        num_defense_wins_buckets=default_base_character_usage_array(),
                        last_reset_time=now)

    def generate_base_character_usage_report(self, request, queryset):
        start = datetime.utcnow()

        queryset = queryset.select_related('char_type')
        # Process data as dataframe
        df = get_base_character_usage_dataframe(queryset)

        # Get totals
        # Write as lists first for readability
        bucket_count = constants.NUMBER_OF_USAGE_BUCKETS
        df['games'] = df[[f'games bucket {f}' for f in range(0, bucket_count)]].sum(axis=1)
        df['wins'] = df[[f'wins bucket {f}' for f in range(0, bucket_count)]].sum(axis=1)
        df['defense games'] = df[[f'defense games bucket {f}' for f in range(0, bucket_count)]].sum(axis=1)
        df['defense wins'] = df[[f'defense wins bucket {f}' for f in range(0, bucket_count)]].sum(axis=1)
        df.drop(df.columns[df.columns.str.contains('bucket')], axis=1, inplace=True)  # Remove all buckets

        # Create other useful columns
        df = df[(df['defense games']+df['games']) != 0]  # Remove all rows with no games or defenses
        df.insert(2, 'win rate', df['wins'] / df['games'])  # Add win rate column
        df.insert(3, 'defense win rate', df['defense wins'] / df['defense games'])  # Defense win rate
        win_rate_average = df['win rate'].mean()
        defense_win_rate_average = df['defense win rate'].mean()
        df.insert(3, 'ΔWR', df['win rate'] - win_rate_average)
        df.insert(5, 'ΔDef WR', df['defense win rate'] - defense_win_rate_average)

        df = df.sort_values(by=['win rate'], ascending=False)  # Default sorting is by win rate, can be changed when viewing as a table

        end = datetime.utcnow()
        elapsed = end - start

        # Set context variables that'll be used by table template
        context = get_table_context(df)
        context['page_title'] = "Base Character Usage Report"
        context['other_data'] = [f'Time: {datetime.now()}']
        context['other_data'].append(f'Function runtime: {elapsed}')
        context['other_data'].append(f'Average Winrate: {"{:.2f}".format(100 * win_rate_average)}')
        context['other_data'].append(f'Average Defense Winrate: {"{:.2f}".format(100 * defense_win_rate_average)}')

        return render(request, 'table.html', context)


@admin.register(RogueAllowedAbilities)
class RogueAllowedAbilitiesAdmin(admin.ModelAdmin):
    list_filter = ('char_type', 'allowed')


@admin.register(MatchReplay)
class MatchReplayAdmin(admin.ModelAdmin):
    raw_id_fields = ('match',)


class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'message', 'sender', 'time_send')
    search_fields = ['=chat__id', 'chat__chat_name', 'message']
    raw_id_fields = ('chat',)


class HackerAlertAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'user', 'match_simulated', 'match_simulated_alert', 'verified_hacker', 'skip_simulation', 'timestamp',)
    list_filter = ('timestamp',)
    raw_id_fields = ('user', 'reporter')
    search_fields = ('=user__id',)
    actions = ('generate_hacker_report',)

    def generate_hacker_report(self, request, queryset):
        start = datetime.utcnow()

        if queryset:
            df = get_hacker_alert_dataframe(queryset)
            df['simulation flag rate'] = 100 * (df['flagged_sims'] / df['reports_processed'])
            context = get_table_context(df)
        else:
            context = {}
        end = datetime.utcnow()
        elapsed = end - start
        context['page_title'] = "Hacker Stats Report"
        context['other_data'] = [f'Time: {datetime.now()}']
        context['other_data'].append(f'Function runtime: {elapsed}')
        return render(request, 'table.html', context)


class GrassEventAdmin(admin.ModelAdmin, DynamicArrayMixin):
    raw_id_fields = ('user',)


class WorldPackAdmin(admin.ModelAdmin, DynamicArrayMixin):
    raw_id_fields = ('user',)


admin.site.register(DungeonStage, DungeonStageAdmin)
admin.site.register(DungeonProgress)
admin.site.register(DungeonBoss, DungeonBossAdmin)
admin.site.register(DungeonStats, DungeonStatsAdmin)

admin.site.register(BaseItem, BaseItemAdmin)
admin.site.register(BasePrestige)
admin.site.register(Character, CharacterAdmin)
admin.site.register(Item)

admin.site.register(Placement, PlacementAdmin)
admin.site.register(UserInfo, UserInfoAdmin)
admin.site.register(UserStats, UserStatsAdmin)
admin.site.register(Match)
admin.site.register(Inventory, InventoryAdmin)

admin.site.register(Chat)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(Friend)
admin.site.register(FriendRequest)
admin.site.register(Clan2)
admin.site.register(ClanMember, ClanMemberAdmin)
admin.site.register(ClanRequest)

admin.site.register(BaseQuest, BaseQuestAdmin)
admin.site.register(PlayerQuestDaily)
admin.site.register(PlayerQuestWeekly)

admin.site.register(ActiveCumulativeQuest, ActiveCumulativeQuestAdmin)
admin.site.register(ActiveDailyQuest, ActiveDailyQuestAdmin)
admin.site.register(ActiveWeeklyQuest, ActiveWeeklyQuestAdmin)

admin.site.register(BaseCode, BaseCodeAdmin)
admin.site.register(ClaimedCode)

admin.site.register(UserReferral)
admin.site.register(ReferralTracker)

admin.site.register(CreatorCode, CreatorCodeAdmin)
admin.site.register(CreatorCodeTracker)

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
admin.site.register(HackerAlert, HackerAlertAdmin)

admin.site.register(ClanPVEEvent)
admin.site.register(ClanPVEResult)
admin.site.register(ClanPVEStatus)
admin.site.register(ClanFarming)

admin.site.register(RelicShop, RelicShopAdmin)
admin.site.register(LevelBooster)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(StoryMode, StoryModeAdmin)
admin.site.register(Mail, MailAdmin)

admin.site.register(RegalRewards, RegalRewardsAdmin)
admin.site.register(ActivityPoints, ActivityPointsAdmin)

admin.site.register(AFKReward, AFKRewardAdmin)

admin.site.register(EventTimeTracker)
admin.site.register(GrassEvent, GrassEventAdmin)
admin.site.register(EventRewards)
admin.site.register(EloRewardTracker)
admin.site.register(BaseResourceShopItem, BaseResourceShopItemAdmin)
admin.site.register(ResourceShop)
admin.site.register(WorldPack, WorldPackAdmin)

admin.site.index_template = 'admin/custom_index.html'
admin.autodiscover()
