// ui.js - DOM-rendering helpers for the sheet's card lists, place detail,
// toasts, skeletons and empty states. Kept separate from app.js so the
// bootstrap/wiring module stays readable.

import { icon, categoryIcon } from './icons.js';
import { formatDistance } from './route.js';

const CATEGORIES = ['academic', 'food', 'facility', 'sports', 'parking', 'admin', 'entrance'];

export function renderCategoryChips(container, activeCategory, onSelect) {
    container.innerHTML = '';
    const allChip = makeChip('All', '', activeCategory === '');
    container.appendChild(allChip);

    CATEGORIES.forEach((cat) => {
        container.appendChild(makeChip(capitalize(cat), cat, activeCategory === cat));
    });

    container.querySelectorAll('.chip').forEach((chip) => {
        chip.addEventListener('click', () => onSelect(chip.dataset.category));
    });

    function makeChip(label, value, active) {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'chip' + (active ? ' chip-active' : '');
        chip.dataset.category = value;
        chip.textContent = label;
        return chip;
    }
}

export function renderSkeletonCards(container, count = 5) {
    container.innerHTML = Array.from({ length: count }).map(() => `
        <div class="loc-card loc-card-skeleton">
            <div class="skeleton skeleton-thumb"></div>
            <div class="loc-card-body">
                <div class="skeleton skeleton-line" style="width:60%"></div>
                <div class="skeleton skeleton-line" style="width:40%"></div>
            </div>
        </div>`).join('');
}

export function renderEmptyState(container, { message, actionLabel, onAction } = {}) {
    container.innerHTML = `
        <div class="empty-state">
            <p>${escapeHtml(message)}</p>
            ${actionLabel ? '<button type="button" class="btn-secondary" data-empty-action>' + escapeHtml(actionLabel) + '</button>' : ''}
        </div>`;
    if (onAction) {
        const btn = container.querySelector('[data-empty-action]');
        if (btn) btn.addEventListener('click', onAction);
    }
}

export function renderBrowseList(container, locations, { userPosition, onSelect } = {}) {
    if (!locations.length) {
        renderEmptyState(container, { message: 'No places match your search.', actionLabel: 'Clear filters' });
        return;
    }

    container.innerHTML = '<div class="sheet-title">Explore campus</div>' + locations.map((loc) => locationCardHtml(loc, userPosition)).join('');
    container.querySelectorAll('[data-loc-code]').forEach((card) => {
        card.addEventListener('click', () => onSelect(card.dataset.locCode));
    });
}

function locationCardHtml(loc, userPosition) {
    const distance = userPosition ? haversineApprox(userPosition, loc) : null;
    const openBadge = loc.isOpenNow === true ? '<span class="dot dot-open"></span>Open'
        : loc.isOpenNow === false ? '<span class="dot dot-closed"></span>Closed'
        : '';

    return `
        <button type="button" class="loc-card" data-loc-code="${loc.code}">
            <span class="loc-thumb">${loc.photoUrl ? `<img src="${loc.photoUrl}" alt="">` : categoryIcon(loc.category)}</span>
            <span class="loc-card-body">
                <span class="loc-name">${escapeHtml(loc.name)}</span>
                <span class="loc-meta">
                    <span class="pill">${escapeHtml(loc.category)}</span>
                    ${distance != null ? `<span class="loc-distance">${formatDistance(distance)}</span>` : ''}
                    ${openBadge ? `<span class="open-status">${openBadge}</span>` : ''}
                </span>
            </span>
        </button>`;
}

export function renderPlaceDetail(container, location, { onDirections, onShare, onNearbySelect } = {}) {
    const openBadge = location.isOpenNow === true ? '<span class="pill pill-open">Open now</span>'
        : location.isOpenNow === false ? '<span class="pill pill-closed">Closed</span>'
        : '';

    container.innerHTML = `
        <div class="place-detail">
            ${location.photoUrl
                ? `<div class="place-hero" style="background-image:url('${location.photoUrl}')"><span class="place-hero-scrim"><span class="place-hero-name">${escapeHtml(location.name)}</span></span></div>`
                : `<div class="place-hero place-hero-noimg"><span class="place-hero-name">${escapeHtml(location.name)}</span></div>`}
            <div class="place-pills">
                <span class="pill">${escapeHtml(location.category)}</span>
                ${location.floorCount ? `<span class="pill">${location.floorCount} floor${location.floorCount === 1 ? '' : 's'}</span>` : ''}
                ${openBadge}
            </div>
            <p class="place-description">${escapeHtml(location.description || location.shortDescription || '')}</p>
            <button type="button" class="btn-primary btn-block" data-action="directions">${icon('flag')} Directions</button>
            <button type="button" class="btn-secondary btn-block" data-action="share">${icon('share')} Share</button>
            ${location.nearby && location.nearby.length ? `
                <div class="sheet-subtitle">Nearby</div>
                <div class="nearby-row">${location.nearby.map(nearbyCardHtml).join('')}</div>` : ''}
        </div>`;

    const directionsBtn = container.querySelector('[data-action="directions"]');
    if (directionsBtn) directionsBtn.addEventListener('click', onDirections);
    const shareBtn = container.querySelector('[data-action="share"]');
    if (shareBtn) shareBtn.addEventListener('click', onShare);
    container.querySelectorAll('[data-nearby-code]').forEach((card) => {
        card.addEventListener('click', () => onNearbySelect(card.dataset.nearbyCode));
    });
}

function nearbyCardHtml(loc) {
    return `
        <button type="button" class="nearby-card" data-nearby-code="${loc.code}">
            <span class="loc-thumb loc-thumb-sm">${loc.photoUrl ? `<img src="${loc.photoUrl}" alt="">` : categoryIcon(loc.category)}</span>
            <span class="nearby-name">${escapeHtml(loc.name)}</span>
            <span class="nearby-distance">${formatDistance(loc.distanceM)}</span>
        </button>`;
}

export function renderRouteHeader(container, { originName, destinationName, distanceM, durationMin }, onExit) {
    container.innerHTML = `
        <div class="route-header">
            <button type="button" class="route-exit" aria-label="Exit directions">${icon('close')}</button>
            <div class="route-summary">
                <div class="route-endpoints">${escapeHtml(originName)} &rarr; ${escapeHtml(destinationName)}</div>
                <div class="route-stats">${formatDistance(distanceM)} &middot; ${durationMin} min walk</div>
            </div>
        </div>
        <div class="step-list" data-step-list></div>`;
    container.querySelector('.route-exit').addEventListener('click', onExit);
    return container.querySelector('[data-step-list]');
}

export function renderNoRoute(container, message, onExit) {
    container.innerHTML = `
        <div class="empty-state route-empty">
            <div class="empty-illustration">${icon('flag')}</div>
            <p>${escapeHtml(message || 'No walking path is mapped between these two points yet.')}</p>
            <button type="button" class="btn-secondary" data-action="exit">Back</button>
        </div>`;
    container.querySelector('[data-action="exit"]').addEventListener('click', onExit);
}

let toastTimer = null;
export function showToast(root, message, variant = 'default') {
    root.innerHTML = `<div class="toast toast-${variant}" role="status">${icon('check')}<span>${escapeHtml(message)}</span></div>`;
    root.classList.add('toast-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => root.classList.remove('toast-visible'), 4000);
}

function haversineApprox(a, b) {
    const R = 6371000;
    const dLat = ((b.lat - a.lat) * Math.PI) / 180;
    const dLng = ((b.lng - a.lng) * Math.PI) / 180;
    const s = Math.sin(dLat / 2) ** 2 + Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
}
