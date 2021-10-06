# Generated by Django 3.0.4 on 2021-10-06 02:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0196_eventrewards'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='login_chest',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='login_chest', to='playerdata.Chest'),
        ),
    ]
