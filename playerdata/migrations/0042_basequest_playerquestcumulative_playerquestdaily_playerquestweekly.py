# Generated by Django 3.0.4 on 2020-06-23 15:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('playerdata', '0041_dungeonprogress_dungeonstage'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseQuest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField()),
                ('type', models.IntegerField()),
                ('total', models.IntegerField()),
                ('gems', models.IntegerField(null=True)),
                ('coins', models.IntegerField(null=True)),
                ('char_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseCharacter')),
                ('item_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseItem')),
            ],
        ),
        migrations.CreateModel(
            name='PlayerQuestWeekly',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress', models.IntegerField(default=0)),
                ('completed', models.BooleanField(default=False)),
                ('claimed', models.BooleanField(default=False)),
                ('expiration_date', models.DateTimeField()),
                ('base_quest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseQuest')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PlayerQuestDaily',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress', models.IntegerField(default=0)),
                ('completed', models.BooleanField(default=False)),
                ('claimed', models.BooleanField(default=False)),
                ('expiration_date', models.DateTimeField()),
                ('base_quest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseQuest')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PlayerQuestCumulative',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress', models.IntegerField(default=0)),
                ('completed', models.BooleanField(default=False)),
                ('claimed', models.BooleanField(default=False)),
                ('base_quest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseQuest')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
