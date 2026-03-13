// ===== IACS Viewer - Main Application Logic =====

const API_BASE = '/api';

// ===== Color Palette for EC_hcat_n categories (from IACS documentation) =====
// Grouped by land-use type with visually distinct colors
const CATEGORY_COLORS = {
    // Cereals — warm yellows/oranges
    'common_soft_wheat':              '#f59e0b',
    'spring_common_soft_wheat':       '#f5a623',
    'winter_common_soft_wheat':       '#e8960a',
    'durum_hard_wheat':               '#d97706',
    'spring_durum_hard_wheat':        '#d4790b',
    'winter_durum_hard_wheat':        '#c26b05',
    'barley':                         '#fbbf24',
    'spring_barley':                  '#fbc73e',
    'winter_barley':                  '#e5a910',
    'rye':                            '#f0a020',
    'spring_rye':                     '#eda21e',
    'winter_rye':                     '#d49018',
    'grain_maize_corn_popcorn':       '#eab308',
    'green_silo_maize':               '#c9a00a',
    'cereal':                         '#fb923c',
    'spring_oats':                    '#e8b84d',
    'winter_oats':                    '#d4a642',
    'spring_triticale':               '#dba030',
    'winter_triticale':               '#c89028',
    'millet_sorghum':                 '#cc8822',
    'rice':                           '#f0d060',
    'buckwheat':                      '#bba030',
    'spring_spelt':                   '#d0a838',
    'winter_spelt':                   '#c09830',
    'spring_emmer':                   '#c8a044',
    'winter_emmer':                   '#b89038',
    'spring_meslin':                  '#ccaa40',
    'winter_meslin':                  '#bb9a38',
    'canary_seed_canaryseed':         '#ddb840',

    // Oilseeds — yellow-greens
    'sunflower':                      '#84cc16',
    'winter_rapeseed_rape':           '#a3e635',
    'summer_rapeseed_rape':           '#bef264',
    'soy_soybeans':                   '#65a30d',
    'flax_linseed':                   '#78b030',
    'flax_linseed_oil':               '#6da028',
    'flax_linen':                     '#72a82c',
    'oilseed_crops':                  '#9cc420',
    'hemp_cannabis':                  '#7db824',
    'camelina':                       '#8ab830',

    // Pulses / Protein — purples
    'legumes_dried_pulses_protein_crops': '#a855f7',
    'peas':                           '#8b5cf6',
    'beans':                          '#7c3aed',
    'lentils':                        '#9f67e8',
    'chickpeas':                      '#b07cf0',
    'sweet_lupins':                   '#9060d8',
    'vetches':                        '#a070e0',

    // Root crops — pinks
    'potatoes':                       '#ec4899',
    'sugar_beet':                     '#f472b6',
    'fodder_roots':                   '#e05090',
    'mangelwurzel_fodder_beet':       '#d84888',
    'beetroot_beets':                 '#e060a0',

    // Vegetables — teals
    'fresh_vegetables':               '#14b8a6',
    'cucumber_pickle':                '#0d9488',
    'pumpkin_squash_gourd':           '#2dd4bf',
    'radish':                         '#10a898',
    'flowers_ornamental_plants':      '#06b6d4',
    'greenhouse_foil_film':           '#0891b2',
    'topinambur_jerusalem_artichoke': '#0ea5c0',

    // Grassland — greens
    'pasture_meadow_grassland_grass': '#22c55e',
    'temporary_grass':                '#4ade80',
    'poaceae_grasses':                '#16a34a',
    'clover':                         '#15803d',
    'alfalfa_lucerne':                '#059669',
    'esparsette_onobrychis':          '#047857',

    // Permanent crops — deep purples / reds
    'vineyards_wine_vine_rebland_grapes': '#7c3aed',
    'olive_plantations':              '#6d28d9',
    'orchards_fruits':                '#c026d3',
    'apples':                         '#d946ef',
    'pears':                          '#c084fc',
    'cherry_cherries':                '#e11d48',
    'peach':                          '#f43f5e',
    'nectarine':                      '#fb7185',
    'plums':                          '#be185d',
    'apricots':                       '#f97316',
    'strawberries':                   '#ef4444',
    'nuts':                           '#a16207',
    'hazelnuts_hazel':                '#92400e',
    'walnuts':                        '#78350f',
    'sweet_chestnuts':                '#854d0e',
    'quinces':                        '#ca8a04',
    'elder_elderberry':               '#9333ea',

    // Industrial / misc — slate / neutrals
    'industrial_nonfood_crops':       '#64748b',
    'hops':                           '#a3b818',
    'mustard':                        '#d0c020',
    'phacelia':                       '#8890a0',
    'aromatic_medicinal_culinary_plants_spices_herbs': '#0ea5e9',
    'black_cumin':                    '#6b7280',
    'caraway':                        '#7b8290',
    'fennel':                         '#54b090',
    'cress':                          '#50a878',
    'sage_chia':                      '#6aa090',
    'summer_poppy':                   '#e27070',
    'winter_poppy':                   '#d06060',
    'marian_thistles':                '#8888b0',
    'amaranth':                       '#b04060',
    'quinoa':                         '#c09040',
    'silphium_rosinweeds':            '#78a860',
    'st_johns_wort':                  '#c8a840',
    'ginko':                          '#88b848',

    // Forestry / fallow
    'tree_wood_forest':               '#166534',
    'afforestation_reforestation':    '#14532d',
    'shrubberries_shrubs':            '#2d6a4f',
    'fallow_land_not_crop':           '#94a3b8',
    'unmaintained':                   '#9ca3af',
    'peat_turf':                      '#78716c',

    // Other
    'not_known_and_other':            '#6b7280',
    'other_arable_land_crops':        '#737a88',
    'other_permanent_crops_plantations': '#7a6898',
    'nurseries_nursery':              '#50a060',
    'arable_land_seed_seedlings':     '#88a048',
};

