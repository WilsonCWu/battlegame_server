# Generated by Django 3.0.4 on 2021-05-15 03:45

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_better_admin_arrayfield.models.fields
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0155_hackeralert'),
    ]

    operations = [
        migrations.CreateModel(
            name='LevelBooster',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('booster_level', models.IntegerField(default=0)),
                ('unlocked_slots', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)])),
                ('slots', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), default=playerdata.models.default_slot_list, size=None)),
                ('cooldown_slots', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.DateTimeField(blank=True, null=True), default=playerdata.models.default_cooldown_slot_list, size=None)),
            ],
        ),
        migrations.AddField(
            model_name='character',
            name='is_boosted',
            field=models.BooleanField(default=False),
        ),
    ]
