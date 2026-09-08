// sheet.js - the draggable bottom sheet. Three snap points (peek/half/
// full), dragged via pointer events on the handle/header, positioned
// with `transform: translateY()` only (never animate `height` - that's
// what jank comes from). Velocity-based snapping: a fast enough flick
// jumps to the next snap point in that direction even if released
// halfway there.

const SNAP_FRACTIONS = { peek: 0.14, half: 0.5, full: 0.92 };
const SNAP_ORDER = ['peek', 'half', 'full'];
const FLING_VELOCITY_PX_PER_MS = 0.5;
const TRANSITION = 'transform 240ms cubic-bezier(.22,.61,.36,1)';

export class BottomSheet {
    constructor(element, { initial = 'half' } = {}) {
        this.el = element;
        this.current = initial;
        this._dragging = false;
        this._startClientY = 0;
        this._startTranslate = 0;
        this._lastClientY = 0;
        this._lastTime = 0;
        this._velocity = 0;
        this.onSnapChange = null;

        this.el.style.willChange = 'transform';
        this._bindDrag();
        window.addEventListener('resize', () => this.snapTo(this.current, false));

        // Layout needs one frame before innerHeight-based math is correct
        // on some mobile browsers (address-bar collapse on first paint).
        requestAnimationFrame(() => this.snapTo(initial, false));
    }

    snapTo(name, animate = true) {
        if (!(name in SNAP_FRACTIONS)) name = 'half';
        this.current = name;
        this.el.style.transition = animate ? TRANSITION : 'none';
        this.el.style.transform = `translateY(${this._translateForFraction(SNAP_FRACTIONS[name])}px)`;
        this.el.setAttribute('data-snap', name);
        this.el.setAttribute('aria-hidden', name === 'peek' ? 'false' : 'false');
        if (this.onSnapChange) this.onSnapChange(name);
    }

    isAtLeast(name) {
        return SNAP_ORDER.indexOf(this.current) >= SNAP_ORDER.indexOf(name);
    }

    _translateForFraction(visibleFraction) {
        const vh = window.innerHeight;
        return Math.max(0, vh - vh * visibleFraction);
    }

    _currentTranslateY() {
        const style = window.getComputedStyle(this.el);
        const matrix = new DOMMatrixReadOnly(style.transform);
        return matrix.m42; // translateY component
    }

    _bindDrag() {
        const dragTargets = this.el.querySelectorAll('[data-sheet-drag]');
        const targets = dragTargets.length ? Array.from(dragTargets) : [this.el];

        targets.forEach((target) => {
            target.addEventListener('pointerdown', (e) => this._onPointerDown(e));
        });
        window.addEventListener('pointermove', (e) => this._onPointerMove(e), { passive: true });
        window.addEventListener('pointerup', (e) => this._onPointerUp(e));
        window.addEventListener('pointercancel', (e) => this._onPointerUp(e));
    }

    _onPointerDown(e) {
        this._dragging = true;
        this._startClientY = e.clientY;
        this._startTranslate = this._currentTranslateY();
        this._lastClientY = e.clientY;
        this._lastTime = performance.now();
        this._velocity = 0;
        this.el.style.transition = 'none';
    }

    _onPointerMove(e) {
        if (!this._dragging) return;

        const now = performance.now();
        const dt = now - this._lastTime || 1;
        this._velocity = (e.clientY - this._lastClientY) / dt;
        this._lastClientY = e.clientY;
        this._lastTime = now;

        const delta = e.clientY - this._startClientY;
        const next = Math.max(0, this._startTranslate + delta);
        this.el.style.transform = `translateY(${next}px)`;
    }

    _onPointerUp() {
        if (!this._dragging) return;
        this._dragging = false;
        this.el.style.transition = TRANSITION;

        const currentTranslate = this._currentTranslateY();
        const vh = window.innerHeight;
        const visibleFraction = 1 - currentTranslate / vh;

        // A fast flick snaps one step in that direction regardless of
        // how far it actually travelled; otherwise snap to the nearest
        // point by distance.
        if (Math.abs(this._velocity) > FLING_VELOCITY_PX_PER_MS) {
            const direction = this._velocity < 0 ? 1 : -1; // moving up = next bigger snap
            const idx = SNAP_ORDER.indexOf(this.current);
            const nextIdx = Math.min(Math.max(idx + direction, 0), SNAP_ORDER.length - 1);
            this.snapTo(SNAP_ORDER[nextIdx]);
            return;
        }

        let closest = SNAP_ORDER[0];
        let closestDelta = Infinity;
        for (const name of SNAP_ORDER) {
            const d = Math.abs(SNAP_FRACTIONS[name] - visibleFraction);
            if (d < closestDelta) {
                closestDelta = d;
                closest = name;
            }
        }
        this.snapTo(closest);
    }
}
