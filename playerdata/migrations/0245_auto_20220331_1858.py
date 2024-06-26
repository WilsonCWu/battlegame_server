# Generated by Django 3.0.4 on 2022-03-31 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0244_auto_20220331_0027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expeditionmap',
            name='game_mode',
            field=models.IntegerField(choices=[(0, 'QuickPlay'), (1, 'Dungeon'), (2, 'Tournament'), (3, 'DailyDungeon'), (4, 'Moevasion'), (5, 'Sandbox'), (6, 'Replay'), (7, 'ClanPVE'), (8, 'MoveTester'), (9, 'Roguelike'), (10, 'AFKBattle'), (11, 'TurkeyRoguelike'), (12, 'StoryRoguelike')], default=12),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='ember',
            field=models.IntegerField(default=100),
        ),
    ]
