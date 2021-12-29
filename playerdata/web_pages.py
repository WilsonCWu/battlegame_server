from django.shortcuts import render
from django.shortcuts import redirect

from playerdata import constants
from playerdata.models import BaseCharacter


def privacy(request):
    return render(request, 'privacy.html', {})

def terms(request):
    return render(request, 'terms.html', {})

def install(request):
    return render(request, 'install.html', {})

def beta(request):
    return redirect("https://forms.gle/Xv7Bfx1a7fPjSU1E8")

def about(request):
    return render(request, 'about.html', {})

def chest_droprate(chest_type, rarity, num_rarity):
    rarity_odds = constants.REGULAR_CHAR_ODDS_PER_CHEST[chest_type - 1][rarity - 1] / 1000
    return round(rarity_odds / num_rarity, 3)

def info(request):
    mythical_droprates = []
    basechars = BaseCharacter.objects.filter(rollable=True, rarity__gt=1).order_by('rarity')
    num_rarity = [
        basechars.filter(rarity=2).count(),
        basechars.filter(rarity=3).count(),
        basechars.filter(rarity=4).count()
    ]

    for char in basechars:
        mythical_droprates.append({
            "name": char.name,
            "rarity": char.to_rarity_name,
            "rate": chest_droprate(constants.ChestType.MYTHICAL.value, char.rarity, num_rarity[char.rarity - 2])
        })


    return render(request, 'info.html', {
        'mythical_droprates': mythical_droprates,
    })
