# Campus Navigation System (Django/Python rewrite)

This is a Python/Django port of the original Laravel `Campus-Navigation-System`
(kept as-is in the sibling `../Campus-Navigation-System` folder for reference).
Same real campus map, search, A* walking-route pathfinding, geofencing,
campus-boundary check, and admin panel — rebuilt on Django, with Django's
built-in admin replacing the original's hand-rolled `/admin/*` CRUD.

## Two audiences, two surfaces

- **`/`, `/c/<slug>/...`, `/admin/`** — the browser-based web app. This is
  the **admin's** tool (manage locations/graph/boundary, browse the map
  while doing so) and now requires **logging in** (see "Web app login"
  below) - the same account either way.
- **`/app/...`** — the mobile-first visitor app. This is what **regular
  users** (students/visitors) use on their own phones, reached by
  scanning a QR code. No login, no account - a QR code is what grants
  access (see "Visitor app" below).

## Stack

- Django 5.x, SQLite (default, no extra services to run).
- No DRF — the JSON API is small `JsonResponse` views, same as the
  original had no API framework either.
- Frontend is vanilla JS + Leaflet 1.9.4 + Bootstrap 5.3.3 via CDN,
  served as static files (`campus/static/campus/js|css`). No build step
  (no Node/Vite needed) anywhere in the project, including the visitor
  app below.
- `qrcode[pil]` + `Pillow` for QR-code generation and Location/Tour
  photo uploads (see Config below for `MEDIA_URL`/`MEDIA_ROOT`).

## Web app login

`/`, `/c/<slug>/...` (both the pages and their `/api/...` endpoints) now
require being logged in - `@login_required` in `views.py`/`api_views.py`,
`LOGIN_URL` pointing at a dedicated `campus/login.html` page (not the
Django-admin-styled `/admin/login/`, though it's the same underlying
account either way). Sign in at `/login/`; an unauthenticated visit to
any protected page redirects there with `?next=` and returns you to
where you were headed once you're signed in. `/admin/` keeps its own
separate login screen as before - both use the same `auth.User` table.

## Visitor app (QR scan → live map guide)

A second, mobile-first surface at **`/app/`**, separate from the
Bootstrap map/admin above (own base template, own `app.css`, no
Bootstrap, no login). A visitor scans a QR sticker with their phone's
stock camera → lands in a polished map experience already centered on
the right place, with a bottom sheet for browsing, directions, and a
guided tour mode.

**Two kinds of QR code - scanning either one is what grants access:**

- **Campus QR** (Admin → Campuses → open one → QR preview) - encodes
  `/app/c/<slug>/`. Scanning it locks the visitor's session to that
  campus and sends them straight into its map.
- **Location QR** (Admin → Locations → open one → QR preview) - encodes
  `/l/<code>/`; scanning it locks the session to *that Location's*
  campus the same way, in addition to opening straight on that place.

Once a session is locked to a campus, it stays locked: `resolve_default_campus()`
in `api_views.py` ignores a `?campus=<slug>` query param from then on, and
`/api/v2/locations/<code>/` + `/api/v2/route/` 404 for anything outside
the locked campus even if the code/slug is otherwise valid - a scanned-in
visitor can't browse or route to another campus's data through the same
session. Scanning a *different* campus's QR (or one of its Locations')
re-locks to that one instead - any valid QR is itself the "permission" to
switch. A session that hasn't scanned anything yet falls back to the
first Campus, same as before.

- **Pages**: `/app/` (map + sheet), `/app/scan/` (in-app camera
  scanner), `/app/tour/<slug>/` (guided tour), `/l/<code>/` and
  `/app/c/<slug>/` (QR landings - the Location one records a
  `ScanEvent` too, both lock the session and redirect into `/app/`).
- **API**: `campus/api_views.py`'s `/api/v2/...` endpoints (locations,
  location detail + nearby, route + turn-by-turn steps, nearby, scan,
  boundary + inside/outside, tours) — all plain `JsonResponse`, no DRF,
  reusing the existing `services/astar.py`/`haversine.py` for routing.
  `code` (`Location.code`, e.g. `main-gate`) is globally unique across
  every campus, so most v2 endpoints don't need a campus slug in the URL
  the way the v1 ones under `/c/<slug>/...` do - the session lock above
  is what scopes them instead.