// Broader grouping for EC_trans_n or crop_name fallback
const GROUP_COLORS = {
    'CEREALS': '#f59e0b',
    'PERMANENT GRASSLANDS': '#22c55e',
    'TEMPORARY GRASSLANDS': '#4ade80',
    'LANDES ESTIVES': '#16a34a',
    'OLIVE TREES': '#6d28d9',
    'VINES': '#7c3aed',
    'ORCHARDS': '#c026d3',
    'NUTS': '#a16207',
    'VEGETABLES': '#14b8a6',
    'CORN': '#eab308',
    'BARLEY': '#fbbf24',
};

const DEFAULT_COLOR = '#4f8ff7';

function getCategoryColor(props) {
    // Try EC_hcat_n first (most specific)
    if (props.EC_hcat_n && CATEGORY_COLORS[props.EC_hcat_n]) {
        return CATEGORY_COLORS[props.EC_hcat_n];
    }
    // Try crop_name in the sample data palette
    if (props.crop_name) {
        const key = props.crop_name.toLowerCase().replace(/ /g, '_');
        if (CATEGORY_COLORS[key]) return CATEGORY_COLORS[key];
        // Try matching partial group names
        for (const [group, color] of Object.entries(GROUP_COLORS)) {
            if (props.crop_name.toUpperCase().includes(group)) return color;
        }
    }
    // Try EC_trans_n
    if (props.EC_trans_n) {
        for (const [group, color] of Object.entries(GROUP_COLORS)) {
            if (props.EC_trans_n.toUpperCase().includes(group)) return color;
        }
    }
    return DEFAULT_COLOR;
}

function getLegendLabel(props) {
    return props.EC_hcat_n || props.crop_name || props.EC_trans_n || 'Unknown';
}

// ===== Map Setup =====
const map = L.map('map', { center: [48.5, 10], zoom: 5, zoomControl: true });
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
}).addTo(map);

let featureLayer = null;
let selectedFeature = null;
let currentDataset = null;
let currentColumns = [];
let lastMode = null; // 'full' or 'overview'

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
    } finally {
        hideLoading();
    }
}

function showDatasetInfo(info) {
    const box = document.getElementById('dataset-info');
    box.classList.add('visible');
    const crs = info.crs ? `EPSG:${info.crs}` : 'EPSG:4326';
    box.innerHTML = `
        <div class="info-row"><span class="info-label">Features</span><span class="info-value">${info.feature_count.toLocaleString()}</span></div>
        <div class="info-row"><span class="info-label">Columns</span><span class="info-value">${info.columns.length}</span></div>
        <div class="info-row"><span class="info-label">Source CRS</span><span class="info-value">${crs}</span></div>
        <div class="info-row"><span class="info-label">Format</span><span class="info-value">${currentDataset.split('.').pop().toUpperCase()}</span></div>
    `;
    document.getElementById('feature-count-badge').textContent = `${info.feature_count.toLocaleString()} features`;
}

