// app.js - visitor-app bootstrap. Wires together map.js, sheet.js,
// route.js, tour.js, ui.js, api.js and store.js against the DOM in
// campus/templates/campus/app/shell.html. This is the one module that's
// allowed to know about all the others; everything else stays focused.

import { api } from './api.js';
import { CampusMap } from './map.js';
import { BottomSheet } from './sheet.js';
import { GeoTracker } from './geo.js';
import * as ui from './ui.js';
import * as routeMod from './route.js';
import * as tourMod from './tour.js';
import { getLastScan, setLastScan, getThemeOverride, setThemeOverride } from './store.js';
import { icon } from './icons.js';

const config = window.APP_CONFIG || {};

const state = {
    locations: [],
    browseResults: [], // currently-shown sheet list - see refreshBrowseResults()
    activeCategory: '',
    searchTerm: '',
    userPosition: null,
    mode: 'browse', // browse | place | route | tour
    selectedLocation: null,
    routeSteps: null,
    routePath: null,
};

let searchDebounceTimer = null;

const el = {
    map: document.getElementById('map'),
    searchInput: document.getElementById('searchInput'),
    scanButton: document.getElementById('scanButton'),
    chips: document.getElementById('categoryChips'),
    sheet: document.getElementById('sheet'),
    sheetContent: document.getElementById('sheetContent'),
    locateFab: document.getElementById('locateFab'),
    themeFab: document.getElementById('themeFab'),
    offlineBanner: document.getElementById('offlineBanner'),
    toastRoot: document.getElementById('toastRoot'),
    liveRegion: document.getElementById('routeLiveRegion'),
    statusBadge: document.getElementById('statusBadge'),
};

let campusMap;
let sheet;
let tourState = null;

init();

async function init() {
    applyTheme(resolveIsDark());
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (!getThemeOverride()) applyTheme(resolveIsDark());
    });

    campusMap = new CampusMap('map', {
        center: config.campusCenter || { lat: 24.8844, lng: 67.1720 },
        zoom: config.defaultZoom || 17,
        isDark: resolveIsDark(),
    });
    campusMap.onMarkerClick = (code) => selectLocation(code);

    sheet = new BottomSheet(el.sheet, { initial: 'half' });
    sheet.onSnapChange = (name) => {
        // Focus trap: everything under the sheet becomes unreachable by
        // Tab/VoiceOver while the sheet covers almost the whole screen.
        const behind = document.getElementById('behindSheet');
        if (behind) behind.toggleAttribute('inert', name === 'full');
    };

    ui.renderCategoryChips(el.chips, state.activeCategory, onCategorySelect);
    ui.renderSkeletonCards(el.sheetContent, 5);

    bindTopBar();
    bindFabs();
    bindOfflineBanner();
    bindElementIconsOnce();

    const [locations, boundary] = await Promise.all([
        loadLocations(),
        loadBoundary(),
    ]);

    campusMap.setLocations(locations);
    campusMap.drawBoundary(boundary.points);
    renderBrowse();

    startGeolocation();

    if (config.tourSlug) {
        await enterTourMode(config.tourSlug);
    } else if (config.atCode) {
        await handleArrival(config.atCode);
    } else if (config.unknownCode) {
        ui.showToast(el.toastRoot, `Code "${config.unknownCode}" was not recognized.`, 'warn');
    }
}

// --- Data loading -----------------------------------------------------

async function loadLocations() {
    try {
        const locations = await api.locations();
        state.locations = locations;
        return locations;
    } catch (err) {
        ui.renderEmptyState(el.sheetContent, { message: 'Could not load campus locations. Check your connection.' });
        return [];
    }
}

async function loadBoundary() {
    try {
        return await api.boundary();
    } catch (err) {
        return { points: [], inside: null };
    }
}

// --- Browse / search / filter ------------------------------------------

function bindTopBar() {
    el.searchInput.addEventListener('input', () => {
        state.searchTerm = el.searchInput.value.trim();
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            if (state.mode === 'browse') refreshBrowseResults();
        }, 200);
    });
    el.scanButton.addEventListener('click', () => {
        window.location.href = '/app/scan/';
    });
}

function onCategorySelect(category) {
    state.activeCategory = category;
    ui.renderCategoryChips(el.chips, category, onCategorySelect);
    campusMap.filterByCategory(category);
    if (state.mode === 'browse') refreshBrowseResults();
}

/**
 * Re-fetches the sheet's location list from the server whenever a search
 * term or category is active. This has to go through the API rather than
 * filtering the already-loaded `state.locations` client-side: that array
 * only carries what the map needs (name/category/short one-liner), not
 * each building's full room/class listing - a building's `description`
 * (e.g. "Ground floor: CS HOD, Faculty room 2-5...") is what a search for
 * a specific class actually has to match against, and only the server
 * has that (see api_views.v2_location_list's `q` handling). An empty
 * search with no category just reuses the already-loaded full list.
 */
