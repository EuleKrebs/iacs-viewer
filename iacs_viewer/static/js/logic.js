// ===== IACS Viewer - Main Application Logic =====

const API_BASE = '/api';

// ===== Color Palette for EC_hcat_n categories (from IACS documentation) =====
// Grouped by land-use type with visually distinct colors
const CATEGORY_COLORS = {
    // Cereals — warm golds/ambers
    'common_soft_wheat':              '#c49a3c',
    'spring_common_soft_wheat':       '#c9a044',
    'winter_common_soft_wheat':       '#b8903a',
    'durum_hard_wheat':               '#b08630',
    'spring_durum_hard_wheat':        '#a87e2c',
    'winter_durum_hard_wheat':        '#9e7628',
    'barley':                         '#d4aa50',
    'spring_barley':                  '#d0a84c',
    'winter_barley':                  '#c09838',
    'rye':                            '#b89040',
    'spring_rye':                     '#b48c3c',
    'winter_rye':                     '#a68034',
    'grain_maize_corn_popcorn':       '#c8a030',
    'green_silo_maize':               '#a89028',
    'cereal':                         '#c49648',
    'spring_oats':                    '#bfa05c',
    'winter_oats':                    '#b09450',
    'spring_triticale':               '#b49044',
    'winter_triticale':               '#a6863c',
    'millet_sorghum':                 '#a07830',
    'rice':                           '#c8b060',
    'buckwheat':                      '#9a8840',
    'spring_spelt':                   '#b09848',
    'winter_spelt':                   '#a08c40',
    'spring_emmer':                   '#a89450',
    'winter_emmer':                   '#988848',
    'spring_meslin':                  '#aa9a4c',
    'winter_meslin':                  '#9c8e44',
    'canary_seed_canaryseed':         '#b8a050',

    // Oilseeds — olive/sage tones
    'sunflower':                      '#8a9e48',
    'winter_rapeseed_rape':           '#7c9440',
    'summer_rapeseed_rape':           '#8ca04c',
    'soy_soybeans':                   '#6e8838',
    'flax_linseed':                   '#748c40',
    'flax_linseed_oil':               '#6c8438',
    'flax_linen':                     '#708840',
    'oilseed_crops':                  '#809844',
    'hemp_cannabis':                  '#6a8234',
    'camelina':                       '#78903c',

    // Pulses / Protein — dusty mauves
    'legumes_dried_pulses_protein_crops': '#8b7098',
    'peas':                           '#7e6890',
    'beans':                          '#6e5c80',
    'lentils':                        '#887498',
    'chickpeas':                      '#9480a0',
    'sweet_lupins':                   '#786c88',
    'vetches':                        '#847098',

    // Root crops — muted roses
    'potatoes':                       '#b07080',
    'sugar_beet':                     '#b87888',
    'fodder_roots':                   '#a06878',
    'mangelwurzel_fodder_beet':       '#986474',
    'beetroot_beets':                 '#a87080',

    // Vegetables — soft teals
    'fresh_vegetables':               '#5a9490',
    'cucumber_pickle':                '#4e8884',
    'pumpkin_squash_gourd':           '#68a09c',
    'radish':                         '#528c88',
    'flowers_ornamental_plants':      '#4c8898',
    'greenhouse_foil_film':           '#48808e',
    'topinambur_jerusalem_artichoke': '#508890',

    // Grassland — natural greens
    'pasture_meadow_grassland_grass': '#5a9a5e',
    'temporary_grass':                '#6ca86c',
    'poaceae_grasses':                '#4e8a4e',
    'clover':                         '#3c7a40',
    'alfalfa_lucerne':                '#3a7c50',
    'esparsette_onobrychis':          '#347048',

    // Permanent crops — earthy plums/burgundy
    'vineyards_wine_vine_rebland_grapes': '#7a5070',
    'olive_plantations':              '#6e7050',
    'orchards_fruits':                '#906878',
    'apples':                         '#987080',
    'pears':                          '#8c7888',
    'cherry_cherries':                '#8c4858',
    'peach':                          '#a06068',
    'nectarine':                      '#a87078',
    'plums':                          '#7c4058',
    'apricots':                       '#b08060',
    'strawberries':                   '#a05458',
    'nuts':                           '#8a7048',
    'hazelnuts_hazel':                '#7c6440',
    'walnuts':                        '#6c5838',
    'sweet_chestnuts':                '#746040',
    'quinces':                        '#9c8848',
    'elder_elderberry':               '#705878',

    // Industrial / misc — warm greys
    'industrial_nonfood_crops':       '#6e7478',
    'hops':                           '#7c8840',
    'mustard':                        '#a09840',
    'phacelia':                       '#787e88',
    'aromatic_medicinal_culinary_plants_spices_herbs': '#508088',
    'black_cumin':                    '#686e74',
    'caraway':                        '#707680',
    'fennel':                         '#4e8070',
    'cress':                          '#4c7868',
    'sage_chia':                      '#5a7870',
    'summer_poppy':                   '#a86868',
    'winter_poppy':                   '#985c5c',
    'marian_thistles':                '#707088',
    'amaranth':                       '#884858',
    'quinoa':                         '#9a8050',
    'silphium_rosinweeds':            '#688848',
    'st_johns_wort':                  '#9c8c48',
    'ginko':                          '#6c8840',

    // Forestry / fallow — deep natural tones
    'tree_wood_forest':               '#2e5a38',
    'afforestation_reforestation':    '#284e30',
    'shrubberries_shrubs':            '#3e5e48',
    'fallow_land_not_crop':           '#808890',
    'unmaintained':                   '#888e94',
    'peat_turf':                      '#6e6860',

    // Other
    'not_known_and_other':            '#686e74',
    'other_arable_land_crops':        '#6e7478',
    'other_permanent_crops_plantations': '#687068',
    'nurseries_nursery':              '#4e7e58',
    'arable_land_seed_seedlings':     '#748848',
};