// ===== Filters =====
const FILTER_COLUMNS = ['nation', 'year', 'crop_name', 'EC_hcat_n'];

async function populateFilters(filename) {
    for (const col of FILTER_COLUMNS) {
        const sel = document.querySelector(`[data-filter="${col}"]`);
        if (!sel) continue;
        const row = sel.closest('.filter-row');
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
                opt.value = v; opt.textContent = v;
                sel.appendChild(opt);
            });
        } catch (e) {}
    }
    const organicRow = document.querySelector('[data-filter="organic"]')?.closest('.filter-row');
    if (organicRow) organicRow.style.display = currentColumns.includes('organic') ? '' : 'none';
}

function getActiveFilters() {
    const f = {};
    document.querySelectorAll('[data-filter]').forEach(el => {
        if (el.value && currentColumns.includes(el.dataset.filter)) f[el.dataset.filter] = el.value;
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
        const zoom = map.getZoom();
        const filters = getActiveFilters();
        let fp = '';
        for (const [k, v] of Object.entries(filters)) fp += `&filter_${k}=${encodeURIComponent(v)}`;

        const geojson = await apiGet(
            `/datasets/${encodeURIComponent(currentDataset)}/features?bbox=${bbox}&zoom=${zoom}&limit=3000${fp}`
        );

        if (featureLayer) map.removeLayer(featureLayer);

        if (geojson.overview) {
            lastMode = 'overview';
            featureLayer = renderOverview(geojson);
        } else {
            lastMode = 'full';
            featureLayer = renderPolygons(geojson);
        }

        featureLayer.addTo(map);

        const count = geojson.features.length;
        const modeLabel = geojson.overview ? ' (overview)' : '';
        document.getElementById('feature-count-badge').textContent = `${count.toLocaleString()}${modeLabel}`;
        updateLegend(geojson);
    } catch (e) {
        console.error('Error loading features:', e);
    } finally {
        hideLoading();
    }
}

function renderPolygons(geojson) {
    return L.geoJSON(geojson, {
        style: f => {
            const color = getCategoryColor(f.properties);
            return { color, weight: 1.5, opacity: 0.9, fillColor: color, fillOpacity: 0.45 };
        },
        onEachFeature: (feature, layer) => {
            layer.on('click', () => showFeatureDetail(feature, layer));
            layer.on('mouseover', () => layer.setStyle({ weight: 3, fillOpacity: 0.7 }));
            layer.on('mouseout', () => { if (selectedFeature !== layer) featureLayer.resetStyle(layer); });
        }
    });
}

function renderOverview(geojson) {
    return L.geoJSON(geojson, {
        pointToLayer: (feature, latlng) => {
            const count = feature.properties.feature_count;
            const cat = feature.properties.dominant_category;
            const color = cat && CATEGORY_COLORS[cat] ? CATEGORY_COLORS[cat] : DEFAULT_COLOR;

            // Scale radius by feature count
            const radius = Math.min(Math.max(Math.sqrt(count) * 0.8, 6), 40);

            return L.circleMarker(latlng, {
                radius,
                fillColor: color,
                fillOpacity: 0.6,
                color: color,
                weight: 1.5,
                opacity: 0.8,
            }).bindTooltip(
                `<strong>${count.toLocaleString()}</strong> features<br>${cat || 'mixed'}`,
                { className: 'overview-tooltip' }
            );
        },
        onEachFeature: (feature, layer) => {
            layer.on('click', () => {
                // Zoom into this cluster
                const gs = feature.properties.grid_size;
                const [lng, lat] = feature.geometry.coordinates;
                map.fitBounds([
                    [lat - gs / 2, lng - gs / 2],
                    [lat + gs / 2, lng + gs / 2]
                ]);
            });
        }
    });
}

// ===== Feature Detail =====
function showFeatureDetail(feature, layer) {
    if (selectedFeature && featureLayer) featureLayer.resetStyle(selectedFeature);
    selectedFeature = layer;
    layer.setStyle({ weight: 3, color: '#ffffff', fillOpacity: 0.8 });

    const props = feature.properties;
    const order = ['field_id','farm_id','crop_name','crop_code','EC_trans_n','EC_hcat_n','EC_hcat_c','field_size','crop_area','organic','nation','year'];
    let rows = '';
    const shown = new Set();
    for (const k of order) { if (k in props) { rows += fmtRow(k, props[k]); shown.add(k); } }
    for (const [k, v] of Object.entries(props)) { if (!shown.has(k)) rows += fmtRow(k, v); }
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
    const cats = new Map(); // label -> color
    geojson.features.forEach(f => {
        if (geojson.overview) {
            const cat = f.properties.dominant_category;
            if (cat) cats.set(cat, CATEGORY_COLORS[cat] || DEFAULT_COLOR);
        } else {
            const label = getLegendLabel(f.properties);
            if (label !== 'Unknown') cats.set(label, getCategoryColor(f.properties));
        }
    });

    const c = document.getElementById('legend-content');
    c.innerHTML = '';
    [...cats.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([label, color]) => {
        const d = document.createElement('div');
        d.className = 'legend-item';
        const shortLabel = label.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        d.innerHTML = `<span class="legend-color" style="background:${color}"></span>${shortLabel}`;
        c.appendChild(d);
    });

    // Update legend title based on mode
    const title = document.querySelector('#legend-section .section-title');
    if (title) {
        const icon = title.querySelector('.section-icon')?.outerHTML || '';
        title.innerHTML = `${icon} Legend ${geojson.overview ? '(Dominant Category)' : '(Crop Type)'}`;
    }
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
        list.innerHTML = `<div class="catalog-loading"><span style="color:var(--danger)">Failed: ${e.message}</span></div>`;
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
    const partialCount = catalogData.files.filter(f => f.status === 'partial').length;
    summary.innerHTML = `
        <span class="stat"><span class="stat-value">${catalogData.files.length}</span><span class="stat-label">datasets</span></span>
        <span class="stat"><span class="stat-value">${catalogData.total_size_gb} GB</span><span class="stat-label">total</span></span>
        <span class="stat"><span class="stat-value">${readyCount}</span><span class="stat-label">ready</span></span>
        ${partialCount ? `<span class="stat"><span class="stat-value">${partialCount}</span><span class="stat-label">partial</span></span>` : ''}
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
        downloading: '⬇️', extracting: '📂', error: '❌',
        cancelled: '⛔', partial: '⚠️',
    };

    let actions = '';
    if (file.status === 'available' || file.status === 'error' || file.status === 'cancelled') {
        actions = `<button class="btn btn-primary btn-sm" onclick="startDownload('${file.name}', '${file.url}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>Download</button>`;
    } else if (file.status === 'downloaded') {
        actions = `<button class="btn btn-primary btn-sm" onclick="extractZip('${file.name}')">📂 Extract All</button>`;
    } else if (file.status === 'partial') {
        const failedJson = JSON.stringify(file.failed_files || []).replace(/'/g, "\\'");
        actions = `
            <button class="btn btn-primary btn-sm" onclick='retryFailed("${file.name}", ${failedJson})'>🔄 Retry Failed</button>
            <button class="btn btn-secondary btn-sm" onclick="extractZip('${file.name}')">📂 Re-extract All</button>
        `;
    } else if (file.status === 'downloading') {
        actions = `<button class="btn btn-danger btn-sm" onclick="cancelDownload('${file.name}')">Cancel</button>`;
    } else if (file.status === 'extracted') {
        actions = `<span style="color:var(--success);font-size:11px;font-weight:500;">✓ Ready</span>`;
    }

    // Status details
    let details = '';
    if (file.extracted_files && file.extracted_files.length > 0) {
        details += `<span title="${file.extracted_files.join(', ')}">${file.extracted_files.length} extracted</span>`;
    }
    if (file.failed_files && file.failed_files.length > 0) {
        details += `<span style="color:var(--danger)" title="${file.failed_files.join(', ')}">${file.failed_files.length} failed</span>`;
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
                ${details}
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
    } catch (e) { console.error('Download start failed:', e); }
}

async function extractZip(name) {
    try {
        await apiPost('/populate/extract', { name });
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) { f.status = 'extracting'; f.progress = 0; }
            renderCatalog(document.getElementById('catalog-search').value);
        }
        addDownloadToast(name, 'extracting');
        startProgressPolling();
        document.getElementById('download-indicator').classList.remove('hidden');
    } catch (e) { console.error('Extract failed:', e); }
}

