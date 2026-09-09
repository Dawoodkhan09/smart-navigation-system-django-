"""
Read-only + navigation JSON endpoints consumed by static/campus/js/map.js
and navigation.js to draw markers, power the destination search box, and
run the A* route calculation. Every endpoint is scoped to one campus (the
<campus_slug> in the URL - see campus/urls.py) so browsing/searching/
routing never crosses into another campus's data.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import BoundaryPoint, Campus, Location, ScanEvent, Tour
from .services import directions, geometry, navigation

# Session key set once a visitor scans any QR (a campus's own, or one of
# its Locations') - see campus.views._lock_session_to_campus. Shared here
# (not duplicated in views.py) since resolve_default_campus below is what
# actually enforces it.
SESSION_LOCKED_CAMPUS_KEY = 'locked_campus_slug'


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


@login_required
@require_GET
def location_list(request, campus_slug):
    campus = get_object_or_404(Campus, slug=campus_slug)
    locations = Location.objects.filter(campus=campus).order_by('name')
    return JsonResponse([_location_dto(l) for l in locations], safe=False)


@login_required
@require_GET
def location_search(request, campus_slug):
    campus = get_object_or_404(Campus, slug=campus_slug)
    q = request.GET.get('q', '').strip()

    queryset = Location.objects.filter(campus=campus)
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(category__icontains=q)
        )

    locations = queryset.order_by('name')
    return JsonResponse([_location_dto(l) for l in locations], safe=False)


@login_required
@require_GET
def location_detail(request, campus_slug, pk: int):
    campus = get_object_or_404(Campus, slug=campus_slug)
    try:
        location = Location.objects.get(campus=campus, pk=pk)
    except Location.DoesNotExist:
        return JsonResponse({'message': 'Not found.'}, status=404)

    return JsonResponse(_location_dto(location))


@login_required
@csrf_exempt
@require_POST
def navigation_route(request, campus_slug):
    campus = get_object_or_404(Campus, slug=campus_slug)

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

    result = navigation.calculate_route(campus, start_lat, start_lon, destination_location_id)

    # Always 200, even on a "no path found" business-logic failure, so the
    # frontend can just read result.success / result.message.
    return JsonResponse(result)


@login_required
@require_GET
def campus_boundary(request, campus_slug):
    campus = get_object_or_404(Campus, slug=campus_slug)
    points = BoundaryPoint.objects.filter(campus=campus).order_by('sequence_order')
    return JsonResponse(
        [{'latitude': p.latitude, 'longitude': p.longitude} for p in points], safe=False
    )


# =============================================================================
# API v2 - the visitor app (QR scan -> live map guide).
#
# Unlike the v1 endpoints above, none of these take a <campus_slug> in the
# URL: `code` is globally unique across every campus (see Location.code in
# models.py), so a single /l/<code>/ or /api/v2/locations/<code>/ can
# resolve a place without knowing which campus it's on first. Endpoints
# that aren't about one specific Location (locations list, nearby, tours,
# boundary) instead take an optional ?campus=<slug> query param, falling
# back to the first Campus - today's de facto "the campus" until the
# visitor app grows its own campus picker.
# =============================================================================


def resolve_default_campus(request):
    """
    Which campus a request without an explicit <campus_slug> in the URL
    (every /app/... page and every /api/v2/... endpoint below) is for.

    Priority: 1) a campus the visitor is locked to, from having scanned a
    QR (see campus.views._lock_session_to_campus) - this always wins, so
    a ?campus=<slug> query param can't be used to hop to another campus
    once a visitor has scanned their way into one; 2) an explicit
    ?campus=<slug> (only reachable before any QR has been scanned yet -
    useful for local testing); 3) the first Campus, as a last resort.
    """
    locked_slug = request.session.get(SESSION_LOCKED_CAMPUS_KEY)
    if locked_slug:
        return get_object_or_404(Campus, slug=locked_slug)

    slug = request.GET.get('campus')
    if slug:
        return get_object_or_404(Campus, slug=slug)

    campus = Campus.objects.first()
    if campus is None:
        raise Http404('No campus has been configured yet.')
    return campus


def _get_locked_campus(request):
    """The Campus a visitor's session is locked to, or None if they
    haven't scanned anything (yet)."""
    slug = request.session.get(SESSION_LOCKED_CAMPUS_KEY)
    return Campus.objects.filter(slug=slug).first() if slug else None


