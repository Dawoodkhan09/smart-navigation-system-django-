// store.js - small localStorage-backed helpers: the QR-scan origin
// ("campus.lastScan"), the manual dark/light override, and reading the
// CSRF cookie for POSTs. No framework, no build step.

const LAST_SCAN_KEY = 'campus.lastScan';
const THEME_KEY = 'campus.theme';
const ACTIVE_CAMPUS_KEY = 'campus.activeCampus';
const SCAN_TTL_MS = 30 * 60 * 1000; // 30 minutes

/** Which campus the visitor scanned into last - set by a campus QR, a
 * location QR (every Location belongs to exactly one campus), or a
 * manual switch. Remembered indefinitely (no TTL, unlike lastScan) so
 * re-opening the app later still knows which campus to load without
 * asking again. */
export function getActiveCampus() {
    try {
        return localStorage.getItem(ACTIVE_CAMPUS_KEY) || '';
    } catch (err) {
        return '';
    }
}

export function setActiveCampus(slug) {
    try {
        if (slug) localStorage.setItem(ACTIVE_CAMPUS_KEY, slug);
        else localStorage.removeItem(ACTIVE_CAMPUS_KEY);
    } catch (err) {
        /* ignore */
    }
}

/** Records the Location the visitor just scanned/landed on as the
 * trusted routing origin for the next 30 minutes (see the visitor-app
 * spec: "more trustworthy than GPS"). */
export function setLastScan(code, location) {
    try {
        localStorage.setItem(LAST_SCAN_KEY, JSON.stringify({
            code,
            lat: location.lat,
            lng: location.lng,
            name: location.name,
            at: Date.now(),
        }));
    } catch (err) {
        // Storage disabled/full - the scan origin just won't persist across reloads.
        console.warn('[store] could not persist lastScan', err);
    }
}

/** Returns the last scan record if it's still within its 30-minute
 * window, otherwise null (and clears the expired entry). */
export function getLastScan() {
    let raw;
    try {
        raw = localStorage.getItem(LAST_SCAN_KEY);
    } catch (err) {
        return null;
    }
    if (!raw) return null;

    try {
        const record = JSON.parse(raw);
        if (Date.now() - record.at > SCAN_TTL_MS) {
            clearLastScan();
            return null;
        }
        return record;
    } catch (err) {
        return null;
    }
}

export function clearLastScan() {
    try {
        localStorage.removeItem(LAST_SCAN_KEY);
    } catch (err) {
        /* ignore */
    }
}

export function getThemeOverride() {
    try {
        return localStorage.getItem(THEME_KEY); // 'light' | 'dark' | null
    } catch (err) {
        return null;
    }
}

export function setThemeOverride(theme) {
    try {
        if (theme) localStorage.setItem(THEME_KEY, theme);
        else localStorage.removeItem(THEME_KEY);
    } catch (err) {
        /* ignore */
    }
}

/** Reads Django's csrftoken cookie, set by {% csrf_token %} in
 * base_app.html, for the X-CSRFToken header on POSTs (api.js). */
export function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}
