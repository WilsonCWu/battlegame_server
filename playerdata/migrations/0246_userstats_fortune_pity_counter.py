# Generated by Django 3.0.4 on 2022-04-12 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0245_auto_20220331_1858'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstats',
            name='fortune_pity_counter',
            field=models.IntegerField(default=0),
        ),
    ]