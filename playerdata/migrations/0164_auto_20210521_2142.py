# Generated by Django 3.0.4 on 2021-05-21 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0163_userstats_pvp_skips'),
    ]

    operations = [
        migrations.AddField(
            model_name='clanpvestatus',
            name='current_borrowed_character',
            field=models.IntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='clanpvestatus',
            name='current_boss',
            field=models.IntegerField(default=-1),
        ),
    ]