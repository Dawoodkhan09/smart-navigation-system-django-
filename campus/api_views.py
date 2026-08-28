"""
Read-only + navigation JSON endpoints consumed by static/campus/js/map.js
and navigation.js to draw markers, power the destination search box, and
run the A* route calculation.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import BoundaryPoint, Location
from .services import navigation


def _location_dto(location: Location) -> dict:
    return {
        'id': location.id,
        'name': location.name,
        'description': location.description,
        'latitude': location.latitude,
        'longitude': location.longitude,
        'category': location.category,
        'geofenceRadius': location.geofence_radius,
    }


@require_GET
def location_list(request):
    locations = Location.objects.order_by('name')
    return JsonResponse([_location_dto(l) for l in locations], safe=False)


@require_GET
def location_search(request):
    q = request.GET.get('q', '').strip()

    queryset = Location.objects.all()
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(category__icontains=q)
        )

    locations = queryset.order_by('name')
    return JsonResponse([_location_dto(l) for l in locations], safe=False)


@require_GET
def location_detail(request, pk: int):
    try:
        location = Location.objects.get(pk=pk)
    except Location.DoesNotExist:
        return JsonResponse({'message': 'Not found.'}, status=404)

    return JsonResponse(_location_dto(location))


@csrf_exempt
@require_POST
def navigation_route(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request body.'})

    try:
        start_lat = float(data['startLatitude'])
        start_lon = float(data['startLongitude'])
        destination_location_id = int(data['destinationLocationId'])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({
            'success': False,
            'message': 'startLatitude, startLongitude and destinationLocationId are required.',
        })

    result = navigation.calculate_route(start_lat, start_lon, destination_location_id)

    # Always 200, even on a "no path found" business-logic failure, so the
    # frontend can just read result.success / result.message.
    return JsonResponse(result)


@require_GET
def campus_boundary(request):
    points = BoundaryPoint.objects.order_by('sequence_order')
    return JsonResponse(
        [{'latitude': p.latitude, 'longitude': p.longitude} for p in points], safe=False
    )
