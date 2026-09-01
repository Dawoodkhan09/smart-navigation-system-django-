from django.conf import settings
from django.shortcuts import render


def locations_tree(request):
    """
    Landing page ('/'): a category -> location node tree instead of
    dropping straight onto the map. Locations are fetched client-side
    from /api/locations (see static/campus/js/location-tree.js); clicking
    a node sends the user to map_view with ?location=<id>, which centers
    the map on that node and selects it as the route destination.
    """
    return render(request, 'campus/tree.html')


def map_view(request):
    return render(request, 'campus/home.html', {
        'map_center_latitude': settings.CAMPUS_MAP_CENTER_LAT,
        'map_center_longitude': settings.CAMPUS_MAP_CENTER_LNG,
        'default_zoom': settings.CAMPUS_DEFAULT_ZOOM,
    })
