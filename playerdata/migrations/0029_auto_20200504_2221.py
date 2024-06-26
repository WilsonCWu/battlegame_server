# Generated by Django 3.0.4 on 2020-05-04 22:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0028_auto_20200504_2035'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clanmember',
            name='clan',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='playerdata.Clan'),
        ),
        migrations.AlterField(
            model_name='clanmember',
            name='userinfo',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='playerdata.UserInfo'),
        ),
    ]
