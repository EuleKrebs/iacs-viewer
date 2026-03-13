// ===== IACS Viewer - Main Application Logic =====

const API_BASE = '/api';

// ===== Crop Colors =====
const CROP_COLORS = {
    'Wheat':      '#f59e0b',
    'Barley':     '#d97706',
    'Maize':      '#eab308',
    'Rapeseed':   '#84cc16',
    'Potatoes':   '#a855f7',
    'Sugar beet': '#ec4899',
    'Grassland':  '#22c55e',
    'Vineyard':   '#8b5cf6',
    'Olive grove':'#14b8a6',
    'Fallow':     '#94a3b8',
};
const DEFAULT_COLOR = '#4f8ff7';
function getCropColor(name) { return CROP_COLORS[name] || DEFAULT_COLOR; }

// ===== Map Setup =====
const map = L.map('map', { center: [48.5, 10], zoom: 5, zoomControl: true });
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
}).addTo(map);

let featureLayer = null;
let selectedFeature = null;
let currentDataset = null;
let currentColumns = []; // track columns of current dataset for dynamic filters

// ===== Helpers =====
function showLoading() { document.getElementById('loading-indicator').classList.remove('hidden'); }
function hideLoading() { document.getElementById('loading-indicator').classList.add('hidden'); }

async function apiGet(path) {
    const r = await fetch(API_BASE + path);
    if (!r.ok) throw new Error(`API ${r.status}`);
    return r.json();
}

async function apiPost(path, body) {
    const r = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return r.json();
}

function formatBytes(bytes) {
    if (bytes >= 1024 ** 3) return (bytes / 1024 ** 3).toFixed(1) + ' GB';
    if (bytes >= 1024 ** 2) return (bytes / 1024 ** 2).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return bytes + ' B';
}

function formatSpeed(bps) {
    if (bps >= 1024 ** 2) return (bps / 1024 ** 2).toFixed(1) + ' MB/s';
    if (bps >= 1024) return (bps / 1024).toFixed(1) + ' KB/s';
    return bps + ' B/s';
}

// ===== Dataset Management =====
async function loadDatasets(selectName) {
    const select = document.getElementById('dataset-select');
    try {
        const datasets = await apiGet('/datasets?reload=1');
        select.innerHTML = '';
        if (datasets.length === 0) {
            select.innerHTML = '<option value="">No datasets – open Data Catalog to download</option>';
            return;
        }
        datasets.forEach(ds => {
            const opt = document.createElement('option');
            opt.value = ds.name;
            opt.textContent = `${ds.name} (${ds.size_mb} MB)`;
            select.appendChild(opt);
        });
        // Select specific dataset or first
        const target = selectName || datasets[0].name;
        select.value = target;
        if (select.value) selectDataset(select.value);
    } catch (e) {
        select.innerHTML = '<option value="">Error loading datasets</option>';
    }
}

async function selectDataset(filename) {
    currentDataset = filename;
    showLoading();
    try {
        const info = await apiGet(`/datasets/${encodeURIComponent(filename)}/info`);
        currentColumns = info.columns.map(c => c.name);
        showDatasetInfo(info);
        await populateFilters(filename);
        const b = info.bounds;
        if (b.minx != null && b.miny != null && b.maxx != null && b.maxy != null) {
            map.fitBounds([[b.miny, b.minx], [b.maxy, b.maxx]], { padding: [30, 30] });
        }
        await loadFeatures();
    } catch (e) {
        console.error('Error loading dataset:', e);
        document.getElementById('dataset-info').classList.remove('visible');
    } finally {
        hideLoading();
    }
}

function showDatasetInfo(info) {
    const box = document.getElementById('dataset-info');
    box.classList.add('visible');
    const crsLabel = info.crs ? `EPSG:${info.crs}` : 'EPSG:4326';
    box.innerHTML = `
        <div class="info-row"><span class="info-label">Features</span><span class="info-value">${info.feature_count.toLocaleString()}</span></div>
        <div class="info-row"><span class="info-label">Columns</span><span class="info-value">${info.columns.length}</span></div>
        <div class="info-row"><span class="info-label">Source CRS</span><span class="info-value">${crsLabel}</span></div>
        <div class="info-row"><span class="info-label">Format</span><span class="info-value">${currentDataset.split('.').pop().toUpperCase()}</span></div>
    `;
    document.getElementById('feature-count-badge').textContent = `${info.feature_count.toLocaleString()} features`;
}

