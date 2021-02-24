# Generated by Django 3.0.4 on 2021-02-24 20:30

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0117_auto_20210224_0219'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyDungeonStatus',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('is_golden', models.BooleanField(default=False)),
                ('stage', models.IntegerField(default=0)),
                ('character_state', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
            ],
        ),
    ]
