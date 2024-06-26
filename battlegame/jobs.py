"""One off jobs."""
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction

from playerdata import formulas, matcher, rolls, leaderboards, grass_event, level_booster
from playerdata.models import *
from playerdata.questupdater import QuestUpdater


def clean_placements():
    for p in Placement.objects.all():
        changed = False

        # If position is -1, there should be no characters equipped.
        if p.pos_1 == -1 and p.char_1 is not None:
            changed = True
            p.char_1 = None
        if p.pos_2 == -1 and p.char_2 is not None:
            changed = True
            p.char_2 = None
        if p.pos_3 == -1 and p.char_3 is not None:
            changed = True
            p.char_3 = None
        if p.pos_4 == -1 and p.char_4 is not None:
            changed = True
            p.char_4 = None
        if p.pos_5 == -1 and p.char_5 is not None:
            changed = True
            p.char_5 = None

        # If character is null, there shouldn't be a position.
        if p.char_1 is None and p.pos_1 != -1:
            changed = True
            p.pos_1 = -1
        if p.char_2 is None and p.pos_2 != -1:
            changed = True
            p.pos_2 = -1
        if p.char_3 is None and p.pos_3 != -1:
            changed = True
            p.pos_3 = -1
        if p.char_4 is None and p.pos_4 != -1:
            changed = True
            p.pos_4 = -1
        if p.char_5 is None and p.pos_5 != -1:
            changed = True
            p.pos_5 = -1

        # Try to give this placement at least 1 character.
        if p.char_1 is None and p.char_2 is None and p.char_3 is None and \
                p.char_4 is None and p.char_5 is None and p.user is not None:
            q = Character.objects.filter(user=p.user)
            if q:
                changed = True
                p.pos_1 = 1
                p.char_1 = q[0]

        if changed:
            p.save()


@transaction.atomic
def backfill_clans():
    for clan in Clan.objects.all():
        equiv = Clan2.objects.filter(name=clan.name)
        if equiv:
            continue

        Clan2.objects.create(
            name=clan.name,
            description=clan.description,
            chat=clan.chat,
            time_started=clan.time_started,
            elo=clan.elo,
            profile_picture=clan.profile_picture,
            num_members=clan.num_members,
            cap=clan.cap,
        )

    cm_objs = ClanMember.objects.all()
    for cm in cm_objs:
        if cm.clan:
            clan = Clan2.objects.get(name=cm.clan.name)
            cm.clan2 = clan
    ClanMember.objects.bulk_update(cm_objs, ['clan2'])

    cr_objs = ClanRequest.objects.all()
    for cr in cr_objs:
        if cr.clan:
            clan = Clan2.objects.get(name=cr.clan.name)
            cr.clan2 = clan
    ClanRequest.objects.bulk_update(cr_objs, ['clan2'])


@transaction.atomic
def fix_clan_count():
    for c in Clan2.objects.all():
        real_count = ClanMember.objects.filter(clan2=c).count()
        if c.num_members != real_count:
            c.num_members = real_count
            c.save()


@transaction.atomic
def backfill_pve_status():
    for member in ClanMember.objects.all():
        if not member.pve_character_lending:
            cs = Character.objects.filter(user_id=member.userinfo_id)[:3]
            member.pve_character_lending = [c.char_id for c in cs]
            member.save()


@transaction.atomic
def shorten_descriptions():
    users = UserInfo.objects.all()
    for user in users:
        if len(user.description) > 96:
            user.description = user.description[0:96]

    UserInfo.objects.bulk_update(users, ['description'])

    clans = Clan2.objects.all()
    for clan in clans:
        if len(clan.description) > 96:
            clan.description = clan.description[0:96]
    Clan2.objects.bulk_update(clans, ['description'])


@transaction.atomic
def reset_expiration_20pack():
    # reset all the expiration dates to give everyone a chance
    reward_packs = ChapterRewardPack.objects.all()
    for pack in reward_packs:
        pack.expiration_date = timezone.now() + timedelta(days=14)

    ChapterRewardPack.objects.bulk_update(reward_packs, ['expiration_date'])


