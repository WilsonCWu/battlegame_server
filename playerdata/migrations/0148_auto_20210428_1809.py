# Generated by Django 3.0.4 on 2021-04-28 18:09

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0147_auto_20210427_1723'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchReplay',
            fields=[
                ('match', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='playerdata.Match')),
                ('seed', models.IntegerField(blank=True, null=True)),
                ('attacking_team', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('defending_team', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='match',
            name='attacker_team',
        ),
        migrations.RemoveField(
            model_name='match',
            name='defender_team',
        ),
        migrations.RemoveField(
            model_name='match',
            name='seed',
        ),
    ]
