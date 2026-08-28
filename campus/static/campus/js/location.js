// location.js - Browser Geolocation API: tracks the user's current
// position and shows a moving "You are here" marker on the map.
// Fires a `campus:locationUpdated` document event with { lat, lng, accuracy }
// every time a new position arrives, so geofence.js and navigation.js can react.

(function () {
    let youAreHereMarker = null;
    let accuracyCircle = null;
    let watchId = null;

    window.currentPosition = null; // { lat, lng, accuracy }

    function onPosition(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const accuracy = position.coords.accuracy;

        window.currentPosition = { lat, lng, accuracy };

        const map = window.campusMap;
        if (!map) return;

        if (!youAreHereMarker) {
            const icon = L.divIcon({
                className: 'you-are-here-icon',
                html: '<div class="you-are-here-dot"></div>',
                iconSize: [18, 18]
            });
            youAreHereMarker = L.marker([lat, lng], { icon, zIndexOffset: 1000 })
                .addTo(map)
                .bindPopup('You are here');
            accuracyCircle = L.circle([lat, lng], { radius: accuracy, color: '#0d6efd', weight: 1, fillOpacity: 0.08 }).addTo(map);
        } else {
            youAreHereMarker.setLatLng([lat, lng]);
            accuracyCircle.setLatLng([lat, lng]);
            accuracyCircle.setRadius(accuracy);
        }

        document.dispatchEvent(new CustomEvent('campus:locationUpdated', { detail: { lat, lng, accuracy } }));
    }

    function onPositionError(err) {
        console.warn('Geolocation error:', err.message);
        const msgEl = document.getElementById('routeMessage');
        if (msgEl) {
            msgEl.textContent = 'Could not get your location: ' + err.message + ' (allow location access in your browser).';
        }
    }

    function startTracking() {
        const msgEl = document.getElementById('routeMessage');

        if (!navigator.geolocation) {
            alert('Geolocation is not supported by this browser.');
            return;
        }

        // Geolocation silently refuses to even show the permission prompt
        // on an insecure origin (plain http on anything other than
        // localhost/127.0.0.1) - this is the #1 reason it looks like
        // "nothing is happening". Surface that clearly instead of failing
        // silently.
        if (window.isSecureContext === false) {
            console.error('Geolocation blocked: not a secure context. Use http://localhost or http://127.0.0.1, or HTTPS.');
            if (msgEl) {
                msgEl.textContent = 'Location needs a secure page (http://localhost or http://127.0.0.1, or HTTPS) - the browser won\'t even ask for permission otherwise.';
            }
            return;
        }

        // If the Permissions API is available, report the current state up
        // front (helps tell "browser already blocked this site before"
        // apart from "browser hasn't asked yet").
        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({ name: 'geolocation' }).then((status) => {
                console.log('Geolocation permission state:', status.state);
                if (status.state === 'denied' && msgEl) {
                    msgEl.textContent = 'Location is blocked for this site in your browser settings - click the padlock/site-info icon next to the address bar and allow Location, then reload.';
                }
            }).catch(() => { /* Permissions API not supported for this query - ignore */ });
        }

        // Get an initial fix immediately...
        navigator.geolocation.getCurrentPosition(onPosition, onPositionError, {
            enableHighAccuracy: true,
            timeout: 10000
        });

        // ...then keep watching for movement.
        watchId = navigator.geolocation.watchPosition(onPosition, onPositionError, {
            enableHighAccuracy: true,
            maximumAge: 2000,
            timeout: 15000
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        startTracking();

        const locateBtn = document.getElementById('locateBtn');
        if (locateBtn) {
            locateBtn.addEventListener('click', () => {
                if (window.currentPosition && window.campusMap) {
                    window.campusMap.setView([window.currentPosition.lat, window.currentPosition.lng], 19);
                } else {
                    startTracking();
                }
            });
        }
    });
})();