from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .api_views import SESSION_LOCKED_CAMPUS_KEY, resolve_default_campus
from .models import Campus, Location, ScanEvent, Tour


@login_required
def campus_picker(request):
    """
    Landing page ('/'): pick which campus to browse. With exactly one
    campus (today's case, and every fresh install after seed_campus) this
    skips straight to it - the chooser only actually shows once a second
    campus exists.

    This whole browser-based web app (this view, locations_tree, map_view
    below) is the admin's own tool now - @login_required, same account as
    /admin/. Visitors never see it; they use /app/... (below), which
    stays public on purpose.
    """
    campuses = list(Campus.objects.all())

    if len(campuses) == 1:
        return redirect('tree', campus_slug=campuses[0].slug)

    return render(request, 'campus/campus_picker.html', {'campuses': campuses})


@login_required
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


@login_required
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
# the /api/v2/... endpoints in api_views.py. Public, no login - this is
# what QR-scanning visitors use.
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


def _lock_session_to_campus(request, campus_slug: str) -> None:
    """
    Once a visitor scans ANY QR (a campus's own, or one of its Locations'),
    their session is locked to that campus: resolve_default_campus() (see
    api_views.py) and the v2 endpoints that use it will only ever serve
    that campus's data from here on, ignoring a ?campus= query param that
    tries to say otherwise. This is what keeps a scanned-in visitor from
    browsing other campuses through the same visitor app.
    """
    request.session[SESSION_LOCKED_CAMPUS_KEY] = campus_slug


def campus_qr_landing(request, campus_slug):
    """
    A CAMPUS's own QR landing (/app/c/<slug>/) - what scanning a campus's
    QR sticker opens. Locks the visitor's session to this campus (see
    _lock_session_to_campus) and sends them straight into its map.
    """
    campus = get_object_or_404(Campus, slug=campus_slug)
    _lock_session_to_campus(request, campus.slug)
    return redirect(reverse('app-shell'))


def location_qr_landing(request, code):
    """
    QR landing (/l/<code>/): what a visitor's phone camera opens when they
    scan a sticker. Records the scan (even for an unrecognised code, so
    admins can see mis-printed/damaged codes in ScanEvent), locks the
    session to this Location's campus (same as campus_qr_landing - any
    valid QR is what grants access), then hands off to the app shell.
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

    _lock_session_to_campus(request, location.campus.slug)
    return redirect(f"{reverse('app-shell')}?at={location.code}")
