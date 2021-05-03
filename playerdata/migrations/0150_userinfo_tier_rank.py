# Generated by Django 3.0.4 on 2021-04-29 22:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0149_auto_20210428_2209'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinfo',
            name='tier_rank',
            field=models.IntegerField(choices=[(1, 'BRONZE_FIVE'), (2, 'BRONZE_FOUR'), (3, 'BRONZE_THREE'), (4, 'BRONZE_TWO'), (5, 'BRONZE_ONE'), (6, 'SILVER_FIVE'), (7, 'SILVER_FOUR'), (8, 'SILVER_THREE'), (9, 'SILVER_TWO'), (10, 'SILVER_ONE'), (11, 'GOLD_FIVE'), (12, 'GOLD_FOUR'), (13, 'GOLD_THREE'), (14, 'GOLD_TWO'), (15, 'GOLD_ONE'), (16, 'PLAT_FIVE'), (17, 'PLAT_FOUR'), (18, 'PLAT_THREE'), (19, 'PLAT_TWO'), (20, 'PLAT_ONE'), (21, 'DIAMOND_FIVE'), (22, 'DIAMOND_FOUR'), (23, 'DIAMOND_THREE'), (24, 'DIAMOND_TWO'), (25, 'DIAMOND_ONE'), (26, 'MASTER')], default=4),
        ),
    ]