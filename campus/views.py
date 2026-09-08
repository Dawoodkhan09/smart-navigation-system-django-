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
    The main visitor-app screen: full-bleed map + bottom sheet. `?at=<code>`
    (set by location_qr_landing below, or by the in-app scanner) tells the
    page which Location to open on, if any.
    """
    campus = resolve_default_campus(request)
    return render(request, 'campus/app/shell.html', {
        'campus': campus,
        'at_code': request.GET.get('at', ''),
        'tour_slug': '',
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
    })


def location_qr_landing(request, code):
    """
    QR landing (/l/<code>/): what a visitor's phone camera opens when they
    scan a sticker. Records the scan (even for an unrecognised code, so
    admins can see mis-printed/damaged codes in ScanEvent), then hands off
    to the app shell.
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

    return redirect(f"{reverse('app-shell')}?at={location.code}")
