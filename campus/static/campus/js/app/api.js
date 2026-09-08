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

export const api = {
    locations(params = {}) {
        return request(`/api/v2/locations/?${new URLSearchParams(params)}`);
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
        return request(`/api/v2/nearby/?${new URLSearchParams({ lat, lng, limit })}`);
    },
    scan(code) {
        return request('/api/v2/scan/', { method: 'POST', body: { code } });
    },
    boundary(lat, lng) {
        const params = lat != null && lng != null ? { lat, lng } : {};
        return request(`/api/v2/boundary/?${new URLSearchParams(params)}`);
    },
    tours() {
        return request('/api/v2/tours/');
    },
    tour(slug) {
        return request(`/api/v2/tours/${encodeURIComponent(slug)}/`);
    },
};
