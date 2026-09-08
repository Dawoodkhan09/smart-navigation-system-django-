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
        // Accept a bare code or a full /l/<code>/ URL - use the last
        // non-empty path segment either way.
        const code = extractCode(decodedText);
        if (navigator.vibrate) navigator.vibrate(60);
        this.onDecode && this.onDecode(code, decodedText);
    }
}

export function extractCode(raw) {
    const trimmed = (raw || '').trim();
    if (!trimmed) return '';
    const withoutTrailingSlash = trimmed.replace(/\/+$/, '');
    const segments = withoutTrailingSlash.split('/');
    return segments[segments.length - 1];
}
