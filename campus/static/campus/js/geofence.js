// geofence.js - Geofencing using the Haversine formula (haversine.js).
// On every GPS update: for each campus location, compute the distance from
// the user to that location's center and compare it with its
// GeofenceRadius. Only fires a notification when the state actually
// changes (outside -> inside = "entered", inside -> outside = "left") so
// the same event doesn't repeat on every GPS tick.

(function () {
    // locationId -> boolean (true = currently inside that geofence)
    const geofenceState = {};

    function logEvent(message) {
        const log = document.getElementById('geofenceLog');
        if (!log) return;
        if (log.textContent === 'No zone events yet.') log.textContent = '';
        const line = document.createElement('div');
        const time = new Date().toLocaleTimeString();
        line.textContent = `[${time}] ${message}`;
        log.prepend(line);
    }

    function checkGeofences(userLat, userLng) {
        const locations = window.allLocations || [];

        locations.forEach((loc) => {
            const distance = haversineDistanceMeters(userLat, userLng, loc.latitude, loc.longitude);
            const isInside = distance <= loc.geofenceRadius;
            const wasInside = geofenceState[loc.id] === true;

            if (isInside && !wasInside) {
                geofenceState[loc.id] = true;
                logEvent(`Entered ${loc.name} zone`);
                window.showToast(`Entered <strong>${loc.name}</strong>${loc.description ? ' — ' + loc.description : ''}`, 'success');
            } else if (!isInside && wasInside) {
                geofenceState[loc.id] = false;
                logEvent(`Left ${loc.name} zone`);
                window.showToast(`Left <strong>${loc.name}</strong>`, 'secondary');
            }
        });
    }

    document.addEventListener('campus:locationUpdated', (e) => {
        checkGeofences(e.detail.lat, e.detail.lng);
    });
})();
