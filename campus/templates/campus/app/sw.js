// sw.js - visitor-app service worker. Served from root scope (see
// campus_navigation/urls.py - a TemplateView, not a static file, so the
// scope covers the whole site and not just /static/campus/js/).
//
// Strategy: cache-first for static assets and map tiles (they rarely
// change and a cache hit is instant), network-first with a cache
// fallback for /api/v2/locations/ (fresh data when online, still
// something to show when offline).

const CACHE_VERSION = 'campus-guide-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

const PRECACHE_URLS = [
    '/app/',
    '/static/campus/css/app.css',
    '/static/campus/js/app/app.js',
    '/static/campus/js/app/api.js',
    '/static/campus/js/app/map.js',
    '/static/campus/js/app/sheet.js',
    '/static/campus/js/app/route.js',
    '/static/campus/js/app/tour.js',
    '/static/campus/js/app/ui.js',
    '/static/campus/js/app/icons.js',
    '/static/campus/js/app/store.js',
    '/static/campus/img/icon-192.png',
    '/static/campus/img/icon-512.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS)).catch(() => {}),
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys
                .filter((key) => key.startsWith('campus-guide-') && key !== STATIC_CACHE && key !== API_CACHE)
                .map((key) => caches.delete(key)),
        )),
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    if (url.pathname.startsWith('/api/v2/locations')) {
        event.respondWith(networkFirst(request, API_CACHE));
        return;
    }

    const isStaticAsset = url.pathname.startsWith('/static/') || url.hostname.includes('basemaps.cartocdn.com') || url.hostname.includes('unpkg.com');
    if (isStaticAsset) {
        event.respondWith(cacheFirst(request, STATIC_CACHE));
        return;
    }

    if (url.pathname === '/app/' || url.pathname.startsWith('/app/')) {
        event.respondWith(networkFirst(request, STATIC_CACHE));
    }
});

async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response && response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        return cached || Response.error();
    }
}

async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response && response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const cached = await caches.match(request);
        if (cached) return cached;
        throw err;
    }
}
