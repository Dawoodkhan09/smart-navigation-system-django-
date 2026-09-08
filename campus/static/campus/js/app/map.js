// map.js - Leaflet setup for the visitor app: base tiles (light/dark),
// campus boundary, custom category markers, selection state. Leaflet
// itself comes from the CDN <script> in base_app.html - this module just
// drives it.

import { categoryIcon } from './icons.js';

const LIGHT_TILES = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const DARK_TILES = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

export class CampusMap {
    constructor(elementId, { center, zoom, isDark }) {
        this.map = L.map(elementId, {
            center: [center.lat, center.lng],
            zoom,
            zoomControl: false,
            attributionControl: true,
        });
        this.map.attributionControl.setPrefix(false);

        this.tileLayer = L.tileLayer(isDark ? DARK_TILES : LIGHT_TILES, {
            attribution: TILE_ATTRIBUTION,
            maxZoom: 20,
            subdomains: 'abcd',
        }).addTo(this.map);

        this.markersByCode = new Map();
        this.selectedCode = null;
        this.boundaryLayer = null;
        this.youAreHereLayer = null;
        this.routeLayer = null;
        this.onMarkerClick = null;
    }

    setDarkTiles(isDark) {
        this.tileLayer.setUrl(isDark ? DARK_TILES : LIGHT_TILES);
    }

    drawBoundary(points) {
        if (this.boundaryLayer) this.map.removeLayer(this.boundaryLayer);
        if (!points || points.length < 3) return;

        this.boundaryLayer = L.polygon(points.map((p) => [p.lat, p.lng]), {
            color: 'var(--accent-line, #0E7C66)',
            className: 'campus-boundary',
            weight: 2,
            dashArray: '6 5',
            fillOpacity: 0.08,
            interactive: false,
        }).addTo(this.map);
    }

    setLocations(locations) {
        this.markersByCode.forEach((marker) => this.map.removeLayer(marker));
        this.markersByCode.clear();

        locations.forEach((location) => {
            const marker = L.marker([location.lat, location.lng], {
                icon: this._pinIcon(location, false),
                keyboard: false,
            });
            marker.on('click', () => this.onMarkerClick && this.onMarkerClick(location.code));
            marker.addTo(this.map);
            this.markersByCode.set(location.code, { marker, location });
        });
    }

    filterByCategory(category) {
        this.markersByCode.forEach(({ marker, location }) => {
            const visible = !category || location.category.toLowerCase() === category.toLowerCase();
            const el = marker.getElement();
            if (el) el.style.display = visible ? '' : 'none';
        });
    }

    selectLocation(code) {
        if (this.selectedCode && this.markersByCode.has(this.selectedCode)) {
            const prev = this.markersByCode.get(this.selectedCode);
            prev.marker.setIcon(this._pinIcon(prev.location, false));
        }
        this.selectedCode = code;
        if (code && this.markersByCode.has(code)) {
            const entry = this.markersByCode.get(code);
            entry.marker.setIcon(this._pinIcon(entry.location, true));
        }
    }

    flyTo(lat, lng, zoom = 18) {
        this.map.flyTo([lat, lng], zoom, { duration: 0.8 });
    }

    fitBoundsPadded(latLngs, bottomPadding = 260) {
        const bounds = L.latLngBounds(latLngs);
        this.map.fitBounds(bounds, { padding: [60, 60], paddingBottomRight: [60, bottomPadding] });
    }

    showYouAreHere(lat, lng) {
        if (this.youAreHereLayer) this.map.removeLayer(this.youAreHereLayer);
        const el = document.createElement('div');
        el.className = 'you-are-here';
        el.innerHTML = '<span class="yah-ring yah-ring-1"></span><span class="yah-ring yah-ring-2"></span><span class="yah-dot"></span>';
        this.youAreHereLayer = L.marker([lat, lng], {
            icon: L.divIcon({ html: el.outerHTML, className: 'you-are-here-icon', iconSize: [18, 18], iconAnchor: [9, 9] }),
            zIndexOffset: 1000,
            keyboard: false,
            interactive: false,
        }).addTo(this.map);
    }

    drawRoute(path) {
        this.clearRoute();
        const latLngs = path.map((p) => [p.lat, p.lng]);
        const casing = L.polyline(latLngs, { color: 'var(--route-casing, #0a5c4c)', weight: 9, opacity: 0.9, lineCap: 'round', lineJoin: 'round' }).addTo(this.map);
        const line = L.polyline(latLngs, { color: 'var(--accent, #0E7C66)', weight: 5, opacity: 0.95, lineCap: 'round', lineJoin: 'round' }).addTo(this.map);
        this.routeLayer = L.layerGroup([casing, line]).addTo(this.map);
        return latLngs;
    }

    clearRoute() {
        if (this.routeLayer) {
            this.map.removeLayer(this.routeLayer);
            this.routeLayer = null;
        }
    }

    _pinIcon(location, selected) {
        const scale = selected ? 1.25 : 1;
        const size = 34 * scale;
        const html = `
            <div class="pin ${selected ? 'pin-selected' : ''}" style="width:${size}px;height:${size}px;">
                <span class="pin-glyph">${categoryIcon(location.category)}</span>
            </div>`;
        return L.divIcon({
            html,
            className: 'campus-pin-wrap',
            iconSize: [size, size],
            iconAnchor: [size / 2, size],
            popupAnchor: [0, -size],
        });
    }
}
