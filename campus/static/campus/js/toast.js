// toast.js - shared Bootstrap toast notification helper. Used by both
// geofence.js (per-location enter/exit) and boundary.js (whole-campus
// enter/exit) so both use the same notification style.
// Requires a <div id="toastContainer"> on the page (see home/index.blade.php).

window.showToast = function (message, variant) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${variant || 'primary'} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    container.appendChild(toastEl);

    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
};
