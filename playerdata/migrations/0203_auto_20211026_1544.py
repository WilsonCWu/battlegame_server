# Generated by Django 3.0.4 on 2021-10-26 15:44

from django.db import migrations, models
import django.utils.timezone
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0202_basecharacterusage_last_reset_time'),
    ]

    operations = [
        migrations.RenameField(
            model_name='afkreward',
            old_name='runes_to_be_converted',
            new_name='reward_ticks',
        ),
        migrations.RemoveField(
            model_name='afkreward',
            name='leftover_shards',
        ),
        migrations.RemoveField(
            model_name='inventory',
            name='last_collected_rewards',
        ),
        migrations.AddField(
            model_name='afkreward',
            name='last_collected_time',
            field=models.DateTimeField(default=playerdata.models.get_default_afk_datetime),
        ),
        migrations.AddField(
            model_name='afkreward',
            name='leftover_shard_intervals',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='afkreward',
            name='last_eval_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='afkreward',
            name='unclaimed_dust',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='afkreward',
            name='unclaimed_gold',
            field=models.FloatField(default=0),
        ),
    ]