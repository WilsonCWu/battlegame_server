# Generated by Django 3.0.4 on 2021-06-17 14:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('playerdata', '0168_wishlist'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChapterRewardPack',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('is_active', models.BooleanField(default=False)),
                ('last_completed', models.IntegerField(default=-1)),
                ('last_claimed', models.IntegerField(default=-1)),
                ('type', models.IntegerField(choices=[(0, 'CHAPTER19'), (1, 'CHAPTER25'), (2, 'CHAPTER30')], default=0)),
            ],
        ),
    ]