def _v2_location_dto(location: Location, request) -> dict:
    return {
        'id': location.id,
        'code': location.code,
        'name': location.name,
        'category': location.category,
        'lat': location.latitude,
        'lng': location.longitude,
        'shortDescription': location.short_description,
        'photoUrl': request.build_absolute_uri(location.photo.url) if location.photo else None,
        'isOpenNow': location.is_open_now,
        'floorCount': location.floor_count,
    }


def _v2_location_detail_dto(location: Location, request) -> dict:
    dto = _v2_location_dto(location, request)
    dto.update({
        'description': location.description,
        'geofenceRadius': location.geofence_radius,
        'isScannable': location.is_scannable,
        'campus': location.campus.slug,
        'nearby': _nearby_dtos(location.campus, request, exclude_id=location.id, lat=location.latitude, lng=location.longitude, limit=4),
    })
    return dto


def _nearby_dtos(campus, request, *, lat: float, lng: float, limit: int, exclude_id=None) -> list:
    from .services import haversine

    queryset = Location.objects.filter(campus=campus, is_published=True)
    if exclude_id is not None:
        queryset = queryset.exclude(pk=exclude_id)

    with_distance = sorted(
        (
            (haversine.distance_meters(lat, lng, loc.latitude, loc.longitude), loc)
            for loc in queryset
        ),
        key=lambda pair: pair[0],
    )[:limit]

    results = []
    for distance_m, loc in with_distance:
        dto = _v2_location_dto(loc, request)
        dto['distanceM'] = round(distance_m, 1)
        results.append(dto)
    return results


@require_GET
def v2_location_list(request):
    campus = resolve_default_campus(request)
    category = request.GET.get('category', '').strip()
    q = request.GET.get('q', '').strip()

    queryset = Location.objects.filter(campus=campus, is_published=True)
    if category:
        queryset = queryset.filter(category__iexact=category)
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(short_description__icontains=q) | Q(description__icontains=q) | Q(category__icontains=q)
        )

    locations = queryset.order_by('name')
    return JsonResponse([_v2_location_dto(loc, request) for loc in locations], safe=False)


@require_GET
def v2_location_detail(request, code):
    location = get_object_or_404(Location, code=code, is_published=True)

    # Locked-in visitors can't look up a Location outside their own
    # campus this way either, not just via ?campus= on the list endpoint -
    # treated as 404 (not "found but forbidden") so it doesn't even
    # confirm the code exists on another campus.
    locked = _get_locked_campus(request)
    if locked and location.campus_id != locked.id:
        raise Http404

    return JsonResponse(_v2_location_detail_dto(location, request))


@require_GET
def v2_route(request):
    """
    GET /api/v2/route/?from=<code>&to=<code>  - origin is a known Location
        (e.g. wherever the visitor scanned in from).
    GET /api/v2/route/?from_lat=&from_lng=&to=<code>  - origin is a raw
        GPS fix instead, which won't line up with any Location's own
        coordinates. This extends the spec's from/to-code-only contract
        (see PROJECT_BRIEF_FOR_CLAUDE.md discussion) because "Directions"
        can also start from the visitor's live position, not just a
        scanned place - reuses navigation.calculate_route exactly as the
        v1 map already does for a GPS start, no new pathfinding code.
    """
    to_code = request.GET.get('to', '').strip()
    from_code = request.GET.get('from', '').strip()
    from_lat = request.GET.get('from_lat')
    from_lng = request.GET.get('from_lng')

    if not to_code:
        return JsonResponse({'error': 'missing_params', 'message': '"to" query param is required.'}, status=400)

    locked = _get_locked_campus(request)

    try:
        destination = Location.objects.get(code=to_code)
    except Location.DoesNotExist:
        return JsonResponse({'error': 'unknown_code'}, status=404)
    if locked and destination.campus_id != locked.id:
        return JsonResponse({'error': 'unknown_code'}, status=404)

    if from_code:
        try:
            origin = Location.objects.get(code=from_code)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'unknown_code'}, status=404)
        if locked and origin.campus_id != locked.id:
            return JsonResponse({'error': 'unknown_code'}, status=404)
        result = navigation.calculate_route_between_locations(origin, destination)
        origin_name = origin.name
    elif from_lat is not None and from_lng is not None:
        try:
            lat, lng = float(from_lat), float(from_lng)
        except ValueError:
            return JsonResponse({'error': 'invalid_params', 'message': '"from_lat"/"from_lng" must be numbers.'}, status=400)
        result = navigation.calculate_route(destination.campus, lat, lng, destination.id)
        origin_name = 'Your location'
    else:
        return JsonResponse({'error': 'missing_params', 'message': 'Provide "from" (a location code) or "from_lat"/"from_lng".'}, status=400)

    if not result['success']:
        return JsonResponse({'error': 'no_route', 'message': result['message']}, status=404)

    path = result['path']
    return JsonResponse({
        'origin_name': origin_name,
        'distance_m': result['totalDistanceMeters'],
        'duration_min': result['estimatedWalkingMinutes'],
        # `code` is null for every node here: these are graph walkway
        # nodes (GraphNode), not Locations, so they don't have a public
        # QR code of their own - only the origin/destination do, and the
        # caller already has those (the from/to query params).
        'path': [{'lat': n['latitude'], 'lng': n['longitude'], 'name': n['name'], 'code': None} for n in path],
        'steps': directions.steps_from_path(path),
    })


