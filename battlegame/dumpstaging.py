"""Dump staging data from the production database, with selected users."""

from django.apps import apps
from django.core import serializers

import playerdata.models


# Models to be ignored for exporting.
IGNORE_LIST = {
    # Unused model.
    'BaseCharacterAbility',
    # Abstract model.
    'StatModifiers',
    # Too big.
    'Match',
    'MatchReplay',
    # References users through other fields.
    'TournamentMatch',
    'ChatMessage',
    'ChatLastReadMessage',
    'Friend',
    'FriendRequest',
    'ReferralTracker',
    # Django metadata.
    'LogEntry',
    'Permission',
    'Group',
    'ContentType',
    'Session',
    'Token',
}


# User IDs to be exported for staging data. We could sample more users for this
# to be a bit more realistic, since right now QuickPlay match making will
# poll for quite a while to get an opponent with this sample.
USERS = [
    2833, # testDaniel2
    1250, # testYan
    21, # testWilson
    1, # battlegame
    78, # Some of these users placements depend on user 78
    23, # Yan's staff account
    20, # Daniel's staff account
]


def has_field(m, field):
    try:
        m._meta.get_field(field)
        return True
    except:
        return False


def get_models():
    """Get models for the staging database. This method returns the models
    ordered with respect to foreign key dependencies, and ignores models listed
    in the IGNORE_LIST.
    """
    for ac in apps.get_app_configs():
        if ac.models_module is None:
            continue
        for m in ac.get_models():
            if m.__name__ in IGNORE_LIST:
                continue
            yield m


def get_objects():
    """Get all objects for the staging database, with selected user IDs from
    USERS.
    """
    for m in get_models():
        # TODO: a more inclusive way to do this is to iterate through the
        # fields and check for foreign relations and cache the pks we dumped,
        # but this will do for now.
        if has_field(m, 'userinfo_id'):
            q = m.objects.filter(userinfo_id__in=USERS)
        elif has_field(m, 'user_id'):
            q = m.objects.filter(user_id__in=USERS)
        elif m.__name__ == 'User':
            q = m.objects.filter(id__in=USERS)
        else:
            q = m.objects.all()
        for obj in q:
            yield obj


def dump(outfile_name='dump.json'):
    with open(outfile_name, 'w') as f:
        serializers.serialize("json", get_objects(), indent=None, stream=f)