// ===== Filters =====
// We try common IACS columns; skip ones that don't exist in the dataset
const FILTER_COLUMNS = ['nation', 'year', 'crop_name', 'EC_hcat_n'];

async function populateFilters(filename) {
    for (const col of FILTER_COLUMNS) {
        const sel = document.querySelector(`[data-filter="${col}"]`);
        if (!sel) continue;
        const row = sel.closest('.filter-row');

        // Hide filter if column doesn't exist in dataset
        if (!currentColumns.includes(col)) {
            if (row) row.style.display = 'none';
            sel.innerHTML = '<option value="">All</option>';
            continue;
        }
        if (row) row.style.display = '';

        try {
            const values = await apiGet(`/datasets/${encodeURIComponent(filename)}/values/${col}`);
            const first = sel.options[0];
            sel.innerHTML = '';
            sel.appendChild(first);
            values.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = v;
                sel.appendChild(opt);
            });
        } catch (e) {
            console.warn(`Filter ${col}:`, e);
        }
    }

    // Also handle organic filter visibility
    const organicRow = document.querySelector('[data-filter="organic"]')?.closest('.filter-row');
    if (organicRow) {
        organicRow.style.display = currentColumns.includes('organic') ? '' : 'none';
    }
}

function getActiveFilters() {
    const f = {};
    document.querySelectorAll('[data-filter]').forEach(el => {
        if (el.value && currentColumns.includes(el.dataset.filter)) {
            f[el.dataset.filter] = el.value;
        }
    });
    return f;
}

// ===== Feature Loading =====
async function loadFeatures() {
    if (!currentDataset) return;
    showLoading();
    try {
        const bounds = map.getBounds();
        const bbox = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(',');
        const filters = getActiveFilters();
        let fp = '';
        for (const [k, v] of Object.entries(filters)) fp += `&filter_${k}=${encodeURIComponent(v)}`;

        const geojson = await apiGet(`/datasets/${encodeURIComponent(currentDataset)}/features?bbox=${bbox}&limit=3000${fp}`);

        if (featureLayer) map.removeLayer(featureLayer);
        featureLayer = L.geoJSON(geojson, {
            style: f => {
                const cropCol = f.properties.crop_name || f.properties.EC_hcat_n || null;
                const color = getCropColor(cropCol);
                return {
                    color, weight: 1.5, opacity: 0.9,
                    fillColor: color, fillOpacity: 0.45,
                };
            },
            onEachFeature: (feature, layer) => {
                layer.on('click', () => showFeatureDetail(feature, layer));
                layer.on('mouseover', () => layer.setStyle({ weight: 3, fillOpacity: 0.7 }));
                layer.on('mouseout', () => { if (selectedFeature !== layer) featureLayer.resetStyle(layer); });
            }
        }).addTo(map);

        document.getElementById('feature-count-badge').textContent = `${geojson.features.length.toLocaleString()} shown`;
        updateLegend(geojson);
    } catch (e) {
        console.error('Error loading features:', e);
    } finally {
        hideLoading();
    }
}

// ===== Feature Detail =====
function showFeatureDetail(feature, layer) {
    if (selectedFeature && featureLayer) featureLayer.resetStyle(selectedFeature);
    selectedFeature = layer;
    layer.setStyle({ weight: 3, color: '#ffffff', fillOpacity: 0.8 });

    const props = feature.properties;
    // Preferred display order (show what exists)
    const preferredOrder = ['field_id','farm_id','crop_name','crop_code','EC_trans_n','EC_hcat_n','EC_hcat_c','field_size','crop_area','organic','nation','year'];
    let rows = '';
    const shown = new Set();
    for (const k of preferredOrder) {
        if (k in props) { rows += fmtRow(k, props[k]); shown.add(k); }
    }
    for (const [k, v] of Object.entries(props)) {
        if (!shown.has(k)) rows += fmtRow(k, v);
    }
    document.getElementById('feature-detail').innerHTML = `<table class="detail-table">${rows}</table>`;
}

