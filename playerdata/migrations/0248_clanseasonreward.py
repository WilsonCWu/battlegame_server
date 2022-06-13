# Generated by Django 3.0.4 on 2022-06-09 18:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0247_auto_20220418_1428'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClanSeasonReward',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('rank', models.IntegerField(default=-1)),
                ('is_claimed', models.BooleanField(default=True)),
            ],
        ),
    ]
