# Generated by Django 3.0.4 on 2021-01-25 02:41

from django.db import migrations, models
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0109_auto_20210121_0042'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventory',
            name='last_collected_rewards',
            field=models.DateTimeField(default=playerdata.models.get_default_afk_datetime),
        ),
    ]
