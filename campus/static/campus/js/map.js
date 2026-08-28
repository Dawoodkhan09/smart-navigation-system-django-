// map.js - Leaflet map setup + campus location markers.
// Exposes: window.campusMap, window.selectDestination(location)

(function () {
    const config = window.CAMPUS_CONFIG || { centerLat: 33.6844, centerLng: 73.0479, defaultZoom: 17 };

    const map = L.map('map').setView([config.centerLat, config.centerLng], config.defaultZoom);
    window.campusMap = map;

    // Street (OpenStreetMap) + Satellite (Esri, free) layer switcher - see basemaps.js.
    addBaseLayerSwitcher(map);

    // Layer group that shows ONLY the currently searched/selected
    // location's marker - not every campus location at once (that got
    // cluttered fast with 15+ overlapping pins/circles). The full list
    // still loads into window.allLocations (needed by geofence.js,
    // boundary.js and the search box), it just isn't drawn on the map
    // until the user actually picks something - see
    // window.selectDestination() in navigation.js.
    window.locationsLayer = L.layerGroup().addTo(map);
    window.allLocations = [];

    async function loadLocations() {
        const res = await fetch('/api/locations');
        if (!res.ok) return;
        window.allLocations = await res.json();
    }

    document.addEventListener('DOMContentLoaded', loadLocations);
    if (document.readyState !== 'loading') loadLocations();

    window.reloadCampusLocations = loadLocations;
})();