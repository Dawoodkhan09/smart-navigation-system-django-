# Location.code, part 1/3: add it nullable (and NOT yet unique-enforced
# against existing rows in a way that would fail) so this is safe to run
# against a database that already has Location rows (existing
# PythonAnywhere data) - 0007 backfills a slug for every row, then 0008
# drops null=True to match the final model definition. Same 3-step
# pattern as 0002/0003/0004 used for the Campus FK.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus', '0005_location_visitor_fields_and_new_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='code',
            field=models.SlugField(db_index=True, max_length=160, null=True, unique=True),
        ),
    ]
