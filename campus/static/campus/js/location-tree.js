// location-tree.js - Landing-page node tree (campus/tree.html): campus
// locations grouped by category. Clicking a category branch expands/
// collapses its children; clicking a location node sends the user to the
// map page centered on that node (see the ?location=<id> handler in
// home.html, which map.js/navigation.js pick up once locations load).
//
// Also powers the search box at the top of the page: it filters this
// same tree (matching name, category, AND description - which is where
// a building's room numbers live, e.g. "Classroom 202") instead of
// showing a separate results dropdown like the map page's search does.

(function () {
    const treeEl = document.getElementById('locationTree');
    if (!treeEl) return;

    const searchBox = document.getElementById('treeSearchBox');
    const mapUrl = treeEl.dataset.mapUrl || '/map/';

    let allLocations = [];

    // Small stroke-icon set matching the rest of the app's SVG style
    // (see base.html / home.html inline icons) - one per seeded category,
    // with a generic pin as the fallback for anything else an admin adds.
    const CATEGORY_ICONS = {
        Academic: '<path d="M4 6.5C4 5.7 4.6 5 5.5 5H12v14H5.5A1.5 1.5 0 0 1 4 17.5v-11z"></path><path d="M20 6.5c0-.8-.6-1.5-1.5-1.5H12v14h6.5c.8 0 1.5-.7 1.5-1.5v-11z"></path>',
        Food: '<path d="M6 3v7a3 3 0 0 0 3 3v8"></path><path d="M6 3v6"></path><path d="M9 3v6"></path><path d="M18 3c-1.7 0-3 2-3 5s1.3 5 3 5v8"></path>',
        Admin: '<rect x="3" y="7.5" width="18" height="12" rx="1.5"></rect><path d="M8 7.5V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1.5"></path>',
        Facility: '<path d="M4 21V9l8-5 8 5v12"></path><path d="M9 21v-6h6v6"></path>',
        Entrance: '<path d="M5 21V4.6A1.6 1.6 0 0 1 6.6 3h8.8A1.6 1.6 0 0 1 17 4.6V21"></path><path d="M19 21H3"></path><path d="M12.5 12v.01"></path>'
    };
    const DEFAULT_ICON = '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"></path><circle cx="12" cy="10" r="2.4"></circle>';

    function iconSvg(markup, extraClass) {
        return `<svg class="${extraClass}" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${markup}</svg>`;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str ?? '';
        return div.innerHTML;
    }

    function escapeRegExp(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Escapes text for HTML first, then wraps whatever matches `query`
    // in <mark> - so a search for "202" highlights it inside "Classroom
    // 202" wherever it shows up (name, category, or description preview).
    function highlight(text, query) {
        const safe = escapeHtml(text);
        if (!query) return safe;
        const re = new RegExp('(' + escapeRegExp(escapeHtml(query)) + ')', 'ig');
        return safe.replace(re, '<mark>$1</mark>');
    }

    function matchesQuery(loc, query) {
        const q = query.toLowerCase();
        return (loc.name || '').toLowerCase().includes(q)
            || (loc.category || '').toLowerCase().includes(q)
            || (loc.description || '').toLowerCase().includes(q);
    }

    function groupByCategory(locations) {
        const groups = new Map();
        locations.forEach((loc) => {
            const key = loc.category || 'General';
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(loc);
        });
        return groups;
    }

    function buildNode(loc, query) {
        const node = document.createElement('button');
        node.type = 'button';
        node.className = 'tree-node';

        const preview = (loc.description || '').replace(/\s+/g, ' ').trim();
        const shortPreview = preview.length > 90 ? preview.slice(0, 90) + '...' : preview;

        node.innerHTML = `
            <span class="tree-node-dot" aria-hidden="true"></span>
            <span class="tree-node-body">
                <span class="tree-node-name">${highlight(loc.name, query)}</span>
                ${preview ? `<span class="tree-node-desc">${highlight(shortPreview, query)}</span>` : ''}
            </span>
            <svg class="tree-node-arrow" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="9,6 15,12 9,18"></polyline>
            </svg>
        `;

        // Click any node -> jump into the map, centered + selected as
        // destination. See home.html's ?location=<id> handler.
        node.addEventListener('click', () => {
            window.location.href = mapUrl + '?location=' + loc.id;
        });

        return node;
    }

    function buildBranch(category, locations, isOpen, query) {
        const branch = document.createElement('div');
        branch.className = 'tree-branch' + (isOpen ? ' is-open' : '');

        const header = document.createElement('button');
        header.type = 'button';
        header.className = 'tree-branch-header';
        header.setAttribute('aria-expanded', String(isOpen));
        header.innerHTML = `
            ${iconSvg(CATEGORY_ICONS[category] || DEFAULT_ICON, 'tree-branch-icon')}
            <span class="tree-branch-name">${highlight(category, query)}</span>
            <span class="tree-branch-count">${locations.length}</span>
            <svg class="tree-branch-chevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="6,9 12,15 18,9"></polyline>
            </svg>
        `;
        header.addEventListener('click', () => {
            const nowOpen = branch.classList.toggle('is-open');
            header.setAttribute('aria-expanded', String(nowOpen));
        });

        const children = document.createElement('div');
        children.className = 'tree-branch-children';

        // A single inner wrapper (not the location buttons directly) is
        // required for the CSS grid-rows collapse animation to clip the
        // whole group together - see .tree-branch-children in site.css.
        const inner = document.createElement('div');
        inner.className = 'tree-branch-inner';
        locations.forEach((loc) => inner.appendChild(buildNode(loc, query)));
        children.appendChild(inner);

        branch.appendChild(header);
        branch.appendChild(children);
        return branch;
    }

    function renderTree(locations, query) {
        if (!allLocations.length) {
            treeEl.innerHTML = '<div class="tree-empty">No locations have been added yet - add some from the admin panel.</div>';
            return;
        }

        const visible = query ? locations.filter((loc) => matchesQuery(loc, query)) : locations;

        if (!visible.length) {
            treeEl.innerHTML = `<div class="tree-empty">No place matches "${escapeHtml(query)}" - try a different name or room number.</div>`;
            return;
        }

        const groups = groupByCategory(visible);
        treeEl.innerHTML = '';

        // While actively searching, expand every branch that has a match
        // so results are visible right away - otherwise only the first
        // category opens by default (the plain-browsing behaviour).
        let isFirst = true;
        groups.forEach((locs, category) => {
            const isOpen = query ? true : isFirst;
            treeEl.appendChild(buildBranch(category, locs, isOpen, query));
            isFirst = false;
        });
    }

    async function loadTree() {
        try {
            const res = await fetch('/api/locations');
            if (!res.ok) throw new Error('Request failed: ' + res.status);
            allLocations = await res.json();
            renderTree(allLocations, '');
        } catch (err) {
            treeEl.innerHTML = '<div class="tree-empty">Could not load locations. Please refresh the page.</div>';
            console.error(err);
        }
    }

    if (searchBox) {
        let debounceTimer = null;
        searchBox.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const query = searchBox.value.trim();
            debounceTimer = setTimeout(() => renderTree(allLocations, query), 150);
        });
    }

    loadTree();
})();