- **QR codes**: generated on demand from `campus/services/qr.py` (error
  correction level H, so a weathered/scuffed outdoor sticker still
  scans). Admin → Campuses or Locations → open one to see/download its
  QR PNG; Locations additionally support selecting several and using
  the "Print QR sheet for selected locations" action for a print-ready
  A4 sheet (3×4 grid).
- **PWA**: `/manifest.webmanifest` and `/sw.js` are served from the root
  urlconf (not `static/`) so the service worker's scope covers the whole
  site, not just `/static/campus/js/`. Installable to a phone's home
  screen; caches map tiles/static assets and the last locations response
  for offline browsing.
- Frontend modules live under `campus/static/campus/js/app/` (`app.js`,
  `map.js`, `sheet.js`, `route.js`, `tour.js`, `scanner.js`, `geo.js`,
  `ui.js`, `api.js`, `store.js`, `icons.js`) — kept separate from the
  existing top-level `campus/static/campus/js/*.js` so the original `/`
  map page's scripts are untouched.

### Testing the visitor app on a real phone

The in-app scanner (`getUserMedia`) and live GPS (`watchPosition`) only
work in a **secure context** — HTTPS, or `localhost` on the same
machine. Running `manage.py runserver 0.0.0.0:8000` and opening
`http://192.168.x.x:8000` from your phone will make both silently fail
(the camera/location prompts just never appear). To test on a real
device during development:

1. **Quick tunnel (easiest)** — get a real HTTPS URL pointed at your
   local server:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   (or `ngrok http 8000` if you have an ngrok account). Either prints a
   `https://*.trycloudflare.com` / `https://*.ngrok-free.app` URL.
2. Add that host to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (both env
   vars already support a comma-separated list - see Config below), e.g.:
   ```bash
   set DJANGO_CSRF_TRUSTED_ORIGINS=https://your-tunnel-host.trycloudflare.com
   ```
3. Open that HTTPS URL on your phone → `/app/` works fully (camera
   scanner, GPS, install-to-home-screen).
4. Alternatively, `django-extensions` + `runserver_plus --cert-file
   cert.pem --key-file key.pem` gives you a locally-trusted HTTPS dev
   server without a tunnel, if your phone and laptop are on the same
   network and you don't mind installing a dev cert.

**QR codes are host-specific**: a code's PNG encodes a full URL
(`https://<host>/l/<code>/`), baked in at generation time (see
`qr.build_location_url`). If your tunnel URL changes (a new
`cloudflared`/`ngrok` run gets a new hostname) or you move from a tunnel
to the real production domain, **regenerate and reprint every QR code**
— Admin → Locations → the QR preview always reflects the *current*
request's host, so open/download it again from wherever you're serving
the site from.

## Native app (Android / iOS)

