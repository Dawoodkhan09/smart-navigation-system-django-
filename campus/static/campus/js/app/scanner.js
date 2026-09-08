// scanner.js - in-app camera QR scanner for /app/scan/. Uses the
// low-level Html5Qrcode class (not Html5QrcodeScanner) so we can draw
// our own frame/overlay instead of the library's default UI - see
// campus/templates/campus/app/scan.html for the markup this drives.
// html5-qrcode itself is loaded from the CDN in base_app.html.

export class Scanner {
    constructor(elementId, { onDecode, onError } = {}) {
        this.elementId = elementId;
        this.onDecode = onDecode;
        this.onError = onError;
        this.html5Qrcode = null;
        this.running = false;
        this.torchOn = false;
    }

    async start() {
        if (typeof Html5Qrcode === 'undefined') {
            this.onError && this.onError('library_missing', 'Scanner library did not load (check your connection).');
            return false;
        }

        this.html5Qrcode = new Html5Qrcode(this.elementId, { verbose: false });

        try {
            await this.html5Qrcode.start(
                { facingMode: 'environment' },
                { fps: 10, qrbox: { width: 240, height: 240 } },
                (decodedText) => this._handleDecode(decodedText),
                () => { /* per-frame "not found yet" noise - ignored */ },
            );
            this.running = true;
            return true;
        } catch (err) {
            this.onError && this.onError('camera_denied', 'Camera access was denied or is unavailable.');
            return false;
        }
    }

    async stop() {
        if (!this.running || !this.html5Qrcode) return;
        try {
            await this.html5Qrcode.stop();
            this.html5Qrcode.clear();
        } catch (err) {
            /* already stopped */
        }
        this.running = false;
    }

    async toggleTorch() {
        if (!this.html5Qrcode) return false;
        try {
            const track = this.html5Qrcode.getRunningTrackCameraCapabilities ? null : null;
            // html5-qrcode exposes torch via applyVideoConstraints in v2.3.
            this.torchOn = !this.torchOn;
            await this.html5Qrcode.applyVideoConstraints({
                advanced: [{ torch: this.torchOn }],
            });
            return this.torchOn;
        } catch (err) {
            this.torchOn = false;
            return false;
        }
    }

    isTorchSupported() {
        try {
            const capabilities = this.html5Qrcode && this.html5Qrcode.getRunningTrackCapabilities
                ? this.html5Qrcode.getRunningTrackCapabilities()
                : null;
            return !!(capabilities && capabilities.torch);
        } catch (err) {
            return false;
        }
    }

    _handleDecode(decodedText) {
        if (navigator.vibrate) navigator.vibrate(60);
        // Raw decoded text goes straight to the caller - parseScannedPayload
        // below is what tells a campus QR apart from a location QR, so the
        // page decides what to do with it rather than this class guessing.
        this.onDecode && this.onDecode(decodedText);
    }
}

/**
 * A scanned campus QR (/c/<slug>/app/) and a scanned location QR
 * (/l/<code>/) look enough alike (both are just URLs) that whoever
 * handles the decode needs to tell them apart before deciding what to
 * do. Also accepts a bare code (manual entry, or an unrecognised URL
 * shape) by falling back to its last path segment.
 */
export function parseScannedPayload(raw) {
    const trimmed = (raw || '').trim();
    if (!trimmed) return { type: 'unknown', raw: '' };

    let path = trimmed;
    try {
        path = new URL(trimmed).pathname;
    } catch (err) {
        // Not a full URL (e.g. manual entry of a bare code) - treat the
        // whole string as a path with one segment.
    }

    const segments = path.replace(/\/+$/, '').split('/').filter(Boolean);

    if (segments.length === 3 && segments[0] === 'c' && segments[2] === 'app') {
        return { type: 'campus', slug: segments[1] };
    }
    if (segments.length === 2 && segments[0] === 'l') {
        return { type: 'location', code: segments[1] };
    }
    return { type: 'location', code: segments[segments.length - 1] || trimmed };
}

/** @deprecated kept for callers that only need the old "just give me a
 * code" behaviour - prefer parseScannedPayload for anything that also
 * needs to recognise a campus QR. */
export function extractCode(raw) {
    const payload = parseScannedPayload(raw);
    return payload.type === 'campus' ? payload.slug : payload.code || '';
}
