// boundary.js - draws the real campus boundary polygon on the map and
// continuously checks (via point-in-polygon.js) whether the user's live
// GPS position is inside it. Fires a notification only on actual state
// change (outside -> inside / inside -> outside), same pattern as the
// per-location geofence.js.

(function () {
    let boundaryPoints = []; // [{lat, lng}, ...]
    let isInsideCampus = null; // null = unknown yet, true/false once we have a GPS fix

    async function loadBoundary() {
        const res = await fetch('/api/campus-boundary');
        if (!res.ok) return;

        const points = await res.json();
        boundaryPoints = points.map((p) => ({ lat: p.latitude, lng: p.longitude }));

        if (boundaryPoints.length >= 3 && window.campusMap) {
            L.polygon(boundaryPoints.map((p) => [p.lat, p.lng]), {
                color: '#dc3545',
                weight: 2,
                dashArray: '6 4',
                fillOpacity: 0.03
            }).addTo(window.campusMap).bindTooltip('Campus boundary');
        }
    }

    function updateStatusBadge(inside) {
        const badge = document.getElementById('campusStatusBadge');
        if (!badge) return;
        badge.textContent = inside ? 'On campus' : 'Off campus';
        badge.className = 'badge ' + (inside ? 'bg-success' : 'bg-secondary');
    }

    function checkBoundary(lat, lng) {
        if (boundaryPoints.length < 3) return; // boundary not defined yet - skip silently

        const inside = isPointInPolygon(lat, lng, boundaryPoints);
        updateStatusBadge(inside);

        if (isInsideCampus === null) {
            // First fix: just record the state, don't announce it as an "entry".
            isInsideCampus = inside;
            return;
        }

        if (inside && !isInsideCampus) {
            isInsideCampus = true;
            if (typeof window.showToast === 'function') {
                window.showToast('Welcome — you are now inside the campus.', 'success');
            }
        } else if (!inside && isInsideCampus) {
            isInsideCampus = false;
            if (typeof window.showToast === 'function') {
                window.showToast('You have left the campus boundary.', 'secondary');
            }
        }
    }

    document.addEventListener('DOMContentLoaded', loadBoundary);
    if (document.readyState !== 'loading') loadBoundary();

    document.addEventListener('campus:locationUpdated', (e) => {
        checkBoundary(e.detail.lat, e.detail.lng);
    });
})();
