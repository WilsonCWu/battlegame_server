# Generated by Django 3.0.4 on 2020-10-23 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0073_merge_20201021_2031'),
    ]

    operations = [
        migrations.AddField(
            model_name='basecharacter',
            name='attack_speed',
            field=models.FloatField(default=1.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='baseitem',
            name='ability_flat',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='baseitem',
            name='ability_mult',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='baseitem',
            name='attack_speed_mult',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
