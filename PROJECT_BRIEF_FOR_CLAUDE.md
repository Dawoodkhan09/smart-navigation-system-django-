# Campus Navigation System — Project Brief (for Claude)

> Copy-paste this whole file into a new Claude conversation as context, then
> tell Claude exactly what you want built (e.g. "build a mobile user app for
> this backend" or "build a separate user-facing web frontend"). This file
> explains what already exists so Claude doesn't have to guess.

## 1. What this project is

A campus navigation system: students/visitors open a map of a physical
campus, search for a destination (building, department, room), see it on
the map, and get a walking route + estimated time from their live GPS
location to that destination. It also detects whether the user is
currently inside or outside the campus boundary.

It's a Python/Django rewrite of an earlier Laravel app (same features,
same real campus data), and now supports **multiple campuses** in one
install (each campus has its own map center, locations, walkway graph,
and boundary polygon).

Repo: `https://github.com/Dawoodkhan09/smart-navigation-system-django-`

## 2. Tech stack

- **Backend**: Django 5.x, Python. SQLite by default (no extra services).
- **No DRF** — the JSON API is plain `JsonResponse` views (`campus/api_views.py`).
- **Frontend (current)**: server-rendered Django templates + vanilla JS +
  Leaflet 1.9.4 (maps) + Bootstrap 5.3.3, all via CDN. No build step, no
  Node/React/Vite — this is the part a "user app" would likely replace or
  sit alongside.
- **Routing algorithm**: A* pathfinding over a manually-defined graph of
  walkway nodes/edges (not a general road network — just the campus's own
  paths between buildings).
- Deployed on **PythonAnywhere** (currently live).

## 3. Data model (`campus/models.py`)

- **Campus** — one physical campus (tenant root). Fields: `name`, `slug`
  (used in URLs, e.g. `/c/main-campus/`), `center_latitude`,
  `center_longitude`, `default_zoom`, `walking_speed_m_per_min`,
  `default_geofence_radius`. Everything below belongs to exactly one Campus.
