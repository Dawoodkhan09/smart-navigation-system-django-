// navigation.js - Destination search + A* route request/draw.
// Flow: user picks a destination (search box or marker popup) ->
// START NAVIGATION -> POST /api/navigation/route with current GPS + destination id
// -> server runs A* -> response path is drawn as a Leaflet polyline.

(function () {
    let selectedDestinationId = null;
    let routeLine = null;
    let destinationMarker = null;

    const searchBox = document.getElementById('searchBox');
    const searchResults = document.getElementById('searchResults');
    const destNameEl = document.getElementById('destName');
    const routeDistanceEl = document.getElementById('routeDistance');
    const routeTimeEl = document.getElementById('routeTime');
    const navigateBtn = document.getElementById('navigateBtn');
    const routeMessageEl = document.getElementById('routeMessage');

    // Exposed globally so map.js marker popups (and the location-tree
    // page's ?location=<id> deep link, see home.html) can call it
    // directly. { pan: true } also recenters the map on the node - used
    // for the tree deep link so the destination is actually visible, not
    // just for search-box picks where the user is already looking at it.
    window.selectDestination = function (locationId, { pan = false } = {}) {
        const loc = (window.allLocations || []).find((l) => l.id === locationId);
        if (!loc) return;

        selectedDestinationId = locationId;
        destNameEl.textContent = loc.name;
        navigateBtn.disabled = false;
        routeMessageEl.textContent = '';

        if (pan) window.campusMap.setView([loc.latitude, loc.longitude], 19);

        // Building descriptions list the rooms/classes/offices inside
        // (e.g. "Ground floor: CS HOD, Faculty room 2-5... | 1st floor:
        // IT room, ...") - show that here so it stays visible the whole
        // time the user is navigating, not just in a popup that closes.
        const destDescriptionEl = document.getElementById('destDescription');
        if (destDescriptionEl) destDescriptionEl.textContent = loc.description || '';

        if (destinationMarker) window.campusMap.removeLayer(destinationMarker);
        const popupHtml = `<strong>${loc.name}</strong>` + (loc.description ? `<div class="small" style="white-space: pre-line;">${escapeHtml(loc.description)}</div>` : '');
        const pinSvg = '<svg viewBox="0 0 24 24" width="26" height="26" xmlns="http://www.w3.org/2000/svg">'
            + '<path d="M12 22s-7.5-6.7-7.5-12.2A7.5 7.5 0 0 1 19.5 9.8C19.5 15.3 12 22 12 22z" fill="#0f6d4c"/>'
            + '<circle cx="12" cy="9.8" r="2.6" fill="#ffffff"/></svg>';
        destinationMarker = L.marker([loc.latitude, loc.longitude], {
            icon: L.divIcon({ className: 'destination-icon', html: pinSvg, iconSize: [26, 26], iconAnchor: [13, 26] })
        }).addTo(window.campusMap).bindPopup(popupHtml).openPopup();

        if (searchResults) searchResults.innerHTML = '';
        if (searchBox) searchBox.value = loc.name;
    };

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str ?? '';
        return div.innerHTML;
    }

    async function performSearch(query) {
        const res = await fetch('/api/locations/search?q=' + encodeURIComponent(query));
        if (!res.ok) return [];
        return res.json();
    }

    function renderSearchResults(results) {
        if (!searchResults) return;
        searchResults.innerHTML = '';
        results.forEach((loc) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'list-group-item list-group-item-action';

            const title = document.createElement('div');
            title.textContent = `${loc.name} (${loc.category})`;
            item.appendChild(title);

            // Buildings store their rooms/classes/offices in `description`
            // (e.g. "Ground floor: CS HOD, Faculty room 2-5... | 1st floor:
            // IT room, ..."). Show a short preview right in the list so the
            // user can see what's inside a building while just browsing,
            // not only after clicking into it.
            if (loc.description) {
                const preview = document.createElement('div');
                preview.className = 'small text-muted';
                preview.style.whiteSpace = 'normal';
                const text = loc.description.replace(/\s+/g, ' ').trim();
                preview.textContent = text.length > 90 ? text.slice(0, 90) + '...' : text;
                item.appendChild(preview);
            }

            item.addEventListener('click', () => window.selectDestination(loc.id));
            searchResults.appendChild(item);
        });
    }

    // An empty query returns every campus location (see
    // Api\LocationController::search()), so this doubles as the "browse
    // everything" quick list, not just a filtered-results dropdown.
    async function runSearch(query) {
        const results = await performSearch(query);
        renderSearchResults(results);
    }

    if (searchBox) {
        let debounceTimer = null;
        searchBox.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const query = searchBox.value.trim();
            debounceTimer = setTimeout(() => runSearch(query), 200);
        });

        // Clicking/focusing the (still empty) search box shows the full
        // list of every campus location right away, so the user can just
        // browse instead of having to know what to type.
        searchBox.addEventListener('focus', () => {
            if (searchBox.value.trim().length === 0) runSearch('');
        });

        document.addEventListener('click', (e) => {
            if (!searchResults.contains(e.target) && e.target !== searchBox) {
                searchResults.innerHTML = '';
            }
        });
    }

    async function startNavigation() {
        routeMessageEl.textContent = '';

        if (!selectedDestinationId) {
            routeMessageEl.textContent = 'Please choose a destination first.';
            return;
        }
        if (!window.currentPosition) {
            routeMessageEl.textContent = 'Waiting for your GPS location - please allow location access.';
            return;
        }

        navigateBtn.disabled = true;
        navigateBtn.textContent = 'Calculating route...';

        try {
            const res = await fetch('/api/navigation/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    startLatitude: window.currentPosition.lat,
                    startLongitude: window.currentPosition.lng,
                    destinationLocationId: selectedDestinationId
                })
            });

            const result = await res.json();

            if (!result.success) {
                routeMessageEl.textContent = result.message || 'Could not calculate a route.';
                routeDistanceEl.textContent = '-';
                routeTimeEl.textContent = '-';
                return;
            }

            drawRoute(result.path);
            routeDistanceEl.textContent = `${result.totalDistanceMeters} m`;
            routeTimeEl.textContent = `${result.estimatedWalkingMinutes} min`;
        } catch (err) {
            routeMessageEl.textContent = 'Network error while calculating the route.';
            console.error(err);
        } finally {
            navigateBtn.disabled = false;
            navigateBtn.textContent = 'START NAVIGATION';
        }
    }

    function drawRoute(path) {
        const map = window.campusMap;
        if (routeLine) map.removeLayer(routeLine);

        const latLngs = path.map((p) => [p.latitude, p.longitude]);
        routeLine = L.polyline(latLngs, { color: '#198754', weight: 5, opacity: 0.85 }).addTo(map);
        map.fitBounds(routeLine.getBounds(), { padding: [40, 40] });
    }

    if (navigateBtn) {
        navigateBtn.addEventListener('click', startNavigation);
    }
})();