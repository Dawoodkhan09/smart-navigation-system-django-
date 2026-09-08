// tour.js - guided-tour mode state + rendering. app.js owns wiring this
// into the map/sheet; this module just knows how to fetch a tour and
// keep track of which stop the visitor is on.

import { api } from './api.js';

export class TourState {
    constructor(tour) {
        this.tour = tour;
        this.index = 0; // current stop index, 0-based
        this.started = false;
    }

    get stop() {
        return this.tour.stops[this.index];
    }

    get nextStop() {
        return this.tour.stops[this.index + 1] || null;
    }

    get isLastStop() {
        return this.index === this.tour.stops.length - 1;
    }

    start() {
        this.started = true;
        this.index = 0;
    }

    goNext() {
        if (!this.isLastStop) this.index += 1;
        return this.stop;
    }

    goPrevious() {
        if (this.index > 0) this.index -= 1;
        return this.stop;
    }
}

export async function loadTour(slug) {
    return api.tour(slug);
}

export function renderCoverCard(tour) {
    return `
        <div class="tour-cover">
            ${tour.coverImageUrl ? `<img class="tour-cover-image" src="${tour.coverImageUrl}" alt="">` : ''}
            <h2 class="tour-title">${escapeHtml(tour.title)}</h2>
            <p class="tour-summary">${escapeHtml(tour.summary)}</p>
            <div class="tour-meta">
                <span>${tour.durationMinutes} min</span>
                <span>&middot;</span>
                <span>${tour.stopCount} stops</span>
            </div>
            <button type="button" class="btn-primary" data-action="start-tour">Start tour</button>
        </div>`;
}

export function renderProgressBar(container, total, currentIndex) {
    container.innerHTML = '';
    for (let i = 0; i < total; i += 1) {
        const seg = document.createElement('span');
        seg.className = 'tour-progress-seg' + (i <= currentIndex ? ' done' : '');
        container.appendChild(seg);
    }
}

export function renderStopCard(tourState) {
    const { tour, index, stop, isLastStop } = tourState;
    const loc = stop.location;

    return `
        <div class="tour-stop">
            <div class="tour-stop-label">Stop ${index + 1} of ${tour.stops.length}</div>
            ${loc.photoUrl ? `<img class="place-hero" src="${loc.photoUrl}" alt="">` : ''}
            <h2 class="place-name">${escapeHtml(loc.name)}</h2>
            <p class="place-short">${escapeHtml(loc.shortDescription || '')}</p>
            ${stop.note ? `<p class="tour-note">${escapeHtml(stop.note)}</p>` : ''}
            <div class="tour-nav">
                <button type="button" class="btn-secondary" data-action="tour-prev" ${index === 0 ? 'disabled' : ''}>Previous</button>
                <button type="button" class="btn-primary" data-action="${isLastStop ? 'tour-done' : 'tour-next'}">${isLastStop ? 'Done' : 'Next stop'}</button>
            </div>
        </div>`;
}

export function renderCelebration(tour) {
    return `
        <div class="tour-celebration">
            <div class="celebration-badge">🎉</div>
            <h2>Tour complete!</h2>
            <p>You've finished "${escapeHtml(tour.title)}".</p>
            <button type="button" class="btn-primary" data-action="tour-exit">Done</button>
        </div>`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
}
