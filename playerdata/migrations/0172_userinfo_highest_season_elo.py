# Generated by Django 3.0.4 on 2021-07-03 03:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0171_auto_20210630_2148'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinfo',
            name='highest_season_elo',
            field=models.IntegerField(default=0),
        ),
    ]
