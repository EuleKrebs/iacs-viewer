// ===== IACS Viewer - Main Application Logic =====

const API_BASE = '/api';

// Crop type color palette
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

function getCropColor(cropName) {
    return CROP_COLORS[cropName] || DEFAULT_COLOR;
}

// ===== Map Setup =====
const map = L.map('map', {
    center: [48.5, 10],
    zoom: 5,
    zoomControl: true,
});

// CartoDB dark tile layer (matches our dark UI)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
}).addTo(map);

// Remove the filter we added for default tiles since CartoDB dark doesn't need it
document.querySelector('.leaflet-tile-pane').style.filter = 'none';

// Feature layer
let featureLayer = null;
let selectedFeature = null;
let currentDataset = null;

// ===== Loading Indicator =====
function showLoading() {
    document.getElementById('loading-indicator').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-indicator').classList.add('hidden');
}

// ===== API Helpers =====
async function apiGet(path) {
    const resp = await fetch(API_BASE + path);
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
}

// ===== Dataset Management =====
async function loadDatasets() {
    const select = document.getElementById('dataset-select');
    try {
        const datasets = await apiGet('/datasets');
        select.innerHTML = '';
        if (datasets.length === 0) {
            select.innerHTML = '<option value="">No datasets found</option>';
            return;
        }
        datasets.forEach(ds => {
            const opt = document.createElement('option');
            opt.value = ds.name;
            opt.textContent = `${ds.name} (${ds.size_mb} MB)`;
            select.appendChild(opt);
        });
        // Auto-load first dataset
        if (datasets.length > 0) {
            selectDataset(datasets[0].name);
        }
    } catch (e) {
        select.innerHTML = '<option value="">Error loading datasets</option>';
        console.error(e);
    }
}

async function selectDataset(filename) {
    currentDataset = filename;
    showLoading();

    try {
        // Get dataset info
        const info = await apiGet(`/datasets/${filename}/info`);
        showDatasetInfo(info);

        // Populate filter dropdowns
        await populateFilters(filename);

        // Fly to dataset bounds
        const b = info.bounds;
        if (b.minx && b.miny && b.maxx && b.maxy) {
            map.fitBounds([[b.miny, b.minx], [b.maxy, b.maxx]], { padding: [30, 30] });
        }

        // Load features
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
    box.innerHTML = `
        <div class="info-row">
            <span class="info-label">Features</span>
            <span class="info-value">${info.feature_count.toLocaleString()}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Columns</span>
            <span class="info-value">${info.columns.length}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Format</span>
            <span class="info-value">${currentDataset.split('.').pop().toUpperCase()}</span>
        </div>
    `;
    document.getElementById('feature-count-badge').textContent = `${info.feature_count.toLocaleString()} features`;
}

// ===== Filters =====
async function populateFilters(filename) {
    const filterColumns = ['nation', 'year', 'crop_name', 'EC_hcat_n'];
    for (const col of filterColumns) {
        try {
            const values = await apiGet(`/datasets/${filename}/values/${col}`);
            const select = document.querySelector(`[data-filter="${col}"]`);
            if (!select) continue;
            // Keep first "All" option, remove rest
            const firstOpt = select.options[0];
            select.innerHTML = '';
            select.appendChild(firstOpt);
            values.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = v;
                select.appendChild(opt);
            });
        } catch (e) {
            console.warn(`Could not load values for ${col}:`, e);
        }
    }
}

function getActiveFilters() {
    const filters = {};
    document.querySelectorAll('[data-filter]').forEach(el => {
        if (el.value) {
            filters[el.dataset.filter] = el.value;
        }
    });
    return filters;
}

