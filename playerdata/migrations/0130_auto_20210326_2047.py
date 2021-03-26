# Generated by Django 3.0.4 on 2021-03-26 20:47

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0129_auto_20210324_2219'),
    ]

    operations = [
        migrations.AddField(
            model_name='dungeonboss',
            name='team_comp',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dungeonboss',
            name='dungeon_type',
            field=models.IntegerField(choices=[(0, 'CAMPAIGN'), (1, 'TOWER'), (2, 'TUNNELS')], default=0),
        ),
        migrations.AlterField(
            model_name='dungeonboss',
            name='placement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='playerdata.Placement'),
        ),
        migrations.AlterField(
            model_name='dungeonstage',
            name='dungeon_type',
            field=models.IntegerField(choices=[(0, 'CAMPAIGN'), (1, 'TOWER'), (2, 'TUNNELS')], default=0),
        ),
    ]
