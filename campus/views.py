from django.shortcuts import get_object_or_404, redirect, render

from .models import Campus


def campus_picker(request):
    """
    Landing page ('/'): pick which campus to browse. With exactly one
    campus (today's case, and every fresh install after seed_campus) this
    skips straight to it - the chooser only actually shows once a second
    campus exists.
    """
    campuses = list(Campus.objects.all())

    if len(campuses) == 1:
        return redirect('tree', campus_slug=campuses[0].slug)

    return render(request, 'campus/campus_picker.html', {'campuses': campuses})


def locations_tree(request, campus_slug):
    """
    Per-campus landing page: a category -> location node tree instead of
    dropping straight onto the map. Locations are fetched client-side
    from this campus's /api/locations (see static/campus/js/location-tree.js);
    clicking a node sends the user to map_view with ?location=<id>, which
    centers the map on that node and selects it as the route destination.
    """
    campus = get_object_or_404(Campus, slug=campus_slug)
    return render(request, 'campus/tree.html', {'campus': campus})


def map_view(request, campus_slug):
    campus = get_object_or_404(Campus, slug=campus_slug)
    return render(request, 'campus/home.html', {
        'campus': campus,
        'map_center_latitude': campus.center_latitude,
        'map_center_longitude': campus.center_longitude,
        'default_zoom': campus.default_zoom,
    })
