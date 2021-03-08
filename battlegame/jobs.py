"""One off jobs."""

from playerdata.models import Placement
from playerdata.models import Character

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
