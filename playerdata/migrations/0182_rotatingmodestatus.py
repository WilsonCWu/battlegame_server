# Generated by Django 3.0.4 on 2021-07-31 01:59

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0181_auto_20210727_1915'),
    ]

    operations = [
        migrations.CreateModel(
            name='RotatingModeStatus',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('stage', models.IntegerField(default=1)),
                ('character_state', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('rewards_claimed', models.IntegerField(default=0)),
            ],
        ),
    ]