async function refreshBrowseResults() {
    state.mode = 'browse';
    sheet.el.setAttribute('data-mode', 'browse');

    if (!state.searchTerm && !state.activeCategory) {
        state.browseResults = state.locations;
        renderBrowseFromCache();
        return;
    }

    try {
        state.browseResults = await api.locations({ q: state.searchTerm, category: state.activeCategory });
    } catch (err) {
        state.browseResults = [];
    }
    renderBrowseFromCache();
}

/** Re-renders the sheet list from whatever refreshBrowseResults() last
 * fetched, without hitting the server again - used for cheap refreshes
 * like a live GPS update changing the shown distances. */
function renderBrowseFromCache() {
    ui.renderBrowseList(el.sheetContent, state.browseResults, {
        userPosition: state.userPosition,
        onSelect: selectLocation,
        onClearFilters: () => {
            state.searchTerm = '';
            state.activeCategory = '';
            el.searchInput.value = '';
            ui.renderCategoryChips(el.chips, '', onCategorySelect);
            campusMap.filterByCategory('');
            refreshBrowseResults();
        },
    });
}

function renderBrowse() {
    state.mode = 'browse';
    sheet.el.setAttribute('data-mode', 'browse');
    state.browseResults = state.locations;
    renderBrowseFromCache();
}

// --- Place selection -----------------------------------------------------

async function selectLocation(code) {
    campusMap.selectLocation(code);
    try {
        const detail = await api.location(code);
        state.selectedLocation = detail;
        state.mode = 'place';
        sheet.el.setAttribute('data-mode', 'place');
        campusMap.flyTo(detail.lat, detail.lng);
        sheet.snapTo('half');
        ui.renderPlaceDetail(el.sheetContent, detail, {
            onDirections: () => startDirections(detail),
            onShare: () => shareLocation(detail),
            onNearbySelect: selectLocation,
        });
    } catch (err) {
        ui.showToast(el.toastRoot, 'Could not load that place.', 'warn');
    }
}

function shareLocation(location) {
    const url = `${window.location.origin}/l/${location.code}/`;
    if (navigator.share) {
        navigator.share({ title: location.name, url }).catch(() => {});
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => ui.showToast(el.toastRoot, 'Link copied.'));
    }
}

// --- QR-scan arrival -----------------------------------------------------

async function handleArrival(code) {
    try {
        const location = await api.location(code);
        setLastScan(code, location);
        campusMap.showYouAreHere(location.lat, location.lng);
        campusMap.flyTo(location.lat, location.lng, 18);
        ui.showToast(el.toastRoot, `You're at ${location.name}`);
        await selectLocation(code);
        sheet.snapTo('half');
    } catch (err) {
        ui.showToast(el.toastRoot, 'That QR code was not recognized.', 'warn');
    }
}

function getRouteOrigin() {
    const lastScan = getLastScan();
    if (lastScan) return { type: 'code', code: lastScan.code, name: lastScan.name, trusted: true };
    if (state.userPosition) return { type: 'gps', lat: state.userPosition.lat, lng: state.userPosition.lng };
    return null;
}

// --- Routing mode -----------------------------------------------------

async function startDirections(destination) {
    const origin = getRouteOrigin();
    if (!origin) {
        ui.showToast(el.toastRoot, 'Waiting for your location - allow location access or scan a QR code first.', 'warn');
        return;
    }

    state.mode = 'route';
    sheet.el.setAttribute('data-mode', 'route');
    sheet.snapTo('half');

    const result = await routeMod.fetchRoute(origin, destination.code);

    if (!result.ok) {
        ui.renderNoRoute(el.sheetContent, result.message, () => selectLocation(destination.code));
        return;
    }

    const { data } = result;
    state.routeSteps = data.steps;
    state.routePath = data.path;

    routeMod.animateRouteIn(campusMap, data.path);

    const stepListEl = ui.renderRouteHeader(el.sheetContent, {
        originName: origin.trusted ? origin.name : data.origin_name,
        destinationName: destination.name,
        distanceM: data.distance_m,
        durationMin: data.duration_min,
    }, () => exitRoute(destination));

    routeMod.renderStepList(stepListEl, data.steps, {
        onStepClick: (step) => {
            const idx = data.steps.indexOf(step);
            const point = data.path[Math.min(idx, data.path.length - 1)];
            campusMap.flyTo(point.lat, point.lng, 19);
        },
    });

    if (el.liveRegion) {
        el.liveRegion.textContent = `Route to ${destination.name}: ${routeMod.formatDistance(data.distance_m)}, about ${data.duration_min} minutes walking.`;
    }
}

