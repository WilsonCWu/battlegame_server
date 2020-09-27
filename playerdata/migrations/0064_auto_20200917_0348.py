# Generated by Django 3.0.4 on 2020-09-17 03:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('playerdata', '0063_auto_20200917_0043'),
    ]

    operations = [
        migrations.AddField(
            model_name='placement',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='userinfo',
            name='default_placement',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='playerdata.Placement'),
        ),
    ]
