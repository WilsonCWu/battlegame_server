# Generated by Django 3.0.4 on 2020-08-27 03:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0057_auto_20200826_0232'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinfo',
            name='prev_tourney_elo',
            field=models.IntegerField(default=0),
        ),
    ]
