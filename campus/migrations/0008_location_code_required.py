# Location.code, part 3/3: now that 0007 backfilled every row, make
# `code` required - matching the final (non-nullable) field definition
# in models.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus', '0007_backfill_location_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='code',
            field=models.SlugField(blank=True, db_index=True, max_length=160, unique=True),
        ),
    ]