// Broader grouping for EC_trans_n or crop_name fallback
const GROUP_COLORS = {
    'CEREALS': '#c49a3c',
    'PERMANENT GRASSLANDS': '#5a9a5e',
    'TEMPORARY GRASSLANDS': '#6ca86c',
    'LANDES ESTIVES': '#4e8a4e',
    'OLIVE TREES': '#6e7050',
    'VINES': '#7a5070',
    'ORCHARDS': '#906878',
    'NUTS': '#8a7048',
    'VEGETABLES': '#5a9490',
    'CORN': '#c8a030',
    'BARLEY': '#d4aa50',
};

const DEFAULT_COLOR = '#6888a8';

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
    const crs = info.crs ? (String(info.crs).startsWith('EPSG:') ? info.crs : `EPSG:${info.crs}`) : 'EPSG:4326';
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

function mergeOverviewClusters(features) {
    /**
     * Greedy merge: repeatedly combine the closest pair of clusters
     * until no two clusters overlap on screen. Uses pixel distance
     * so it works at any zoom level.
     */
    if (!features.length) return features;

    // Convert to working array with pixel positions
    let clusters = features.map(f => {
        const [lng, lat] = f.geometry.coordinates;
        const pt = map.latLngToContainerPoint([lat, lng]);
        return {
            x: pt.x, y: pt.y,
            lng, lat,
            count: f.properties.feature_count,
            cat: f.properties.dominant_category,
            gridSize: f.properties.grid_size,
        };
    });

    // Merge until no overlaps. A cluster's radius in pixels:
    function radius(c) { return Math.min(Math.max(Math.sqrt(c.count) * 0.7, 8), 44); }

    let merged = true;
    while (merged) {
        merged = false;
        for (let i = 0; i < clusters.length; i++) {
            for (let j = i + 1; j < clusters.length; j++) {
                const a = clusters[i], b = clusters[j];
                const dx = a.x - b.x, dy = a.y - b.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const minDist = radius(a) + radius(b) + 4; // 4px padding

                if (dist < minDist) {
                    // Merge b into a (weighted average position)
                    const total = a.count + b.count;
                    a.lng = (a.lng * a.count + b.lng * b.count) / total;
                    a.lat = (a.lat * a.count + b.lat * b.count) / total;
                    const pt = map.latLngToContainerPoint([a.lat, a.lng]);
                    a.x = pt.x; a.y = pt.y;
                    a.count = total;
                    // Keep dominant category of the larger cluster
                    if (b.count > a.count - b.count) a.cat = b.cat;
                    a.gridSize = Math.max(a.gridSize, b.gridSize);
                    clusters.splice(j, 1);
                    merged = true;
                    break;
                }
            }
            if (merged) break;
        }
    }

    return clusters;
}

function renderOverview(geojson) {
    const clusters = mergeOverviewClusters(geojson.features);
    const group = L.layerGroup();

    for (const c of clusters) {
        const color = c.cat && CATEGORY_COLORS[c.cat] ? CATEGORY_COLORS[c.cat] : DEFAULT_COLOR;
        const radius = Math.min(Math.max(Math.sqrt(c.count) * 0.7, 8), 44);

        const marker = L.circleMarker([c.lat, c.lng], {
            radius,
            fillColor: color,
            fillOpacity: 0.55,
            color: color,
            weight: 1.5,
            opacity: 0.75,
        }).bindTooltip(
            `<strong>${c.count.toLocaleString()}</strong> features<br>${(c.cat || 'mixed').replace(/_/g, ' ')}`,
            { className: 'overview-tooltip' }
        );

        marker.on('click', () => {
            const gs = c.gridSize;
            map.fitBounds([
                [c.lat - gs, c.lng - gs],
                [c.lat + gs, c.lng + gs]
            ]);
        });

        group.addLayer(marker);
    }

    return group;
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
