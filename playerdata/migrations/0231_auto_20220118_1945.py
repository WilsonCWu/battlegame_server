# Generated by Django 3.0.4 on 2022-01-18 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0230_baseresourceshopitem_resourceshop'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baseresourceshopitem',
            name='cost_type',
            field=models.TextField(choices=[('coins', 'COINS'), ('gems', 'GEMS'), ('essence', 'DUST'), ('relic_stone', 'RELIC_STONES'), ('rare_shards', 'RARE_SHARDS'), ('epic_shards', 'EPIC_SHARDS'), ('legendary_shards', 'LEGENDARY_SHARDS'), ('dust_fast_reward_hours', 'DUST_FAST_REWARDS'), ('coins_fast_reward_hours', 'COINS_FAST_REWARDS'), ('champ_badge', 'CHAMP_BADGE'), ('regal_points', 'REGAL_POINTS'), ('char_id', 'CHAR_ID'), ('item_id', 'ITEM_ID'), ('profile_pic', 'PROFILE_PIC'), ('pet_id', 'PET_ID')]),
        ),
    ]
