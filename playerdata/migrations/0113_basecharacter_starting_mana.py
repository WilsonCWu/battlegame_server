# Generated by Django 3.0.4 on 2021-02-17 23:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0112_auto_20210206_2118'),
    ]

    operations = [
        migrations.AddField(
            model_name='basecharacter',
            name='starting_mana',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