function fmtRow(key, value) {
    let v = value;
    if (key === 'organic') {
        v = (value === true || value === 'true' || value === 'True')
            ? '<span class="tag tag-organic">✓ Organic</span>'
            : '<span class="tag tag-conventional">Conventional</span>';
    } else if ((key === 'field_size' || key === 'crop_area') && value != null && !isNaN(value)) {
        v = `${parseFloat(value).toFixed(2)} ha`;
    } else if (value == null) {
        v = '<span style="color:var(--text-muted)">–</span>';
    }
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    return `<tr><td class="detail-key">${label}</td><td class="detail-value">${v}</td></tr>`;
}

// ===== Legend =====
function updateLegend(geojson) {
    const crops = new Set();
    geojson.features.forEach(f => {
        const name = f.properties.crop_name || f.properties.EC_hcat_n;
        if (name) crops.add(name);
    });
    const c = document.getElementById('legend-content');
    c.innerHTML = '';
    [...crops].sort().forEach(crop => {
        const d = document.createElement('div');
        d.className = 'legend-item';
        d.innerHTML = `<span class="legend-color" style="background:${getCropColor(crop)}"></span>${crop}`;
        c.appendChild(d);
    });
}

// ===== Data Catalog =====
let catalogData = null;
let sseSource = null;

function openCatalog() {
    document.getElementById('catalog-modal').classList.remove('hidden');
    fetchCatalog();
}

function closeCatalog() {
    document.getElementById('catalog-modal').classList.add('hidden');
}

async function fetchCatalog() {
    const list = document.getElementById('catalog-list');
    list.innerHTML = '<div class="catalog-loading"><div class="spinner"></div><span>Fetching catalog from Zenodo...</span></div>';
    try {
        catalogData = await apiGet('/populate/catalog');
        renderCatalog();
    } catch (e) {
        list.innerHTML = `<div class="catalog-loading"><span style="color:var(--danger)">Failed to load catalog: ${e.message}</span></div>`;
    }
}

function renderCatalog(searchTerm = '') {
    const list = document.getElementById('catalog-list');
    const summary = document.getElementById('catalog-summary');
    if (!catalogData) return;

    const files = searchTerm
        ? catalogData.files.filter(f => f.name.toLowerCase().includes(searchTerm.toLowerCase()))
        : catalogData.files;

    const readyCount = catalogData.files.filter(f => f.status === 'extracted').length;
    summary.innerHTML = `
        <span class="stat"><span class="stat-value">${catalogData.files.length}</span><span class="stat-label">datasets</span></span>
        <span class="stat"><span class="stat-value">${catalogData.total_size_gb} GB</span><span class="stat-label">total</span></span>
        <span class="stat"><span class="stat-value">${readyCount}</span><span class="stat-label">ready</span></span>
    `;

    list.innerHTML = '';
    if (files.length === 0) {
        list.innerHTML = '<div class="catalog-loading"><span>No matching datasets</span></div>';
        return;
    }
    for (const file of files) list.appendChild(createCatalogItem(file));
}

