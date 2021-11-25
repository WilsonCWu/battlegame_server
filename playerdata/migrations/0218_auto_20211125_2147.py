# Generated by Django 3.0.4 on 2021-11-25 21:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0217_userinfo_last_login'),
    ]

    operations = [
        migrations.AddField(
            model_name='basedeal',
            name='is_premium',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userinfo',
            name='is_purchaser',
            field=models.BooleanField(default=False),
        ),
    ]