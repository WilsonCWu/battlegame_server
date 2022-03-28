# Generated by Django 3.0.4 on 2022-03-28 19:09

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0240_auto_20220326_2019'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoryQuest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=-1)),
                ('title', models.TextField()),
                ('description', models.TextField()),
                ('dialog_1', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, validators=[playerdata.models.validate_char_dialog])),
                ('dialog_2', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, validators=[playerdata.models.validate_char_dialog])),
                ('char_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseCharacter')),
            ],
            options={
                'unique_together': {('char_type', 'order')},
            },
        ),
    ]
