# Generated by Django 3.0.4 on 2021-06-12 00:46

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django_better_admin_arrayfield.models.fields
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0166_auto_20210528_2143'),
    ]

    operations = [
        migrations.AddField(
            model_name='clanmember',
            name='last_farm_reward',
            field=models.DateField(default=playerdata.models.week_old_date),
        ),
        migrations.CreateModel(
            name='ClanFarming',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('daily_farms', django_better_admin_arrayfield.models.fields.ArrayField(base_field=django.contrib.postgres.fields.jsonb.JSONField(), default=playerdata.models.empty_farms, size=None)),
                ('previous_farm_reward', models.DateField(default=playerdata.models.week_old_date)),
                ('unclaimed_rewards', django.contrib.postgres.fields.jsonb.JSONField(default=playerdata.models.empty_rewards)),
                ('clan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.Clan2')),
            ],
        ),
    ]
