// geo.js - live GPS tracking + the on-campus/off-campus boundary check.
// Split out of app.js to keep the bootstrap module focused on wiring.

import { api } from './api.js';

export class GeoTracker {
    constructor({ onPosition, onStatus, onBoundaryChange, onUnavailable } = {}) {
        this.onPosition = onPosition;
        this.onStatus = onStatus;
        this.onBoundaryChange = onBoundaryChange;
        this.onUnavailable = onUnavailable;
        this.lastInside = null;
        this.watchId = null;
    }

    start() {
        if (!('geolocation' in navigator)) {
            this.onStatus && this.onStatus('Location unavailable', null);
            this.onUnavailable && this.onUnavailable();
            return;
        }

        this.onStatus && this.onStatus('Locating…', null);
        this.watchId = navigator.geolocation.watchPosition(
            (position) => {
                const point = { lat: position.coords.latitude, lng: position.coords.longitude };
                this.onPosition && this.onPosition(point);
                this._checkBoundary(point);
            },
            () => this.onStatus && this.onStatus('Location off', false),
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 },
        );
    }

    stop() {
        if (this.watchId != null) navigator.geolocation.clearWatch(this.watchId);
        this.watchId = null;
    }

    async _checkBoundary(point) {
        try {
            const boundary = await api.boundary(point.lat, point.lng);
            this.onStatus && this.onStatus(boundary.inside ? 'On campus' : 'Off campus', boundary.inside);
            if (this.lastInside !== null && this.lastInside !== boundary.inside) {
                this.onBoundaryChange && this.onBoundaryChange(boundary.inside);
            }
            this.lastInside = boundary.inside;
        } catch (err) {
            /* boundary check is best-effort - a network blip shouldn't spam errors */
        }
    }
}
