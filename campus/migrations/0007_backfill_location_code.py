# Location.code, part 2/3: assign every existing Location a unique slug
# derived from its name (same algorithm as Location._generate_unique_code
# in models.py, duplicated here per Django's migration convention of not
# importing the live model - so this keeps working even if that method
# changes later).

from django.db import migrations
from django.utils.text import slugify


def backfill_codes(apps, schema_editor):
    Location = apps.get_model('campus', 'Location')

    existing_codes = set(
        Location.objects.exclude(code__isnull=True).values_list('code', flat=True)
    )

    for location in Location.objects.filter(code__isnull=True).order_by('id'):
        base = slugify(location.name)[:140] or f'location-{location.pk}'
        candidate = base
        suffix = 2
        while candidate in existing_codes:
            candidate = f'{base}-{suffix}'
            suffix += 1
        location.code = candidate
        location.save(update_fields=['code'])
        existing_codes.add(candidate)


def noop_reverse(apps, schema_editor):
    # Nothing to undo - unmigrating 0008 will make the field nullable
    # again, at which point leaving rows with a code is harmless.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('campus', '0006_location_code'),
    ]

    operations = [
        migrations.RunPython(backfill_codes, noop_reverse),
    ]
