# Generated by Django 3.0.4 on 2020-07-11 21:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('playerdata', '0046_claimedreferral_userreferral'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferralTracker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.TextField()),
                ('converted', models.BooleanField(default=False)),
                ('referral', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.UserReferral')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.DeleteModel(
            name='ClaimedReferral',
        ),
    ]