// ===== Feature Loading =====
async function loadFeatures() {
    if (!currentDataset) return;
    showLoading();

    try {
        // Build query params
        const bounds = map.getBounds();
        const bbox = [
            bounds.getWest(), bounds.getSouth(),
            bounds.getEast(), bounds.getNorth()
        ].join(',');

        const filters = getActiveFilters();
        let filterParams = '';
        for (const [k, v] of Object.entries(filters)) {
            filterParams += `&filter_${k}=${encodeURIComponent(v)}`;
        }

        const geojson = await apiGet(`/datasets/${currentDataset}/features?bbox=${bbox}&limit=3000${filterParams}`);

        // Update map layer
        if (featureLayer) {
            map.removeLayer(featureLayer);
        }

        featureLayer = L.geoJSON(geojson, {
            style: feature => ({
                color: getCropColor(feature.properties.crop_name),
                weight: 1.5,
                opacity: 0.9,
                fillColor: getCropColor(feature.properties.crop_name),
                fillOpacity: 0.45,
            }),
            onEachFeature: (feature, layer) => {
                layer.on('click', () => showFeatureDetail(feature, layer));
                layer.on('mouseover', () => {
                    layer.setStyle({ weight: 3, fillOpacity: 0.7 });
                });
                layer.on('mouseout', () => {
                    if (selectedFeature !== layer) {
                        featureLayer.resetStyle(layer);
                    }
                });
            }
        }).addTo(map);

        // Update badge
        document.getElementById('feature-count-badge').textContent =
            `${geojson.features.length.toLocaleString()} shown`;

        // Update legend
        updateLegend(geojson);

    } catch (e) {
        console.error('Error loading features:', e);
    } finally {
        hideLoading();
    }
}

// ===== Feature Detail =====
function showFeatureDetail(feature, layer) {
    // Reset previous selection
    if (selectedFeature && featureLayer) {
        featureLayer.resetStyle(selectedFeature);
    }
    selectedFeature = layer;
    layer.setStyle({ weight: 3, color: '#ffffff', fillOpacity: 0.8 });

    const props = feature.properties;
    const detailDiv = document.getElementById('feature-detail');

    let rows = '';
    const fieldOrder = [
        'field_id', 'farm_id', 'crop_name', 'crop_code',
        'EC_trans_n', 'EC_hcat_n', 'EC_hcat_c',
        'field_size', 'crop_area', 'organic', 'nation', 'year'
    ];

    // Show ordered fields first, then any extras
    const shown = new Set();
    for (const key of fieldOrder) {
        if (key in props) {
            rows += formatDetailRow(key, props[key]);
            shown.add(key);
        }
    }
    for (const [key, val] of Object.entries(props)) {
        if (!shown.has(key)) {
            rows += formatDetailRow(key, val);
        }
    }

    detailDiv.innerHTML = `<table class="detail-table">${rows}</table>`;
}

function formatDetailRow(key, value) {
    let displayVal = value;

    if (key === 'organic') {
        if (value === true || value === 'true' || value === 'True') {
            displayVal = '<span class="tag tag-organic">✓ Organic</span>';
        } else {
            displayVal = '<span class="tag tag-conventional">Conventional</span>';
        }
    } else if (key === 'field_size' || key === 'crop_area') {
        displayVal = value != null ? `${parseFloat(value).toFixed(2)} ha` : '–';
    } else if (value === null || value === undefined) {
        displayVal = '<span style="color: var(--text-muted)">–</span>';
    }

    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    return `<tr><td class="detail-key">${label}</td><td class="detail-value">${displayVal}</td></tr>`;
}

// ===== Legend =====
function updateLegend(geojson) {
    const crops = new Set();
    geojson.features.forEach(f => {
        if (f.properties.crop_name) crops.add(f.properties.crop_name);
    });

    const container = document.getElementById('legend-content');
    container.innerHTML = '';

    [...crops].sort().forEach(crop => {
        const item = document.createElement('div');
        item.className = 'legend-item';
        item.innerHTML = `
            <span class="legend-color" style="background: ${getCropColor(crop)}"></span>
            ${crop}
        `;
        container.appendChild(item);
    });
}

// ===== Event Listeners =====
document.getElementById('dataset-select').addEventListener('change', (e) => {
    if (e.target.value) selectDataset(e.target.value);
});

document.getElementById('apply-filters').addEventListener('click', () => {
    loadFeatures();
});

document.getElementById('clear-filters').addEventListener('click', () => {
    document.querySelectorAll('[data-filter]').forEach(el => el.value = '');
    loadFeatures();
});

// Reload features on map move (debounced)
let moveTimeout;
map.on('moveend', () => {
    clearTimeout(moveTimeout);
    moveTimeout = setTimeout(() => {
        if (currentDataset) loadFeatures();
    }, 300);
});

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    loadDatasets();
});
