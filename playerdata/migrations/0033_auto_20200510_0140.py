# Generated by Django 3.0.4 on 2020-05-10 01:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0032_auto_20200507_0033'),
    ]

    operations = [
        migrations.AddField(
            model_name='clan',
            name='num_members',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='friend',
            name='chat',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='playerdata.Chat'),
        ),
    ]
