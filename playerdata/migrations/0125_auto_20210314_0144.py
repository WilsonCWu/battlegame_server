# Generated by Django 3.0.4 on 2021-03-14 01:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0124_userinfo_best_daily_dungeon_stage'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstats',
            name='gold_pity_counter',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userstats',
            name='mythic_pity_counter',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userstats',
            name='silver_pity_counter',
            field=models.IntegerField(default=0),
        ),
    ]