The visitor app is a full PWA already (`/manifest.webmanifest`, `/sw.js`,
installable, works offline) - the fastest path to a real app-store-style
app is **[PWABuilder](https://www.pwabuilder.com/)**, which packages an
existing PWA into an Android APK/AAB (and an iOS Xcode project) with no
local Android/iOS tooling at all.

### Android (APK/AAB)

1. Deploy the site somewhere with a **stable** HTTPS URL first (a
   `cloudflared`/`ngrok` tunnel's URL changes every run, which breaks a
   packaged app pointed at the old one) - e.g. `https://<you>.pythonanywhere.com`.
2. Go to pwabuilder.com → enter that URL → **Package for Store** → **Android**.
3. Either let it generate a new signing key, or upload your own. Either
   way it gives you a **package name** and a **SHA256 signing
   fingerprint**.
4. Set those as env vars on the server so `/.well-known/assetlinks.json`
   serves the right verification (see `campus_navigation/urls.py` /
   `settings.py`):
   ```bash
   ANDROID_PACKAGE_NAME=com.example.campusguide
   ANDROID_SHA256_FINGERPRINT=14:6D:E9:83:...
   ```
   Without this step the APK still works, it just shows a Chrome address
   bar (a plain Trusted Web Activity isn't "verified" yet) instead of
   looking fully native.
5. Download the `.apk`/`.aab` PWABuilder built and install/upload it.

### iOS

Apple only allows building/signing an iOS app on **macOS with Xcode** -
there's no way around this from Windows, whichever tool is used
(PWABuilder, Capacitor, or plain Swift). PWABuilder can still generate
the Xcode project for you (same "Package for Store" flow → **iOS**), but
turning that into an installable `.ipa` needs access to a Mac (or a
cloud Mac CI service like Codemagic/GitHub Actions macOS runners) plus
an Apple Developer account to sign it. Until then, Safari's own
"Add to Home Screen" on `/app/` already gives iOS visitors an installable,
full-screen, offline-capable app icon - see the `apple-mobile-web-app-*`
meta tags in `base_app.html`.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # (Windows) or: source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_campus   # loads the real 15 locations, 17 edges, 16-point boundary
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for the map, `http://127.0.0.1:8000/admin/`
for the admin panel (log in with the superuser you just created).

## Config

Same env vars as the original's `config/campus.php`, read in
`campus_navigation/settings.py`:

- `CAMPUS_MAP_CENTER_LAT` (default `24.8844`)
- `CAMPUS_MAP_CENTER_LNG` (default `67.1720`)
- `CAMPUS_DEFAULT_ZOOM` (default `17`)
- `CAMPUS_WALKING_SPEED_M_PER_MIN` (default `80`)
- `CAMPUS_DEFAULT_GEOFENCE_RADIUS` (default `50`)
- `DJANGO_CSRF_TRUSTED_ORIGINS` — comma-separated list, needed for any
  HTTPS host (PythonAnywhere, a tunnel while testing on a phone, ...).
- `DJANGO_ALLOWED_HOSTS` — comma-separated list, appended to the
  hardcoded defaults in `settings.py` (same idea, for `ALLOWED_HOSTS`).
- `ANDROID_PACKAGE_NAME` / `ANDROID_SHA256_FINGERPRINT` — only needed
  after packaging the Android app (see "Native app" above); power
  `/.well-known/assetlinks.json`.

Uploaded media (Location photos, Tour cover images) is written to
`MEDIA_ROOT` (`media/` at the project root, gitignored) and served at
`MEDIA_URL` (`/media/`) — Django serves it itself only when `DEBUG=True`;
a real deployment needs a `/media/` static mapping the same way
`/static/` already has one (see DEPLOY.md).

## Known gaps (carried over from the original)

- "Building 3" and "Building 5" have no seeded coordinates — add them via
  the admin panel once their real GPS coordinates are known.
- The walkway graph edges are an educated guess based on building
  positions, not a measured path network — correct/add edges via
  Admin → Graph Edges as you walk the real campus; that's what actually
  determines the routes A* will suggest.

## Difference from the original

The Laravel app's `/admin/*` had **no authentication at all** (a gap its
own README called out). Django's admin always requires a logged-in staff
user, so this rewrite closes that gap by default — you need the
`createsuperuser` account above to reach any `/admin/...` page.

## Project layout

```
campus_navigation/       Django project settings/urls (+ /manifest.webmanifest, /sw.js)
campus/
  models.py               Campus, Location, GraphNode, GraphEdge, BoundaryPoint,
                           ScanEvent, Tour, TourStop
  services/                haversine.py, astar.py, navigation.py, directions.py,
                           geometry.py, qr.py - pure logic, no framework code
  api_views.py             /api/... (v1) and /api/v2/... (visitor app) JSON endpoints
  views.py                 map/tree pages + visitor-app pages (app_shell, app_scan, ...)
  admin.py                 admin customizations (map pickers, suggest-distance,
                           boundary editor, QR preview/print sheet)
  management/commands/seed_campus.py
  tests/test_directions.py
  templates/
    campus/                original map/tree/admin templates
    campus/app/            visitor-app templates (base_app.html, shell.html, scan.html, ...)
  static/campus/
    js/                    original map/tree/admin scripts
    js/app/                visitor-app ES modules (app.js, map.js, sheet.js, ...)
    css/site.css           original styles
    css/app.css            visitor-app design system (no Bootstrap)
```