async function retryFailed(name, failedFiles) {
    try {
        await apiPost('/populate/extract', { name, files: failedFiles });
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) { f.status = 'extracting'; }
            renderCatalog(document.getElementById('catalog-search').value);
        }
        addDownloadToast(name, 'extracting');
        startProgressPolling();
        document.getElementById('download-indicator').classList.remove('hidden');
    } catch (e) { console.error('Retry failed:', e); }
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
    } catch (e) { console.error('Cancel failed:', e); }
}

// ===== Progress SSE =====
function startProgressPolling() {
    if (sseSource) return;
    sseSource = new EventSource(API_BASE + '/populate/downloads/events');
    sseSource.onmessage = (event) => updateDownloadProgress(JSON.parse(event.data));
    sseSource.onerror = () => { sseSource.close(); sseSource = null; checkDownloadsComplete(); };
}

function updateDownloadProgress(downloads) {
    let anyActive = false;
    for (const [name, info] of Object.entries(downloads)) {
        updateToast(name, info);
        if (catalogData) {
            const f = catalogData.files.find(f => f.name === name);
            if (f) {
                f.status = info.status;
                f.progress = info.progress;
                f.extracted_files = info.extracted_files || [];
                f.failed_files = info.failed_files || [];
            }
        }
        if (info.status === 'downloading' || info.status === 'extracting') anyActive = true;
    }
    if (!document.getElementById('catalog-modal').classList.contains('hidden')) {
        renderCatalog(document.getElementById('catalog-search').value);
    }
    if (!anyActive) {
        if (sseSource) { sseSource.close(); sseSource = null; }
        document.getElementById('download-indicator').classList.add('hidden');
        loadDatasets(currentDataset);
    }
}

