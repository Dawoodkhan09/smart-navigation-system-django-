# Campus Navigation System (Django/Python rewrite)

This is a Python/Django port of the original Laravel `Campus-Navigation-System`
(kept as-is in the sibling `../Campus-Navigation-System` folder for reference).
Same real campus map, search, A* walking-route pathfinding, geofencing,
campus-boundary check, and admin panel — rebuilt on Django, with Django's
built-in admin replacing the original's hand-rolled `/admin/*` CRUD.

## Stack

- Django 5.x, SQLite (default, no extra services to run).
- No DRF — the JSON API is 5 small `JsonResponse` views, same as the
  original had no API framework either.
- Frontend is unchanged: vanilla JS + Leaflet 1.9.4 + Bootstrap 5.3.3 via
  CDN, served as static files (`campus/static/campus/js|css`). No
  build step (no Node/Vite needed).

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
campus_navigation/       Django project settings/urls
campus/
  models.py               Location, GraphNode, GraphEdge, BoundaryPoint
  services/                haversine.py, astar.py, navigation.py (pure logic, no framework code)
  api_views.py             /api/... JSON endpoints
  views.py                 home page
  admin.py                 admin customizations (map pickers, suggest-distance, boundary editor)
  management/commands/seed_campus.py
  templates/, static/
```
