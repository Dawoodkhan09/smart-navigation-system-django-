from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .api_views import resolve_default_campus
from .models import Campus, Location, ScanEvent, Tour


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


# =============================================================================
# Visitor app (QR scan -> live map guide). Separate surface from the pages
# above - see PROJECT_BRIEF_FOR_CLAUDE.md / the visitor-app spec. Pages
# render campus/templates/campus/app/*.html (base_app.html, not
# campus/base.html) and do their own data fetching client-side against
# the /api/v2/... endpoints in api_views.py.
# =============================================================================

def app_shell(request):
    """
    The main visitor-app screen: full-bleed map + bottom sheet.

    `?campus=<slug>` (set by campus_qr_landing, location_qr_landing, or
    static/campus/js/app/app.js remembering a previous scan) says which
    campus to load - explicitly, as opposed to resolve_default_campus()
    silently falling back to the first one. `explicit_campus` in the
    template tells app.js whether this page load actually came from a
    scan/link (`?campus=` or `?at=`) or is a bare, unscoped `/app/` visit
    - app.js uses that to decide whether to send a first-time visitor
    straight to the scanner instead of guessing a campus for them (see
    the visitor-app spec: campuses each get their own QR code).

    `?at=<code>` (set by location_qr_landing, or the in-app scanner) tells
    the page which Location to open on, if any. The in-app scanner's own
    redirect only sets `?at=`, not `?campus=` (unlike location_qr_landing)
    - so when `?campus=` is missing but `?at=` isn't, the Location's own
    campus is used instead of silently defaulting to the first one.
    """
    at_code = request.GET.get('at', '')
    campus_slug = request.GET.get('campus', '')

    if not campus_slug and at_code:
        at_location = Location.objects.filter(code=at_code).select_related('campus').first()
        if at_location:
            campus_slug = at_location.campus.slug

    campus = get_object_or_404(Campus, slug=campus_slug) if campus_slug else resolve_default_campus(request)

    return render(request, 'campus/app/shell.html', {
        'campus': campus,
        'at_code': at_code,
        'tour_slug': '',
        'explicit_campus': bool(request.GET.get('campus')) or bool(at_code),
    })


def app_scan(request):
    """Full-screen in-app camera QR scanner (see static/campus/js/app/scanner.js)."""
    campus = resolve_default_campus(request)
    return render(request, 'campus/app/scan.html', {'campus': campus})


def app_tour(request, slug):
    """
    Guided-tour mode. Renders the same app shell as app_shell, just
    bootstrapped straight into tour mode (see static/campus/js/app/tour.js)
    instead of plain browse mode.
    """
    tour = get_object_or_404(Tour, slug=slug, is_published=True)
    campus = resolve_default_campus(request)
    return render(request, 'campus/app/shell.html', {
        'campus': campus,
        'at_code': '',
        'tour_slug': tour.slug,
        'explicit_campus': bool(request.GET.get('campus')),
    })


def campus_qr_landing(request, campus_slug):
    """
    A CAMPUS's own QR landing (/c/<slug>/app/) - what scanning a campus's
    QR sticker opens. This is the code the visitor app's very first
    launch is meant to scan (see app.js): it's what tells a fresh install
    which campus's map/locations/graph to load, before the visitor has
    scanned any individual Location yet.
    """
    campus = get_object_or_404(Campus, slug=campus_slug)
    return redirect(f"{reverse('app-shell')}?campus={campus.slug}")


def location_qr_landing(request, code):
    """
    QR landing (/l/<code>/): what a visitor's phone camera opens when they
    scan a sticker. Records the scan (even for an unrecognised code, so
    admins can see mis-printed/damaged codes in ScanEvent), then hands off
    to the app shell - passing along this location's own campus too, so
    scanning any one Location's QR is *also* enough to establish which
    campus the visitor app should load (not just a dedicated campus QR).
    """
    location = Location.objects.filter(code=code, is_published=True).first()

    ScanEvent.objects.create(
        location=location,
        code_raw=code,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        session_key=request.session.session_key or '',
    )

    if not location:
        return redirect(f"{reverse('app-shell')}?unknown={code}")

    return redirect(f"{reverse('app-shell')}?at={location.code}&campus={location.campus.slug}")