@transaction.atomic
def backfill_highest_seasonelo():
    userinfos = UserInfo.objects.all()
    for userinfo in userinfos:
        userinfo.highest_season_elo = userinfo.elo

    UserInfo.objects.bulk_update(userinfos, ['highest_season_elo'])


@transaction.atomic
def backfill_storymode():
    for user in User.objects.all():
        _, _ = StoryMode.objects.get_or_create(user=user)


@transaction.atomic
def backfill_vip_levels():
    userinfos = UserInfo.objects.all().select_related('user__inventory')
    for userinfo in userinfos:
        player_level = formulas.exp_to_level(userinfo.player_exp)

        if player_level < 15:
            exp = 0
        elif player_level < 30:
            exp = 50
        elif player_level < 35:
            exp = 100
        elif player_level < 40:
            exp = 200
        elif player_level < 45:
            exp = 300
        elif player_level < 50:
            exp = 650
        elif player_level < 55:
            exp = 1000
        elif player_level < 60:
            exp = 1500
        elif player_level < 65:
            exp = 2000
        elif player_level < 70:
            exp = 3000
        elif player_level < 75:
            exp = 4000
        elif player_level < 80:
            exp = 5500
        elif player_level < 85:
            exp = 7000
        elif player_level < 90:
            exp = 8500
        elif player_level < 95:
            exp = 10000
        elif player_level < 100:
            exp = 12000
        elif player_level < 105:
            exp = 14000
        elif player_level < 110:
            exp = 17000
        elif player_level < 115:
            exp = 20000
        elif player_level < 120:
            exp = 2500
        else:
            exp = 30000

        userinfo.vip_exp = exp

        # backfill the purchased gems if the person bought something more than the free deal
        pt = PurchasedTracker.objects.filter(user=userinfo.user)
        for purchase in pt:
            userinfo.vip_exp += formulas.cost_to_vip_exp(formulas.product_to_dollar_cost(purchase.purchase_id))

    UserInfo.objects.bulk_update(userinfos, ['vip_exp'])


@transaction.atomic
def backfill_rotating_mode():
    for user in User.objects.all():
        _, _ = RotatingModeStatus.objects.get_or_create(user=user)


# Send an inbox message to userid_list
# if userid_list = ['all'] then it sends to all users
#
# Usage:
# > python manage.py shell_plus
#
# > send_inbox("Welcome", "heya welcome to the game!", [349, 348])  # Sends a basic mail to the userid_list inboxes
# > send_inbox("Welcome","heya welcome to the game!", ['all'], 500) # Sends mail to all users and also creates a gem reward of 500

@transaction.atomic
def send_inbox(title, message, userid_list, gems=0, sender_id=10506):
    if userid_list == ['all']:
        userid_list = User.objects.values_list('id', flat=True)

    basecode = None
    if gems != 0:
        curr_time = datetime.now(timezone.utc)
        codename = "inboxcode_" + curr_time.strftime("%m_%d_%Y_%H:%M:%S")
        basecode = BaseCode.objects.create(code=codename, num_left=-1, start_time=curr_time,
                                           end_time=curr_time + timedelta(days=30), gems=gems)

    sender = User.objects.get(id=sender_id)
    pfp_id = sender.userinfo.profile_picture
    has_unclaimed_reward = basecode is not None

    mails = []
    for userid in userid_list:
        mails.append(Mail(title=title, message=message,
                          sender_id=sender_id, receiver_id=userid,
                          code=basecode, sender_profile_picture_id=pfp_id,
                          has_unclaimed_reward=has_unclaimed_reward))

    Mail.objects.bulk_create(mails)


@transaction.atomic
def generate_bots_bulk(start_elo, end_elo, num_bots_per_elo_range):
    matcher.generate_bots_bulk(start_elo, end_elo, num_bots_per_elo_range)


# Creates a test user account with full resources and all characters
@transaction.atomic
def new_test_user(name: str):
    password = secrets.token_urlsafe(35)

    user = get_user_model().objects.create_user(username=name, password=password)
    print("username: " + name)
    print("password: " + password)

    user.inventory.gems = 1000000
    user.inventory.coins = 50000000
    user.inventory.dust = 1000000
    user.inventory.save()

    basechars = BaseCharacter.objects.filter(rollable=True)
    for basechar in basechars:
        rolls.insert_character(user, basechar.char_type)

    chars = Character.objects.filter(user=user)
    for char in chars:
        char.level = 81
        char.save()


