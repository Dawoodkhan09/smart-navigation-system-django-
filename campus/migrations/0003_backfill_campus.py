# Multi-campus support, part 2/3: create one Campus row matching this
# app's existing CAMPUS_* settings defaults (so behaviour for the current
# single campus is unchanged), then point every existing Location/
# GraphNode/BoundaryPoint row at it. Safe to run on a fresh (empty)
# database too - the loops just do nothing.

from django.db import migrations


DEFAULT_CAMPUS = {
    'name': 'Main Campus',
    'slug': 'main-campus',
    'center_latitude': 24.8844,
    'center_longitude': 67.1720,
    'default_zoom': 17,
    'walking_speed_m_per_min': 80,
    'default_geofence_radius': 50,
}


def backfill_campus(apps, schema_editor):
    Campus = apps.get_model('campus', 'Campus')
    Location = apps.get_model('campus', 'Location')
    GraphNode = apps.get_model('campus', 'GraphNode')
    BoundaryPoint = apps.get_model('campus', 'BoundaryPoint')

    needs_backfill = (
        Location.objects.filter(campus__isnull=True).exists()
        or GraphNode.objects.filter(campus__isnull=True).exists()
        or BoundaryPoint.objects.filter(campus__isnull=True).exists()
    )
    if not needs_backfill:
        return

    campus, _ = Campus.objects.get_or_create(slug=DEFAULT_CAMPUS['slug'], defaults=DEFAULT_CAMPUS)

    Location.objects.filter(campus__isnull=True).update(campus=campus)
    GraphNode.objects.filter(campus__isnull=True).update(campus=campus)
    BoundaryPoint.objects.filter(campus__isnull=True).update(campus=campus)


def noop_reverse(apps, schema_editor):
    # Nothing to undo - unmigrating 0004 will make the FK nullable again,
    # at which point leaving rows pointed at "Main Campus" is harmless.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('campus', '0002_campus'),
    ]

    operations = [
        migrations.RunPython(backfill_campus, noop_reverse),
    ]
