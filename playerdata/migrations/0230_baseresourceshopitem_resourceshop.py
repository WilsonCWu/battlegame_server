# Generated by Django 3.0.4 on 2022-01-12 00:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_better_admin_arrayfield.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0229_basecharacterstats_starting_ability_ticks'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseResourceShopItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost_type', models.IntegerField(choices=[(0, 'GOLD'), (1, 'GEMS')])),
                ('cost_value', models.IntegerField(default=0)),
                ('reward_type', models.TextField(choices=[('coins', 'COINS'), ('gems', 'GEMS'), ('essence', 'DUST'), ('relic_stone', 'RELIC_STONES'), ('rare_shards', 'RARE_SHARDS'), ('epic_shards', 'EPIC_SHARDS'), ('legendary_shards', 'LEGENDARY_SHARDS'), ('dust_fast_reward_hours', 'DUST_FAST_REWARDS'), ('coins_fast_reward_hours', 'COINS_FAST_REWARDS'), ('champ_badge', 'CHAMP_BADGE'), ('regal_points', 'REGAL_POINTS'), ('char_id', 'CHAR_ID'), ('item_id', 'ITEM_ID'), ('profile_pic', 'PROFILE_PIC'), ('pet_id', 'PET_ID')])),
                ('reward_value', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='ResourceShop',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('purchased_items', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
            ],
        ),
    ]
