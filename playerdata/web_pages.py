from django.shortcuts import render
from django.shortcuts import redirect
from playerdata.models import User, ClaimedCode, BaseCode, Mail

from playerdata import constants, redemptioncodes
from playerdata.forms import RedeemInboxForm
from playerdata.login import UserRecoveryTokenGenerator
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


def redeem(request):
    if request.method != 'POST':
        return render(request, 'redeem.html', {})

    form = RedeemInboxForm(request.POST)
    if not form.is_valid():
        return render(request, 'redeem.html', {'error': 'Invalid form contains errors'})

    otp = form.cleaned_data['otp']
    code = form.cleaned_data['code']

    user_id_index = otp.find("-")
    if user_id_index == -1:
        return render(request, 'redeem.html', {'error': 'Invalid token, try copying it again from Settings > Transfer'})

    user_id = otp[:user_id_index]  # Grab the userid from the otp token
    token = otp[user_id_index + 1:]  # Grab the rest from the otp token

    try:
        user = User.objects.get(id=user_id)
    except:
        return render(request, 'redeem.html', {'error': 'Invalid token, try copying it again from Settings > Transfer'})

    generator = UserRecoveryTokenGenerator()
    if not generator.check_token(user, token):
        return render(request, 'redeem.html', {'error': 'Invalid token, try copying it again from Settings > Transfer'})

    basecode = BaseCode.objects.filter(code=code).first()
    if basecode is None:
        return render(request, 'redeem.html', {'error': 'Invalid code'})

    if not redemptioncodes.is_valid_code(basecode):
        return render(request, 'redeem.html', {'error': 'Code has expired'})

    # if not already claimed token
    if ClaimedCode.objects.filter(user=user, code=basecode).exists():
        return render(request, 'redeem.html', {'error': 'Invalid code, already claimed'})

    # send inbox
    sender_id = 1
    sender = User.objects.get(id=sender_id)
    pfp_id = sender.userinfo.profile_picture

    Mail.objects.create(title="Redeem Your Code", message="Claim your rewards!\n\nBattle on adventurer!",
                        sender_id=sender_id, receiver_id=user_id,
                        code=basecode, sender_profile_picture_id=pfp_id,
                        has_unclaimed_reward=True)
    return render(request, 'redeem.html', {'success': 'Check your in-game Inbox to claim your rewards!'})


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
