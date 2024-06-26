# Generated by Django 3.0.4 on 2022-03-30 18:24

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import playerdata.constants


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0241_storyquest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpeditionMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mapkey', models.CharField(max_length=50)),
                ('game_mode', models.IntegerField(choices=[(0, 'QuickPlay'), (1, 'Dungeon'), (2, 'Tournament'), (3, 'DailyDungeon'), (4, 'Moevasion'), (5, 'Sandbox'), (6, 'Replay'), (7, 'ClanPVE'), (8, 'MoveTester'), (9, 'Roguelike'), (10, 'AFKBattle'), (11, 'TurkeyRoguelike')], default=9)),
                ('version', models.CharField(default='0.0.0', max_length=30)),
                ('map_json', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='expeditionmap',
            index=models.Index(fields=['mapkey', 'game_mode'], name='playerdata__mapkey_367762_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='expeditionmap',
            unique_together={('mapkey', 'game_mode', 'version')},
        ),
    ]
