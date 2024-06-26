# Generated by Django 3.0.4 on 2021-11-30 14:56

from django.db import migrations, models
import django_better_admin_arrayfield.models.fields
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0220_chatmessage_replay_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='basecharacterusage',
            name='num_defense_games_buckets',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), default=playerdata.models.default_base_character_usage_array, size=None),
        ),
        migrations.AddField(
            model_name='basecharacterusage',
            name='num_defense_wins_buckets',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), default=playerdata.models.default_base_character_usage_array, size=None),
        ),
        migrations.AddField(
            model_name='basecharacterusage',
            name='num_games_buckets',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), default=playerdata.models.default_base_character_usage_array, size=None),
        ),
        migrations.AddField(
            model_name='basecharacterusage',
            name='num_wins_buckets',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), default=playerdata.models.default_base_character_usage_array, size=None),
        ),
    ]