function exitRoute(destination) {
    campusMap.clearRoute();
    selectLocation(destination.code);
}

// --- Tour mode -----------------------------------------------------

async function enterTourMode(slug) {
    try {
        const tour = await tourMod.loadTour(slug);
        tourState = new tourMod.TourState(tour);
        state.mode = 'tour';
        sheet.el.setAttribute('data-mode', 'tour');
        sheet.snapTo('half');
        renderTourCover();
    } catch (err) {
        ui.showToast(el.toastRoot, 'Could not load that tour.', 'warn');
    }
}

function renderTourCover() {
    el.sheetContent.innerHTML = tourMod.renderCoverCard(tourState.tour);
    el.sheetContent.querySelector('[data-action="start-tour"]').addEventListener('click', () => {
        tourState.start();
        renderTourStop();
    });
}

function renderTourStop() {
    const stop = tourState.stop;
    campusMap.selectLocation(stop.location.code);
    campusMap.flyTo(stop.location.lat, stop.location.lng, 18);

    el.sheetContent.innerHTML = '<div class="tour-progress" data-progress></div>' + tourMod.renderStopCard(tourState);
    tourMod.renderProgressBar(el.sheetContent.querySelector('[data-progress]'), tourState.tour.stops.length, tourState.index);

    const prevBtn = el.sheetContent.querySelector('[data-action="tour-prev"]');
    const nextBtn = el.sheetContent.querySelector('[data-action="tour-next"]');
    const doneBtn = el.sheetContent.querySelector('[data-action="tour-done"]');
    if (prevBtn) prevBtn.addEventListener('click', () => { tourState.goPrevious(); renderTourStop(); });
    if (nextBtn) nextBtn.addEventListener('click', () => advanceTour());
    if (doneBtn) doneBtn.addEventListener('click', () => finishTour());

    if (tourState.nextStop) {
        routeMod.fetchRoute({ type: 'code', code: stop.location.code }, tourState.nextStop.location.code).then((result) => {
            if (result.ok) routeMod.animateRouteIn(campusMap, result.data.path);
        });
    } else {
        campusMap.clearRoute();
    }
}

function advanceTour() {
    tourState.goNext();
    renderTourStop();
}

function finishTour() {
    campusMap.clearRoute();
    el.sheetContent.innerHTML = tourMod.renderCelebration(tourState.tour);
    el.sheetContent.querySelector('[data-action="tour-exit"]').addEventListener('click', () => {
        tourState = null;
        window.location.href = '/app/';
    });
}

// --- Geolocation -----------------------------------------------------

const geoTracker = new GeoTracker({
    onPosition: (point) => {
        state.userPosition = point;
        campusMap.showYouAreHere(point.lat, point.lng);
        // Cache-only re-render (not refreshBrowseResults()) - a GPS tick
        // just needs to update the shown distances, not re-run the search.
        if (state.mode === 'browse') renderBrowseFromCache();
    },
    onStatus: setStatus,
    onBoundaryChange: (inside) => {
        ui.showToast(el.toastRoot, inside ? 'Welcome — you are now inside the campus.' : 'You have left the campus boundary.');
    },
});

function startGeolocation() {
    geoTracker.start();
}

function setStatus(text, inside) {
    if (!el.statusBadge) return;
    el.statusBadge.textContent = text;
    el.statusBadge.className = 'status-badge pill' + (inside === true ? ' status-on' : inside === false ? ' status-off' : '');
}

// --- FABs, theme, offline -----------------------------------------------------

function bindFabs() {
    el.locateFab.addEventListener('click', () => {
        if (state.userPosition) {
            campusMap.flyTo(state.userPosition.lat, state.userPosition.lng, 18);
            el.locateFab.classList.add('fab-active');
        } else {
            startGeolocation();
        }
    });
    if (el.themeFab) {
        el.themeFab.addEventListener('click', () => {
            const next = resolveIsDark() ? 'light' : 'dark';
            setThemeOverride(next);
            applyTheme(next === 'dark');
        });
    }
}

function resolveIsDark() {
    const override = getThemeOverride();
    if (override) return override === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function applyTheme(isDark) {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    if (campusMap) campusMap.setDarkTiles(isDark);
    if (el.themeFab) el.themeFab.innerHTML = icon(isDark ? 'sun' : 'moon');
}

function bindOfflineBanner() {
    const update = () => {
        const offline = !navigator.onLine;
        el.offlineBanner.hidden = !offline;
        el.scanButton.disabled = offline;
    };
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    update();
}

function bindElementIconsOnce() {
    document.querySelectorAll('[data-icon]').forEach((node) => {
        node.innerHTML = icon(node.dataset.icon);
    });
}
