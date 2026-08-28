// admin-boundary-editor.js - click-to-add-polygon-point editor used on
// Admin/CampusBoundary/Index.blade.php. Each click on the map is saved
// immediately (AJAX) as the next vertex of the campus boundary polygon.
// Also supports importing a whole boundary at once from pasted GeoJSON.

(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const mapDiv = document.getElementById('boundaryMap');
        if (!mapDiv) return;

        const config = window.CAMPUS_CONFIG || { centerLat: 24.8844, centerLng: 67.1720, defaultZoom: 16 };
        let points = (window.INITIAL_BOUNDARY_POINTS || []).slice(); // [{lat, lng}, ...] in order
        const routes = window.BOUNDARY_ROUTES;

        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.content : '';

        const map = L.map('boundaryMap').setView([config.centerLat, config.centerLng], config.defaultZoom);
        // Satellite is usually the better choice here - it's much easier to
        // trace your real campus edge (walls, roads, roofs) than on a plain
        // street map, so default to it on this page.
        addBaseLayerSwitcher(map, { defaultSatellite: true });

        let polygon = null;
        let markers = [];

        function redraw() {
            if (polygon) map.removeLayer(polygon);
            markers.forEach((m) => map.removeLayer(m));
            markers = [];

            const latLngs = points.map((p) => [p.lat, p.lng]);

            points.forEach((p, i) => {
                const marker = L.circleMarker([p.lat, p.lng], { radius: 5, color: '#dc3545' })
                    .addTo(map)
                    .bindTooltip(String(i + 1));
                markers.push(marker);
            });

            if (latLngs.length >= 2) {
                polygon = L.polygon(latLngs, { color: '#0d6efd', weight: 2, fillOpacity: 0.1 }).addTo(map);
            }

            document.getElementById('pointCount').textContent = points.length;
            const list = document.getElementById('pointList');
            list.innerHTML = '';
            points.forEach((p) => {
                const li = document.createElement('li');
                li.textContent = `${p.lat.toFixed(6)}, ${p.lng.toFixed(6)}`;
                list.appendChild(li);
            });
        }

        async function postJson(url, body) {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'Accept': 'application/json'
                },
                body: body ? JSON.stringify(body) : null
            });
            return res;
        }

        map.on('click', async function (e) {
            const { lat, lng } = e.latlng;
            const res = await postJson(routes.addPoint, { latitude: lat, longitude: lng });
            if (res.ok) {
                points.push({ lat, lng });
                redraw();
            } else {
                alert('Could not save that point - please try again.');
            }
        });

        document.getElementById('undoBtn').addEventListener('click', async function () {
            if (points.length === 0) return;
            const res = await postJson(routes.removeLastPoint);
            if (res.ok) {
                points.pop();
                redraw();
            }
        });

        document.getElementById('clearBtn').addEventListener('click', async function () {
            if (points.length === 0) return;
            if (!confirm('Remove all boundary points?')) return;
            const res = await postJson(routes.clearAll);
            if (res.ok) {
                points = [];
                redraw();
            }
        });

        // ----- Import from pasted GeoJSON (e.g. drawn on geojson.io) -----
        // Accepts a bare Polygon/LineString geometry, a single Feature, or a
        // FeatureCollection containing one. GeoJSON coordinates are always
        // [longitude, latitude] - the opposite order from this app's
        // {lat, lng} - so that swap happens here.
        function extractRingFromGeoJson(text) {
            const data = JSON.parse(text);

            let geometry = data;
            if (data.type === 'FeatureCollection') {
                const feature = (data.features || []).find(
                    (f) => f.geometry && (f.geometry.type === 'Polygon' || f.geometry.type === 'LineString')
                );
                if (!feature) throw new Error('No Polygon or LineString found in that GeoJSON.');
                geometry = feature.geometry;
            } else if (data.type === 'Feature') {
                geometry = data.geometry;
            }

            let coords;
            if (geometry.type === 'Polygon') {
                coords = geometry.coordinates[0]; // outer ring
            } else if (geometry.type === 'LineString') {
                coords = geometry.coordinates;
            } else {
                throw new Error('Expected a Polygon or LineString geometry.');
            }

            let ring = coords.map((c) => ({ lat: c[1], lng: c[0] }));

            // Drop a duplicate closing point (first === last), since this
            // app already closes the polygon automatically.
            if (ring.length > 1) {
                const first = ring[0], last = ring[ring.length - 1];
                const same = Math.abs(first.lat - last.lat) < 1e-7 && Math.abs(first.lng - last.lng) < 1e-7;
                if (same) ring = ring.slice(0, -1);
            }

            return ring;
        }

        document.getElementById('importBtn').addEventListener('click', async function () {
            const messageEl = document.getElementById('importMessage');
            messageEl.className = 'small mt-1';
            messageEl.textContent = '';

            const text = document.getElementById('geoJsonInput').value.trim();
            if (!text) {
                messageEl.className = 'small mt-1 text-danger';
                messageEl.textContent = 'Paste some GeoJSON first.';
                return;
            }

            let ring;
            try {
                ring = extractRingFromGeoJson(text);
            } catch (err) {
                messageEl.className = 'small mt-1 text-danger';
                messageEl.textContent = 'Could not read that GeoJSON: ' + err.message;
                return;
            }

            if (ring.length < 3) {
                messageEl.className = 'small mt-1 text-danger';
                messageEl.textContent = `Only found ${ring.length} point(s) - need at least 3.`;
                return;
            }

            const body = { points: ring.map((p) => ({ latitude: p.lat, longitude: p.lng })) };
            const res = await postJson(routes.importPoints, body);

            if (res.ok) {
                points = ring;
                redraw();
                map.fitBounds(points.map((p) => [p.lat, p.lng]), { padding: [30, 30] });
                messageEl.className = 'small mt-1 text-success';
                messageEl.textContent = `Imported ${ring.length} points - this replaced your previous boundary.`;
            } else {
                const data = await res.json().catch(() => ({}));
                messageEl.className = 'small mt-1 text-danger';
                messageEl.textContent = data.message || 'Import failed - please try again.';
            }
        });

        redraw();
    });
})();
