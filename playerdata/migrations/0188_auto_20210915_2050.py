# Generated by Django 3.0.4 on 2021-09-15 20:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0187_regalrewards'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityPoints',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('daily_last_completed', models.IntegerField(default=-1)),
                ('daily_last_claimed', models.IntegerField(default=-1)),
                ('weekly_last_completed', models.IntegerField(default=-1)),
                ('weekly_last_claimed', models.IntegerField(default=-1)),
                ('daily_points', models.IntegerField(default=0)),
                ('weekly_points', models.IntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='basequest',
            name='points',
            field=models.IntegerField(default=0),
        ),
    ]
