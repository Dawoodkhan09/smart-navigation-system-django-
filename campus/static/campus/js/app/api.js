// api.js - thin fetch wrapper around the /api/v2/... endpoints
// (campus/api_views.py). Every visitor-app module goes through here
// instead of calling fetch() directly, so the CSRF header and error
// handling live in exactly one place.

import { getCsrfToken } from './store.js';

async function request(path, { method = 'GET', body } = {}) {
    const options = { method, headers: {} };

    if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }
    if (method !== 'GET') {
        options.headers['X-CSRFToken'] = getCsrfToken();
    }

    let response;
    try {
        response = await fetch(path, options);
    } catch (err) {
        throw new ApiError('network', 'Could not reach the server. Check your connection.');
    }

    let data = null;
    try {
        data = await response.json();
    } catch (err) {
        /* empty/non-JSON body is fine for some responses */
    }

    if (!response.ok) {
        throw new ApiError((data && data.error) || 'http_error', (data && data.message) || `Request failed (${response.status}).`, response.status);
    }

    return data;
}

export class ApiError extends Error {
    constructor(code, message, status) {
        super(message);
        this.code = code;
        this.status = status;
    }
}

// Which campus's data every campus-scoped call below fetches (locations,
// nearby, boundary - the endpoints that don't already identify a campus
// via a globally-unique code of their own). Set once by app.js after it
// resolves the active campus (from a QR scan, the server's initial
// render, or a remembered previous scan) - see store.getActiveCampus().
let activeCampusSlug = '';
export function setCampusSlug(slug) {
    activeCampusSlug = slug || '';
}

function withCampus(params = {}) {
    return activeCampusSlug ? { ...params, campus: activeCampusSlug } : params;
}

export const api = {
    locations(params = {}) {
        return request(`/api/v2/locations/?${new URLSearchParams(withCampus(params))}`);
    },
    location(code) {
        return request(`/api/v2/locations/${encodeURIComponent(code)}/`);
    },
    route(fromCode, toCode) {
        return request(`/api/v2/route/?${new URLSearchParams({ from: fromCode, to: toCode })}`);
    },
    routeFromGps(lat, lng, toCode) {
        return request(`/api/v2/route/?${new URLSearchParams({ from_lat: lat, from_lng: lng, to: toCode })}`);
    },
    nearby(lat, lng, limit = 5) {
        return request(`/api/v2/nearby/?${new URLSearchParams(withCampus({ lat, lng, limit }))}`);
    },
    scan(code) {
        return request('/api/v2/scan/', { method: 'POST', body: { code } });
    },
    boundary(lat, lng) {
        const base = lat != null && lng != null ? { lat, lng } : {};
        return request(`/api/v2/boundary/?${new URLSearchParams(withCampus(base))}`);
    },
    tours() {
        return request('/api/v2/tours/');
    },
    tour(slug) {
        return request(`/api/v2/tours/${encodeURIComponent(slug)}/`);
    },
};
