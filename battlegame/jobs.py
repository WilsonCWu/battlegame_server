"""One off jobs."""

from django.db import transaction
from playerdata.models import *

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
def backfill_cumulative_quests():
    users = User.objects.all()
    # for all playerquest
    bulk_quests2 = []
    for user in users:
        player_quests = PlayerQuestCumulative.objects.filter(user=user)
        if PlayerQuestCumulative2.objects.filter(user=user).exists():
            continue
        quests2 = PlayerQuestCumulative2(user=user)
        quests2.completed_quests = []
        quests2.claimed_quests = []
        for quest in player_quests:
            if quest.completed:
                quests2.completed_quests.append(quest.base_quest_id)
            if quest.claimed:
                quests2.claimed_quests.append(quest.base_quest_id)

        bulk_quests2.append(quests2)

    PlayerQuestCumulative2.objects.bulk_create(bulk_quests2)


@transaction.atomic
def fix_clan_count():
    for c in Clan2.objects.all():
        real_count = ClanMember.objects.filter(clan2=c).count()
        if c.num_members != real_count:
            c.num_members = real_count
            c.save()


@transaction.atomic
def backfill_level_booster():
    for user in User.objects.all():
        _, _ = LevelBooster.objects.get_or_create(user=user)


@transaction.atomic
def backfill_relics():
    for user in User.objects.all():
        _, _ = RelicShop.objects.get_or_create(user=user)


@transaction.atomic
def backfill_pve_status():
    for member in ClanMember.objects.all():
        if not member.pve_character_lending:
            cs = Character.objects.filter(user_id=member.userinfo_id)[:3]
            member.pve_character_lending=[c.char_id for c in cs]
            member.save()
