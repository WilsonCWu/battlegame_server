# Generated by Django 3.0.4 on 2020-08-17 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0052_auto_20200811_0520'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinfo',
            name='tourney_elo',
            field=models.IntegerField(default=0),
        ),
    ]