@require_GET
def v2_nearby(request):
    campus = resolve_default_campus(request)

    try:
        lat = float(request.GET['lat'])
        lng = float(request.GET['lng'])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({'error': 'invalid_params', 'message': '"lat" and "lng" query params are required.'}, status=400)

    try:
        limit = int(request.GET.get('limit', 5))
    except ValueError:
        limit = 5
    limit = max(1, min(limit, 50))

    return JsonResponse(_nearby_dtos(campus, request, lat=lat, lng=lng, limit=limit), safe=False)


@require_POST
def v2_scan(request):
    """
    POST {"code": "main-gate"} (or a full /l/<code>/ URL - the last path
    segment is used). CSRF-protected: the visitor-app page sends the
    standard X-CSRFToken header (see static/campus/js/api.js), unlike the
    v1 navigation_route endpoint which predates that being wired up.
    """
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid_body'}, status=400)

    raw_code = str(data.get('code', '')).strip()
    code = raw_code.rstrip('/').rsplit('/', 1)[-1] if raw_code else ''

    location = Location.objects.filter(code=code, is_published=True).first() if code else None

    ScanEvent.objects.create(
        location=location,
        code_raw=raw_code,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        session_key=request.session.session_key or '',
    )

    if not location:
        return JsonResponse({'error': 'unknown_code'}, status=404)

    # Scanning any valid QR is what grants access to a campus (see
    # campus.views._lock_session_to_campus for the /l/<code>/ and
    # /app/c/<slug>/ landing equivalents) - the in-app scanner goes
    # through this endpoint instead, so it re-locks here too, even
    # switching a previously-locked session to a different campus if
    # that's genuinely what was just scanned.
    request.session[SESSION_LOCKED_CAMPUS_KEY] = location.campus.slug

    return JsonResponse(_v2_location_detail_dto(location, request))


@require_GET
def v2_boundary(request):
    campus = resolve_default_campus(request)
    points = list(BoundaryPoint.objects.filter(campus=campus).order_by('sequence_order'))
    point_dicts = [{'latitude': p.latitude, 'longitude': p.longitude} for p in points]

    inside = None
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat is not None and lng is not None:
        try:
            inside = geometry.point_in_polygon(float(lat), float(lng), point_dicts)
        except ValueError:
            inside = None

    return JsonResponse({
        'points': [{'lat': p['latitude'], 'lng': p['longitude']} for p in point_dicts],
        'inside': inside,
    })


def _v2_tour_summary_dto(tour: Tour, request) -> dict:
    return {
        'slug': tour.slug,
        'title': tour.title,
        'summary': tour.summary,
        'durationMinutes': tour.duration_minutes,
        'stopCount': tour.stops.count(),
        'coverImageUrl': request.build_absolute_uri(tour.cover_image.url) if tour.cover_image else None,
    }


@require_GET
def v2_tour_list(request):
    tours = Tour.objects.filter(is_published=True)
    return JsonResponse([_v2_tour_summary_dto(t, request) for t in tours], safe=False)


@require_GET
def v2_tour_detail(request, slug):
    tour = get_object_or_404(Tour, slug=slug, is_published=True)
    stops = tour.stops.select_related('location').order_by('order')

    dto = _v2_tour_summary_dto(tour, request)
    dto['stops'] = [
        {
            'order': stop.order,
            'note': stop.note,
            'location': _v2_location_dto(stop.location, request),
        }
        for stop in stops
    ]
    return JsonResponse(dto)
