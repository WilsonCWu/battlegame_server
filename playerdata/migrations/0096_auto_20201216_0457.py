# Generated by Django 3.0.4 on 2020-12-16 04:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0095_auto_20201207_0524'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basequest',
            name='coins',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='basequest',
            name='dust',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='basequest',
            name='gems',
            field=models.IntegerField(default=0),
        ),
    ]
