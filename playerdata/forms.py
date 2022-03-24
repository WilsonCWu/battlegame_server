from django import forms


class RedeemInboxForm(forms.Form):
    otp = forms.CharField(max_length=34)
    code = forms.CharField(max_length=34)