@transaction.atomic
def backfill_regal_rewards():
    for user in User.objects.all():
        _, _ = RegalRewards.objects.get_or_create(user=user)


@transaction.atomic
def backfill_activity_points():
    for user in User.objects.all():
        _, _ = ActivityPoints.objects.get_or_create(user=user)


@transaction.atomic
def backfill_cumulative_stats():
    trackers = CumulativeTracker.objects.all()
    tracker_dict = {}

    for tracker in trackers:
        if tracker.user.id not in tracker_dict:
            tracker_dict[tracker.user.id] = {tracker.type: tracker.progress}
        else:
            tracker_dict[tracker.user.id][tracker.type] = tracker.progress

    user_stats = UserStats.objects.all()
    for stat in user_stats:
        if stat.user.id in tracker_dict:
            stat.cumulative_stats = tracker_dict[stat.user.id]

    UserStats.objects.bulk_update(user_stats, ['cumulative_stats'])


@transaction.atomic
def backfill_afk_rewards():
    for user in User.objects.all():
        _, _ = AFKReward.objects.get_or_create(user=user)


@transaction.atomic
def backfill_event_rewards():
    for user in User.objects.all():
        _, _ = EventRewards.objects.get_or_create(user=user)


@transaction.atomic
def backfill_login_chest():
    invs = Inventory.objects.all()
    for inv in invs:
        if inv.login_chest is None:
            login_chest = Chest.objects.create(user=inv.user, rarity=constants.ChestType.LOGIN_GEMS.value,
                                               locked_until=timezone.now())
            inv.login_chest = login_chest

    Inventory.objects.bulk_update(invs, ['login_chest'])


@transaction.atomic
def backfill_creatorcode():
    for user in User.objects.all():
        _, _ = CreatorCodeTracker.objects.get_or_create(user=user, created_time=None, code=None)


def check_placement_correctness():
    dungeons = DungeonBoss.objects.all()
    for dungeon in dungeons:
        if dungeon.team_comp:
            try:
                validate_placement_json(dungeon.team_comp)
            except ValidationError as e:
                print(f'Dungeon Type: {dungeon.dungeon_type}, Stage: {dungeon.stage}. Error: {e.message}')


@transaction.atomic
def remove_nonactive_cumulative_quests():
    player_quests = PlayerQuestCumulative2.objects.all()
    active_quests_ids = ActiveCumulativeQuest.objects.values_list('base_quest_id', flat=True)

    for player_quest in player_quests:
        # Filter out all the non-active quests
        player_quest.completed_quests = [quest for quest in player_quest.completed_quests if quest in active_quests_ids]

    PlayerQuestCumulative2.objects.bulk_update(player_quests, ['completed_quests'])


@transaction.atomic
def update_redis_player_elos():
    userinfos = UserInfo.objects.filter(elo__gt=0)
    users_dict = {}
    for userinfo in userinfos:
        users_dict[userinfo.user_id] = userinfo.elo

    leaderboards.bulk_update_redis_ranking(users_dict, leaderboards.pvp_ranking_key())


@transaction.atomic()
def reset_grass_event():
    grass_events = GrassEvent.objects.all()

    for event in grass_events:
        event.cur_floor = 1
        event.ladder_index = -1
        event.tickets = 0
        event.unclaimed_dynamite = 3
        event.dynamite_left = 1
        event.claimed_tiles = []
        event.rewards_left = default_grass_rewards_left()

    GrassEvent.objects.bulk_update(grass_events, ['cur_floor', 'ladder_index', 'tickets',
                                                  'unclaimed_dynamite', 'dynamite_left', 'claimed_tiles',
                                                  'rewards_left'])


def backfill_ascend_quests():
    users = User.objects.filter(userinfo__elo__gt=0).select_related('playerquestcumulative2', 'userstats').prefetch_related('character_set__char_type')

    for user in users:
        total_ascensions = sum([char.prestige for char in user.character_set.all()])
        QuestUpdater.set_progress_by_type(user, constants.ASCEND_X_HEROES, total_ascensions)


