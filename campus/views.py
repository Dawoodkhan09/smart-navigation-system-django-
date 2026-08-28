from django.conf import settings
from django.shortcuts import render


def home(request):
    return render(request, 'campus/home.html', {
        'map_center_latitude': settings.CAMPUS_MAP_CENTER_LAT,
        'map_center_longitude': settings.CAMPUS_MAP_CENTER_LNG,
        'default_zoom': settings.CAMPUS_DEFAULT_ZOOM,
    })
