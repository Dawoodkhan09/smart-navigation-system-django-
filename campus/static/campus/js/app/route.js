// route.js - routing mode: fetch a route from /api/v2/route/, draw it,
// animate it in, and render/track the turn-by-turn step list. Reuses
// campus.map's drawRoute() for the actual polyline; this module owns the
// step list DOM and the "which step am I on" live-tracking logic.

import { api, ApiError } from './api.js';
import { icon } from './icons.js';

const STEP_ICONS = {
    'Continue straight': 'arrowUp',
    'Turn slight left': 'arrowUpLeft',
    'Turn slight right': 'arrowUpRight',
    'Turn left': 'arrowUpLeft',
    'Turn right': 'arrowUpRight',
    'Turn sharp left': 'arrowUpLeft',
    'Turn sharp right': 'arrowUpRight',
};

function stepIconFor(instruction) {
    if (instruction.startsWith('Head ')) return 'arrowUp';
    if (instruction.startsWith('Arrive')) return 'flag';
    return STEP_ICONS[instruction] || 'arrowUp';
}

/** origin: { type: 'code', code } | { type: 'gps', lat, lng } */
export async function fetchRoute(origin, toCode) {
    try {
        const data = origin.type === 'gps'
            ? await api.routeFromGps(origin.lat, origin.lng, toCode)
            : await api.route(origin.code, toCode);
        return { ok: true, data };
    } catch (err) {
        if (err instanceof ApiError) return { ok: false, message: err.message };
        return { ok: false, message: 'Could not calculate a route.' };
    }
}

/** Draws the route, then grows the polyline in over ~600ms by
 * progressively revealing more of its coordinate array. */
export function animateRouteIn(campusMap, path) {
    const fullLatLngs = path.map((p) => [p.lat, p.lng]);
    if (fullLatLngs.length < 2) return;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        campusMap.drawRoute(path);
        campusMap.fitBoundsPadded(fullLatLngs);
        return;
    }

    campusMap.clearRoute();
    const steps = 18;
    let frame = 0;
    const total = fullLatLngs.length;

    function tick() {
        frame += 1;
        const count = Math.max(2, Math.round((frame / steps) * total));
        campusMap.drawRoute(path.slice(0, count));
        if (frame < steps) {
            requestAnimationFrame(tick);
        } else {
            campusMap.drawRoute(path); // ensure the final frame is exact
        }
    }
    requestAnimationFrame(tick);
    campusMap.fitBoundsPadded(fullLatLngs);
}

export function renderStepList(container, steps, { onStepClick } = {}) {
    container.innerHTML = '';
    steps.forEach((step, index) => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = 'step-row';
        row.dataset.stepIndex = String(index);
        row.innerHTML = `
            <span class="step-icon">${icon(stepIconFor(step.instruction))}</span>
            <span class="step-text">
                <span class="step-instruction">${escapeHtml(step.instruction)}</span>
                ${step.distance_m > 0 ? `<span class="step-distance">${formatDistance(step.distance_m)}</span>` : ''}
            </span>`;
        row.addEventListener('click', () => onStepClick && onStepClick(step, index));
        container.appendChild(row);
    });
}

/** Greys out completed steps and highlights the current one, based on
 * how far along the path's cumulative distance the live GPS fix is. */
export function highlightCurrentStep(container, steps, completedCount) {
    const rows = container.querySelectorAll('.step-row');
    rows.forEach((row, index) => {
        row.classList.toggle('step-done', index < completedCount);
        row.classList.toggle('step-current', index === completedCount);
    });
}

export function formatDistance(meters) {
    if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
    return `${Math.round(meters)} m`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
}
