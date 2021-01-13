# Generated by Django 3.0.4 on 2021-01-13 23:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('playerdata', '0106_auto_20210109_1941'),
    ]

    operations = [
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_win', models.BooleanField()),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('attacker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('defender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opponent', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='match',
            index=models.Index(fields=['attacker', 'defender', 'uploaded_at'], name='playerdata__attacke_ec3d04_idx'),
        ),
    ]