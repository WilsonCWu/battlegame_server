# Generated by Django 3.0.4 on 2021-03-15 03:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0126_auto_20210314_1804'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstats',
            name='chest_counter',
            field=models.IntegerField(default=0),
        ),
    ]
