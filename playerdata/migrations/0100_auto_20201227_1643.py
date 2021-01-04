# Generated by Django 3.0.4 on 2020-12-27 16:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0099_auto_20201223_0209'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dungeonprogress',
            old_name='stage_id',
            new_name='campaign_stage',
        ),
        migrations.AddField(
            model_name='dungeonboss',
            name='dungeon_type',
            field=models.IntegerField(choices=[(0, 'CAMPAIGN'), (1, 'TOWER')], default=0),
        ),
        migrations.AddField(
            model_name='dungeonprogress',
            name='tower_stage',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='dungeonstage',
            name='dungeon_type',
            field=models.IntegerField(choices=[(0, 'CAMPAIGN'), (1, 'TOWER')], default=0),
        ),
        migrations.AddField(
            model_name='dungeonstage',
            name='story_text',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='dungeonstage',
            name='stage',
            field=models.IntegerField(null=True),
        ),
        migrations.AddConstraint(
            model_name='dungeonboss',
            constraint=models.UniqueConstraint(fields=('stage', 'dungeon_type'), name='unique_dungeonboss'),
        ),
        migrations.AddConstraint(
            model_name='dungeonstage',
            constraint=models.UniqueConstraint(fields=('stage', 'dungeon_type'), name='unique_stage'),
        ),
    ]