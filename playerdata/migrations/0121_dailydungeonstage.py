# Generated by Django 3.0.4 on 2021-03-04 06:33

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0120_dailydungeonstatus_run_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyDungeonStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage', models.IntegerField(default=0)),
                ('team_comp', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
            ],
        ),
    ]
