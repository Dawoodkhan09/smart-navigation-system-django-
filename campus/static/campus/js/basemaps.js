// basemaps.js - shared helper: adds a Street/Satellite base layer switcher
// to a Leaflet map. Both layers are free, no API key required:
//   - "Street" = OpenStreetMap
//   - "Satellite" = Esri World Imagery (free ArcGIS Online tile service)
// Satellite view is especially useful when placing campus boundary points
// or building markers, since you can actually see roofs/paths/walls
// instead of a plain street map.
//
// Usage: const map = L.map('someDiv').setView(...);
//        addBaseLayerSwitcher(map); // adds Street as default + a layer control

function addBaseLayerSwitcher(map, options) {
    options = options || {};

    const street = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        attribution: '&copy; OpenStreetMap contributors'
    });

    const satellite = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
            maxZoom: 19,
            attribution: 'Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community'
        }
    );

    const defaultLayer = options.defaultSatellite ? satellite : street;
    defaultLayer.addTo(map);

    L.control.layers({ 'Street': street, 'Satellite': satellite }, null, { position: 'topright' }).addTo(map);

    return { street, satellite };
}
