// admin-map-picker.js - small Leaflet map used on the Django admin
// add/change forms for Location and GraphNode, so you can click a point
// on the map instead of typing coordinates by hand. Fills the
// #id_latitude / #id_longitude inputs (Django admin's auto-generated
// field ids) on click.

(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const mapDiv = document.getElementById('pickerMap');
        if (!mapDiv) return;

        const config = window.CAMPUS_CONFIG || { centerLat: 33.6844, centerLng: 73.0479, defaultZoom: 17 };
        const latInput = document.getElementById('id_latitude');
        const lngInput = document.getElementById('id_longitude');

        const startLat = (latInput && latInput.value) ? parseFloat(latInput.value) : config.centerLat;
        const startLng = (lngInput && lngInput.value) ? parseFloat(lngInput.value) : config.centerLng;

        const map = L.map('pickerMap').setView([startLat, startLng], config.defaultZoom);
        addBaseLayerSwitcher(map);

        let marker = null;
        if (latInput && latInput.value && lngInput && lngInput.value) {
            marker = L.marker([startLat, startLng]).addTo(map);
        }

        map.on('click', function (e) {
            const { lat, lng } = e.latlng;

            if (marker) {
                marker.setLatLng(e.latlng);
            } else {
                marker = L.marker(e.latlng).addTo(map);
            }

            if (latInput) latInput.value = lat.toFixed(7);
            if (lngInput) lngInput.value = lng.toFixed(7);
        });
    });
})();
