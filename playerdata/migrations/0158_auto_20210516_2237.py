# Generated by Django 3.0.4 on 2021-05-16 22:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0157_auto_20210515_2148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='levelbooster',
            name='booster_level',
            field=models.IntegerField(default=240),
        ),
    ]
