# Multi-campus support, part 3/3: now that 0003 backfilled every row,
# make `campus` required - matching the final (non-nullable) field
# definition in models.py.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus', '0003_backfill_campus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='campus',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locations', to='campus.campus'),
        ),
        migrations.AlterField(
            model_name='graphnode',
            name='campus',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='graph_nodes', to='campus.campus'),
        ),
        migrations.AlterField(
            model_name='boundarypoint',
            name='campus',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='boundary_points', to='campus.campus'),
        ),
        migrations.AlterModelOptions(
            name='location',
            options={'ordering': ['campus', 'name']},
        ),
        migrations.AlterModelOptions(
            name='graphnode',
            options={'ordering': ['campus', 'name']},
        ),
        migrations.AlterModelOptions(
            name='boundarypoint',
            options={'ordering': ['campus', 'sequence_order']},
        ),
    ]