- **Location** — a named place shown on the map and searchable (building,
  gate, department, cafeteria, etc.). Fields: `campus` (FK), `name`,
  `description` (free text — for buildings with multiple rooms, the rooms/
  offices/labs are just listed here, e.g. "Ground floor: CS HOD, Faculty
  room 2-5 | 1st floor: IT room, ..."), `latitude`, `longitude`,
  `category`, `geofence_radius`. Search matches `name`, `description`
  *and* `category`, so searching a room name finds its building.
- **GraphNode** — a walkable point (intersection, building entrance).
  Fields: `campus`, `name`, `latitude`, `longitude`.
- **GraphEdge** — an undirected walkway between two `GraphNode`s, with a
  `distance` (meters). Both nodes must belong to the same campus.
- **BoundaryPoint** — one ordered vertex (`sequence_order`) of a campus's
  closed outer-boundary polygon, used for the on-campus/off-campus check.

## 4. URL routes (`campus/urls.py`)

All per-campus routes are scoped under `/c/<campus_slug>/`.

| Path | View | Purpose |
|---|---|---|
| `/` | `campus_picker` | Landing page. Auto-redirects straight into the only campus if there's just one; shows a chooser once there are several. |
| `/c/<slug>/` | `locations_tree` | Category → location tree page (browse without a map first). |
| `/c/<slug>/map/` | `map_view` | The main Leaflet map + search + route panel. |
| `/c/<slug>/api/locations` | `location_list` | GET — all locations in this campus. |
| `/c/<slug>/api/locations/search?q=` | `location_search` | GET — filtered by name/description/category; empty `q` returns everything. |
| `/c/<slug>/api/locations/<id>` | `location_detail` | GET — one location. |
| `/c/<slug>/api/navigation/route` | `navigation_route` | POST — computes the A* walking route. |
| `/c/<slug>/api/campus-boundary` | `campus_boundary` | GET — ordered boundary polygon points. |

## 5. API contracts (what a client app would call)

### `GET /c/<slug>/api/locations` and `.../api/locations/search?q=...`
Response: JSON array of:
```json
{
  "id": 3,
  "name": "Main Library",
  "description": "Ground floor: Circulation desk | 1st floor: Study hall",
  "latitude": 24.8846,
  "longitude": 67.1721,
  "category": "Academic",
  "geofenceRadius": 50
}
```

### `GET /c/<slug>/api/locations/<id>`
Same shape as one item above, or `404 {"message": "Not found."}`.

### `POST /c/<slug>/api/navigation/route`
Request body:
```json
{ "startLatitude": 24.8840, "startLongitude": 67.1715, "destinationLocationId": 3 }
```
Success response (always HTTP 200 — check `success`):
```json
{
  "success": true,
  "message": null,
  "path": [
    { "nodeId": 1, "name": "Gate A", "latitude": 24.884, "longitude": 67.171 },
    { "nodeId": 5, "name": "Library entrance", "latitude": 24.8846, "longitude": 67.1721 }
  ],
  "totalDistanceMeters": 142.3,
  "estimatedWalkingMinutes": 1.8
}
```
Failure response: `{ "success": false, "message": "No walkable path found..." }`.

### `GET /c/<slug>/api/campus-boundary`
Response: `[{ "latitude": 24.88, "longitude": 67.17 }, ...]` (ordered polygon
vertices; a client should point-in-polygon test the user's live GPS
against this to show "on campus" / "off campus").

## 6. Current user-facing flow (what the web UI already does)

1. User lands on `/`, gets sent into their campus (or picks one).
2. **Tree page** (`/c/<slug>/`) — browse locations by category as a
   collapsible tree; clicking a node jumps to the map with that location
   pre-selected as the destination.
3. **Map page** (`/c/<slug>/map/`):
   - Leaflet map centered on the campus, live GPS marker (`geolocation`
     watch), a badge showing "Locating…" / "On campus" / "Off campus".
   - Search box: debounced fetch to `/api/locations/search`, empty query
     shows the full list (browse mode); results show name + category +
     a truncated description preview.
   - Clicking a result (or a map marker) selects it as the destination,
     drops a pin, shows its full description in a side panel.
   - "START NAVIGATION" button POSTs to `/api/navigation/route` with the
     user's current GPS + destination id, draws the returned path as a
     polyline, and shows distance (m) + estimated walking time (min).
   - The real campus boundary polygon is drawn (dashed red) and the app
     toasts a notification on actual "entered campus" / "left campus"
     transitions (not on every GPS tick).
4. **Admin panel** (`/admin/`, Django auth required): manage Campuses,
   Locations, GraphNodes, GraphEdges (with a "suggest distance" helper
   using Haversine straight-line distance), and a dedicated click-to-add
   boundary-point map editor per campus (add/remove/clear/import points).

## 7. Known gaps / things a new client should account for

- Two real buildings ("Building 3", "Building 5") have no seeded GPS
  coordinates yet.
- The walkway graph (GraphNode/GraphEdge) is an educated guess, not a
  measured path network — routes are only as good as the admin-entered
  graph.
- `Campus.walking_speed_m_per_min` and `Campus.default_geofence_radius`
  exist on the model but the route calculation currently still reads the
  **global** Django setting `CAMPUS_WALKING_SPEED_M_PER_MIN`, not the
  per-campus field — worth fixing if per-campus walking speed matters.
- No authentication/accounts for end users at all today — anyone can hit
  the public API. Only `/admin/` requires login.
- CSRF is exempted on the route endpoint (`navigation_route`) since it's
  called from public pages without a session; keep that in mind if a new
  client adds auth.

## 8. What to ask Claude for

Fill this in before sending, e.g.:
- "Build a Flutter/React Native mobile app that consumes these APIs for
  the map/search/navigate flow described above."
- "Build a standalone React web frontend calling this same Django backend,
  replacing the current server-rendered templates."
- Specify: target platform, whether it should reuse the existing backend
  as-is or you're open to backend changes, and any new features you want
  beyond what's listed in section 6 (e.g. saved favorites, turn-by-turn
  voice directions, offline maps, user accounts).
