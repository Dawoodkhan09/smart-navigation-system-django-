# Multi-campus support, part 1/3: create Campus and add a nullable
# `campus` FK to Location/GraphNode/BoundaryPoint. Nullable for now so
# this is safe to run against a database that already has rows (existing
# PythonAnywhere data) - 0003 backfills every row onto one Campus, then
# 0004 makes the field required to match the final model definition.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Campus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('slug', models.SlugField(help_text='Used in the campus URL, e.g. /c/main-campus/.', max_length=160, unique=True)),
                ('center_latitude', models.FloatField(validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ('center_longitude', models.FloatField(validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ('default_zoom', models.PositiveSmallIntegerField(default=17)),
                ('walking_speed_m_per_min', models.FloatField(default=80, validators=[django.core.validators.MinValueValidator(1)])),
                ('default_geofence_radius', models.FloatField(default=50, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(2000)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'campuses',
            },
        ),
        migrations.AddField(
            model_name='location',
            name='campus',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='locations', to='campus.campus'),
        ),
        migrations.AddField(
            model_name='graphnode',
            name='campus',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='graph_nodes', to='campus.campus'),
        ),
        migrations.AddField(
            model_name='boundarypoint',
            name='campus',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='boundary_points', to='campus.campus'),
        ),
    ]