function createCatalogItem(file) {
    const div = document.createElement('div');
    div.className = 'catalog-item';
    div.dataset.name = file.name;

    const icons = {
        available: '📦', downloaded: '💾', extracted: '✅',
        downloading: '⬇️', extracting: '📂', error: '❌', cancelled: '⛔',
    };

    let actions = '';
    if (file.status === 'available' || file.status === 'error' || file.status === 'cancelled') {
        actions = `<button class="btn btn-primary btn-sm" onclick="startDownload('${file.name}', '${file.url}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>Download</button>`;
    } else if (file.status === 'downloaded') {
        actions = `<button class="btn btn-primary btn-sm" onclick="extractZip('${file.name}')">📂 Extract</button>`;
    } else if (file.status === 'downloading') {
        actions = `<button class="btn btn-danger btn-sm" onclick="cancelDownload('${file.name}')">Cancel</button>`;
    } else if (file.status === 'extracted') {
        actions = `<span style="color:var(--success);font-size:11px;font-weight:500;">✓ Ready</span>`;
    }

    let progressHtml = '';
    if (file.status === 'downloading' || file.status === 'extracting') {
        const cls = file.status === 'extracting' ? 'extracting' : '';
        progressHtml = `
            <div style="width:100%;margin-top:6px;">
                <div class="progress-bar-wrap"><div class="progress-bar-fill ${cls}" style="width:${file.progress}%"></div></div>
                <div class="progress-text">${file.status === 'extracting' ? 'Extracting...' : file.progress + '%'}</div>
            </div>`;
    }

    div.innerHTML = `
        <div class="catalog-item-icon ${file.status}">${icons[file.status] || '📦'}</div>
        <div class="catalog-item-info">
            <div class="catalog-item-name" title="${file.name}">${file.name}</div>
            <div class="catalog-item-meta">
                <span>${formatBytes(file.size_bytes)}</span>
                <span class="status-badge ${file.status}">${file.status}</span>
            </div>
            ${progressHtml}
        </div>
        <div class="catalog-item-actions">${actions}</div>
    `;
    return div;
}

async function startDownload(name, url) {
    try {
        await apiPost('/populate/download', { name, url });
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) { f.status = 'downloading'; f.progress = 0; }
            renderCatalog(document.getElementById('catalog-search').value);
        }
        addDownloadToast(name);
        startProgressPolling();
        document.getElementById('download-indicator').classList.remove('hidden');
    } catch (e) {
        console.error('Download start failed:', e);
    }
}

async function extractZip(name) {
    try {
        await apiPost('/populate/extract', { name });
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) { f.status = 'extracting'; f.progress = 100; }
            renderCatalog(document.getElementById('catalog-search').value);
        }
        addDownloadToast(name, 'extracting');
        startProgressPolling();
        document.getElementById('download-indicator').classList.remove('hidden');
    } catch (e) {
        console.error('Extract failed:', e);
    }
}

async function cancelDownload(name) {
    try {
        await apiPost(`/populate/download/${name}/cancel`, {});
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) { f.status = 'cancelled'; f.progress = 0; }
            renderCatalog(document.getElementById('catalog-search').value);
        }
        removeDownloadToast(name);
    } catch (e) {
        console.error('Cancel failed:', e);
    }
}

// ===== Progress Polling via SSE =====
function startProgressPolling() {
    if (sseSource) return;
    sseSource = new EventSource(API_BASE + '/populate/downloads/events');
    sseSource.onmessage = (event) => {
        const downloads = JSON.parse(event.data);
        updateDownloadProgress(downloads);
    };
    sseSource.onerror = () => {
        sseSource.close();
        sseSource = null;
        checkDownloadsComplete();
    };
}

function updateDownloadProgress(downloads) {
    let anyActive = false;

    for (const [name, info] of Object.entries(downloads)) {
        updateToast(name, info);
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) { f.status = info.status; f.progress = info.progress; }
        }
        if (info.status === 'downloading' || info.status === 'extracting') anyActive = true;
    }

    if (!document.getElementById('catalog-modal').classList.contains('hidden')) {
        renderCatalog(document.getElementById('catalog-search').value);
    }

    if (!anyActive) {
        if (sseSource) { sseSource.close(); sseSource = null; }
        document.getElementById('download-indicator').classList.add('hidden');
        // Reload dataset list to pick up newly extracted files
        loadDatasets(currentDataset);
    }
}

async function checkDownloadsComplete() {
    try {
        const status = await apiGet('/populate/downloads/status');
        const anyActive = Object.values(status).some(d =>
            d.status === 'downloading' || d.status === 'extracting'
        );
        if (anyActive) {
            startProgressPolling();
        } else {
            document.getElementById('download-indicator').classList.add('hidden');
        }
    } catch (e) {}
}