def backfill_Levelbooster():
    lvl_boosters = LevelBooster.objects.all().select_related('user__dungeonprogress')
    for lvl_booster in lvl_boosters:
        if lvl_booster.slots[0] != -1:
            lvl_booster.is_active = True
            lvl_booster.is_enhanced = True
        if lvl_booster.user.dungeonprogress.campaign_stage >= constants.LEVEL_BOOSTER_UNLOCK_STAGE:
            lvl_booster.is_active = True
        lvl_booster.slots_bought = lvl_booster.unlocked_slots

    LevelBooster.objects.bulk_update(lvl_boosters, ['is_active', 'is_enhanced', 'slots_bought'])


# One time job: slots are all the same fixed length right now
# this trims slots to be exactly the number of available slots makes it possible to add more slots easily
# (including if we bump the max slot size with more new chars)
@transaction.atomic()
def reformat_lvlboost_slots():
    lvl_boosters = LevelBooster.objects.all()
    for lvl_booster in lvl_boosters:
        lvl_booster.slots = lvl_booster.slots[:lvl_booster.unlocked_slots]
        lvl_booster.cooldown_slots = lvl_booster.cooldown_slots[:lvl_booster.unlocked_slots]

    LevelBooster.objects.bulk_update(lvl_boosters, ['slots', 'cooldown_slots'])


@transaction.atomic()
def backfill_char_story_mode(char_type: int):
    stories = StoryMode.objects.all()
    for story in stories:
        if char_type not in story.available_stories:
            story.available_stories.append(char_type)
    StoryMode.objects.bulk_update(stories, ['available_stories'])


@transaction.atomic()
def clawback_levelbooster_levels():
    lvl_boosters = LevelBooster.objects.filter(is_enhanced=True).select_related('user__inventory')
    updated_inventories = []
    for lvl_booster in lvl_boosters:
        refunded_costs = level_booster.refund_costs(lvl_booster.booster_level)

        lvl_booster.booster_level, remaining_coins, remaining_dust = level_booster.resources_to_levels_backfill(refunded_costs)
        lvl_booster.user.inventory.coins += remaining_coins
        lvl_booster.user.inventory.dust += remaining_dust

        updated_inventories.append(lvl_booster.user.inventory)

    LevelBooster.objects.bulk_update(lvl_boosters, ['booster_level'])
    Inventory.objects.bulk_update(updated_inventories, ['coins', 'dust'])

    ids = list(lvl_boosters.values_list('user_id', flat=True))
    msg = "From the latest Star Seeker changes, we've shifted the cost of not needing more than 5 manually leveled characters into the Star Seeker. As part of this reorganization, we've adjusted your current Star Seeker levels to match the new costs (you shouldn't see more than a few levels adjustment). We apologize for any inconvenience and have given out a gem reward as compensation as well.\n\nThank you and battle on!"
    send_inbox("Star Seeker Compensation", msg, ids, 2000)


@transaction.atomic()
def backfill_wishlist():
    Wishlist.objects.filter(user__dungeonprogress__campaign_stage__gte=constants.WISHLIST_UNLOCK_STAGE, is_active=False).update(is_active=True)


@transaction.atomic()
def backfill_lvl_booster():
    LevelBooster.objects.filter(user__dungeonprogress__campaign_stage__gte=constants.LEVEL_BOOSTER_UNLOCK_STAGE, is_active=False).update(is_active=True)


@transaction.atomic()
def backfill_clan_rewards():
    clan_seasons = []
    for user in User.objects.filter(clanseasonreward__isnull=True):
        clan_seasons.append(ClanSeasonReward(user=user))

    ClanSeasonReward.objects.bulk_create(clan_seasons)


@transaction.atomic
def update_redis_clan_rankings():
    clans = Clan2.objects.all()
    clans_dict = {}
    for clan in clans:
        clans_dict[clan.name] = clan.elo

    leaderboards.bulk_update_redis_ranking(clans_dict, leaderboards.clan_ranking_key())
