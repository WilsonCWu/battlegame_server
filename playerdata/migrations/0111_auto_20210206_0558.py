# Generated by Django 3.0.4 on 2021-02-06 05:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0110_auto_20210125_0241'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstats',
            name='longest_win_streak',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userstats',
            name='win_streak',
            field=models.IntegerField(default=0),
        ),
    ]
