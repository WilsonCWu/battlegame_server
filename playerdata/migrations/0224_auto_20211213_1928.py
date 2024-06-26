# Generated by Django 3.0.4 on 2021-12-13 19:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0223_auto_20211209_1728'),
    ]

    operations = [
        migrations.AddField(
            model_name='basequest',
            name='coins_fast_reward_hours',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='basequest',
            name='dust_fast_reward_hours',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='dust',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='gems',
            field=models.IntegerField(default=0),
        ),
    ]
