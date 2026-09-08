// scan-page.js - bootstrap for /app/scan/ (campus/templates/campus/app/scan.html).
// Wires the Scanner class (scanner.js) to the page's overlay/fallback UI.

import { Scanner, parseScannedPayload } from './scanner.js';
import { api } from './api.js';
import { icon } from './icons.js';
import { setActiveCampus } from './store.js';

const el = {
    reader: document.getElementById('scanReader'),
    backBtn: document.getElementById('scanBackBtn'),
    torchBtn: document.getElementById('scanTorchBtn'),
    help: document.getElementById('scanHelp'),
    success: document.getElementById('scanSuccess'),
    fallback: document.getElementById('scanFallback'),
    manualForm: document.getElementById('manualEntryForm'),
    manualInput: document.getElementById('manualEntryInput'),
    manualLink: document.getElementById('manualEntryLink'),
    overlay: document.querySelector('.scan-overlay'),
};

document.querySelectorAll('[data-icon]').forEach((node) => { node.innerHTML = icon(node.dataset.icon); });

el.backBtn.addEventListener('click', () => { window.location.href = '/app/'; });
el.manualLink.addEventListener('click', (e) => { e.preventDefault(); showFallback(); });

const scanner = new Scanner('scanReader', {
    onDecode: handleDecode,
    onError: (code) => {
        if (code === 'camera_denied' || code === 'library_missing') showFallback();
    },
});

scanner.start().then((started) => {
    if (started && el.torchBtn) {
        el.torchBtn.hidden = false;
        el.torchBtn.addEventListener('click', async () => {
            const on = await scanner.toggleTorch();
            el.torchBtn.classList.toggle('fab-active', on);
        });
    }
});

let handled = false;
async function handleDecode(raw) {
    if (handled) return;
    handled = true;
    await scanner.stop();
    showSuccess();

    const payload = parseScannedPayload(raw);

    // A campus QR (see Admin -> Campuses -> QR preview) just picks which
    // campus to load - no ScanEvent/Location involved, so it skips
    // straight to the redirect.
    if (payload.type === 'campus') {
        setActiveCampus(payload.slug);
        setTimeout(() => {
            window.location.href = `/app/?campus=${encodeURIComponent(payload.slug)}`;
        }, 700);
        return;
    }

    const code = payload.code;
    try {
        await api.scan(code);
    } catch (err) {
        /* still navigate - the landing page will show "not recognized" itself */
    }
    setTimeout(() => {
        window.location.href = `/app/?at=${encodeURIComponent(code)}`;
    }, 700);
}

function showSuccess() {
    el.overlay.hidden = true;
    el.help.hidden = true;
    el.success.hidden = false;
}

function showFallback() {
    scanner.stop();
    el.overlay.hidden = true;
    el.help.hidden = true;
    el.fallback.hidden = false;
    el.manualInput.focus();
}

el.manualForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const raw = el.manualInput.value.trim();
    if (!raw) return;
    handleDecode(raw);
});