async function checkDownloadsComplete() {
    try {
        const status = await apiGet('/populate/downloads/status');
        const anyActive = Object.values(status).some(d => d.status === 'downloading' || d.status === 'extracting');
        if (anyActive) startProgressPolling();
        else document.getElementById('download-indicator').classList.add('hidden');
    } catch (e) {}
}

// ===== Download Toasts =====
function addDownloadToast(name, initialStatus = 'downloading') {
    const container = document.getElementById('download-toasts');
    if (document.getElementById(`toast-${CSS.escape(name)}`)) return;
    const toast = document.createElement('div');
    toast.className = 'download-toast';
    toast.id = `toast-${name}`;
    const iconHtml = initialStatus === 'extracting' ? '📂' : '<div class="mini-spinner"></div>';
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
    if (!toast) { if (info.status === 'downloading' || info.status === 'extracting') addDownloadToast(name, info.status); return; }
    const fill = toast.querySelector('.toast-progress-fill');
    const status = toast.querySelector('.toast-status');
    const icon = toast.querySelector('.toast-icon');
    fill.style.width = `${info.progress}%`;
    if (info.status === 'downloading') {
        fill.className = 'toast-progress-fill';
        const dl = formatBytes(info.downloaded_bytes || 0), total = formatBytes(info.total_bytes || 0);
        const speed = info.speed_bps ? formatSpeed(info.speed_bps) : '';
        status.textContent = `${dl} / ${total}${speed ? ' • ' + speed : ''} • ${info.progress}%`;
    } else if (info.status === 'extracting') {
        fill.className = 'toast-progress-fill extracting'; fill.style.width = '100%';
        const ext = (info.extracted_files || []).length;
        status.textContent = ext ? `Extracting... (${ext} done)` : 'Extracting...';
        icon.innerHTML = '📂';
    } else if (info.status === 'extracted') {
        fill.style.width = '100%'; fill.className = 'toast-progress-fill'; fill.style.background = 'var(--success)';
        status.textContent = 'Complete! Ready to explore.'; icon.innerHTML = '✅';
        toast.classList.add('success'); setTimeout(() => removeDownloadToast(name), 5000);
    } else if (info.status === 'partial') {
        fill.style.width = '100%'; fill.style.background = 'var(--warning)';
        const failed = (info.failed_files || []).length;
        status.textContent = `${failed} file(s) failed – retry in catalog`; icon.innerHTML = '⚠️';
        toast.classList.add('error');
    } else if (info.status === 'error') {
        fill.style.background = 'var(--danger)';
        status.textContent = `Error: ${info.error || 'Unknown'}`; icon.innerHTML = '❌';
        toast.classList.add('error');
    } else if (info.status === 'cancelled') {
        status.textContent = 'Cancelled'; icon.innerHTML = '⛔';
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
document.getElementById('catalog-search').addEventListener('input', (e) => renderCatalog(e.target.value));

let moveTimeout;
map.on('moveend', () => {
    clearTimeout(moveTimeout);
    moveTimeout = setTimeout(() => { if (currentDataset) loadFeatures(); }, 300);
});

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => { loadDatasets(); checkDownloadsComplete(); });