// ===== Download Toasts =====
function addDownloadToast(name, initialStatus = 'downloading') {
    const container = document.getElementById('download-toasts');
    if (document.getElementById(`toast-${CSS.escape(name)}`)) return;

    const toast = document.createElement('div');
    toast.className = 'download-toast';
    toast.id = `toast-${name}`;

    const iconHtml = initialStatus === 'extracting'
        ? '📂'
        : '<div class="mini-spinner"></div>';

    toast.innerHTML = `
        <div class="toast-icon">${iconHtml}</div>
        <div class="toast-body">
            <div class="toast-name" title="${name}">${name}</div>
            <div class="toast-progress-wrap"><div class="toast-progress-fill" style="width:0%"></div></div>
            <div class="toast-status">${initialStatus === 'extracting' ? 'Extracting...' : 'Starting download...'}</div>
        </div>
        <button class="toast-close" onclick="removeDownloadToast('${name}')">&times;</button>
    `;
    container.appendChild(toast);
}

function updateToast(name, info) {
    const toast = document.getElementById(`toast-${name}`);
    if (!toast) {
        if (info.status === 'downloading' || info.status === 'extracting') addDownloadToast(name, info.status);
        return;
    }

    const fill = toast.querySelector('.toast-progress-fill');
    const status = toast.querySelector('.toast-status');
    const icon = toast.querySelector('.toast-icon');

    fill.style.width = `${info.progress}%`;

    if (info.status === 'downloading') {
        fill.className = 'toast-progress-fill';
        const dl = formatBytes(info.downloaded_bytes || 0);
        const total = formatBytes(info.total_bytes || 0);
        const speed = info.speed_bps ? formatSpeed(info.speed_bps) : '';
        status.textContent = `${dl} / ${total}${speed ? ' • ' + speed : ''} • ${info.progress}%`;
    } else if (info.status === 'extracting') {
        fill.className = 'toast-progress-fill extracting';
        fill.style.width = '100%';
        status.textContent = 'Extracting files...';
        icon.innerHTML = '📂';
    } else if (info.status === 'extracted') {
        fill.style.width = '100%';
        fill.className = 'toast-progress-fill';
        fill.style.background = 'var(--success)';
        status.textContent = 'Complete! Ready to explore.';
        icon.innerHTML = '✅';
        toast.classList.add('success');
        setTimeout(() => removeDownloadToast(name), 5000);
    } else if (info.status === 'error') {
        fill.style.background = 'var(--danger)';
        status.textContent = `Error: ${info.error || 'Unknown'}`;
        icon.innerHTML = '❌';
        toast.classList.add('error');
    } else if (info.status === 'cancelled') {
        status.textContent = 'Cancelled';
        icon.innerHTML = '⛔';
        setTimeout(() => removeDownloadToast(name), 3000);
    }
}

function removeDownloadToast(name) {
    const t = document.getElementById(`toast-${name}`);
    if (t) t.remove();
}

// ===== Event Listeners =====
document.getElementById('dataset-select').addEventListener('change', (e) => {
    if (e.target.value) selectDataset(e.target.value);
});

document.getElementById('apply-filters').addEventListener('click', () => loadFeatures());
document.getElementById('clear-filters').addEventListener('click', () => {
    document.querySelectorAll('[data-filter]').forEach(el => el.value = '');
    loadFeatures();
});

document.getElementById('catalog-toggle').addEventListener('click', openCatalog);
document.getElementById('catalog-close').addEventListener('click', closeCatalog);
document.querySelector('.modal-backdrop').addEventListener('click', closeCatalog);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeCatalog(); });

document.getElementById('catalog-search').addEventListener('input', (e) => {
    renderCatalog(e.target.value);
});

let moveTimeout;
map.on('moveend', () => {
    clearTimeout(moveTimeout);
    moveTimeout = setTimeout(() => { if (currentDataset) loadFeatures(); }, 300);
});

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    loadDatasets();
    checkDownloadsComplete();
});
