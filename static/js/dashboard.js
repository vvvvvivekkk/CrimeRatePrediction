/* ================================================================
   CRIME ANALYTICS INDIA – DASHBOARD JS v2
   Multi-state filtering · Year range · Recursive ML forecast
   Leaflet choropleth · Chart.js (Line/Bar/Doughnut/Radar)
   ================================================================ */
'use strict';

/* ─── Chart.js Defaults ─────────────────────────────────────── */
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.boxWidth = 12;

/* ─── App State ─────────────────────────────────────────────── */
const State = {
    historicalData: [],
    predictedData: [],
    allStates: [],
    selectedStates: [],
    startYear: null,
    endYear: null,
    leafletMap: null,
    geoLayer: null,
    trendChart: null,
    barChart: null,
    riskChart: null,
    featureChart: null,
    growthChart: null,
    tableData: [],
    tableSortCol: 1,
    tableSortAsc: true,
    featureImportance: null,
};

/* ─── Colours ───────────────────────────────────────────────── */
const COLORS = {
    blue: '#3b82f6', purple: '#8b5cf6', cyan: '#06b6d4',
    green: '#10b981', amber: '#f59e0b', red: '#ef4444',
    pink: '#ec4899', indigo: '#6366f1',
};
const PALETTE = Object.values(COLORS);

/* ─── GeoJSON → DB name aliases ─────────────────────────────── */
/* Maps every GADM GeoJSON NAME_1 variant → the DB state_name used
   in the dataset. Add entries here whenever the popup shows N/A.  */
const STATE_ALIASES = {
    // Spelling / old-name variants (GADM dataset)
    'Orissa': 'Odisha',
    'Uttaranchal': 'Uttarakhand',
    'Pondicherry': 'Puducherry',

    // GADM often uses these exact names – map to DB name
    'Andaman and Nicobar': 'Andaman and Nicobar Islands',
    'Andaman & Nicobar': 'Andaman and Nicobar Islands',
    'Andaman and Nicobar Islands': 'Andaman and Nicobar Islands',
    'Dadra and Nagar Haveli': 'Dadra and Nagar Haveli',
    'Daman and Diu': 'Daman and Diu',
    'Jammu and Kashmir': 'Jammu and Kashmir',
    'Jammu & Kashmir': 'Jammu and Kashmir',
    'NCT of Delhi': 'Delhi',
    'Delhi': 'Delhi',
    'Arunachal Pradesh': 'Arunachal Pradesh',
    'Himachal Pradesh': 'Himachal Pradesh',
    'Madhya Pradesh': 'Madhya Pradesh',
    'Andhra Pradesh': 'Andhra Pradesh',
    'Uttar Pradesh': 'Uttar Pradesh',
    'West Bengal': 'West Bengal',
    'Tamil Nadu': 'Tamil Nadu',
    'Chhattisgarh': 'Chhattisgarh',
    'Chattisgarh': 'Chhattisgarh',
};

/* Build a lowercase → canonical DB name lookup for fallback matching */
function buildLookupWithFallback(predData) {
    const lookup = {};
    predData.forEach(r => {
        if (!lookup[r.state_name] || r.year > lookup[r.state_name].year)
            lookup[r.state_name] = r;
    });
    // Also index by lowercase for case-insensitive fallback
    const lowerLookup = {};
    Object.keys(lookup).forEach(k => { lowerLookup[k.toLowerCase().trim()] = lookup[k]; });
    return { lookup, lowerLookup };
}

/* Resolve a GeoJSON NAME_1 to the dataset entry, with multiple fallbacks */
function resolveEntry(geoName, lookup, lowerLookup) {
    if (!geoName) return null;
    // 1. Direct alias map
    const aliased = STATE_ALIASES[geoName];
    if (aliased && lookup[aliased]) return lookup[aliased];
    // 2. Exact DB name match
    if (lookup[geoName]) return lookup[geoName];
    // 3. Case-insensitive match
    const lower = geoName.toLowerCase().trim();
    if (lowerLookup[lower]) return lowerLookup[lower];
    // 4. Partial match (GeoJSON name starts with or contains DB name)
    for (const [dbKey, entry] of Object.entries(lookup)) {
        if (lower.includes(dbKey.toLowerCase()) || dbKey.toLowerCase().includes(lower))
            return entry;
    }
    return null;
}

const STATE_COORDS = {
    "Andhra Pradesh": [15.91, 79.74], "Arunachal Pradesh": [28.21, 94.72],
    "Assam": [26.20, 92.93], "Bihar": [25.09, 85.31],
    "Chhattisgarh": [21.27, 81.86], "Goa": [15.29, 74.12],
    "Gujarat": [22.25, 71.19], "Haryana": [29.05, 76.08],
    "Himachal Pradesh": [31.10, 77.17], "Jharkhand": [23.61, 85.27],
    "Karnataka": [15.31, 75.71], "Kerala": [10.85, 76.27],
    "Madhya Pradesh": [22.97, 78.65], "Maharashtra": [19.75, 75.71],
    "Manipur": [24.66, 93.90], "Meghalaya": [25.46, 91.36],
    "Mizoram": [23.16, 92.93], "Nagaland": [26.15, 94.56],
    "Odisha": [20.95, 85.09], "Punjab": [31.14, 75.34],
    "Rajasthan": [27.02, 74.21], "Sikkim": [27.53, 88.51],
    "Tamil Nadu": [11.12, 78.65], "Telangana": [18.11, 79.01],
    "Tripura": [23.94, 91.98], "Uttar Pradesh": [26.84, 80.94],
    "Uttarakhand": [30.06, 79.01], "West Bengal": [22.98, 87.85],
    "Delhi": [28.70, 77.10],
};

/* ════════════════════════════════════════════════════════════════
   TOAST & UI HELPERS
   ════════════════════════════════════════════════════════════════ */
function showToast(msg, type = 'info', duration = 4000) {
    const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
    const tc = document.getElementById('toasts');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span>
                   <span class="toast-msg">${msg}</span>`;
    tc.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0'; t.style.transition = 'opacity 0.4s';
        setTimeout(() => t.remove(), 400);
    }, duration);
}

function setSideMsg(msg, type = '') {
    const el = document.getElementById('side-msg');
    el.innerHTML = msg;
    el.className = `text-sm ${type}`;
}

function setForecastBtnLoading(loading) {
    const btn = document.getElementById('btn-forecast');
    const txt = document.getElementById('fc-txt');
    const sp = document.getElementById('fc-spin');
    btn.disabled = loading;
    txt.textContent = loading ? 'Forecasting…' : '🔮 Generate Forecast';
    sp.classList.toggle('hidden', !loading);
}

function showLoadingOverlay(text = 'Loading data…') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
}
function hideLoadingOverlay() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

/* ════════════════════════════════════════════════════════════════
   MULTI-STATE DROPDOWN
   ════════════════════════════════════════════════════════════════ */
function initMultiSelect(states) {
    State.allStates = states;
    const container = document.getElementById('ms-options');
    container.innerHTML = '';

    states.forEach(s => {
        const div = document.createElement('div');
        div.className = 'ms-option';
        div.dataset.value = s;
        div.innerHTML = `<input type="checkbox" id="ms-cb-${s.replace(/\s/g, '_')}" value="${s}">
                         <label for="ms-cb-${s.replace(/\s/g, '_')}">${s}</label>`;
        div.querySelector('input').addEventListener('change', updateMsLabel);
        container.appendChild(div);
    });
}

function updateMsLabel() {
    const checked = [...document.querySelectorAll('#ms-options input:checked')].map(c => c.value);
    State.selectedStates = checked;
    const label = document.getElementById('ms-label');
    if (checked.length === 0 || checked.length === State.allStates.length) {
        label.textContent = 'All States (India)';
    } else if (checked.length === 1) {
        label.textContent = checked[0];
    } else {
        label.textContent = `${checked.length} States selected`;
    }
}

function setupMultiSelectUI() {
    const trigger = document.getElementById('ms-trigger');
    const dropdown = document.getElementById('ms-dropdown');
    const search = document.getElementById('ms-search');
    const options = document.getElementById('ms-options');

    trigger.addEventListener('click', () => dropdown.classList.toggle('hidden'));
    document.addEventListener('click', e => {
        if (!document.getElementById('ms-wrapper').contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    search.addEventListener('input', () => {
        const q = search.value.toLowerCase();
        [...options.querySelectorAll('.ms-option')].forEach(opt => {
            opt.style.display = opt.dataset.value.toLowerCase().includes(q) ? '' : 'none';
        });
    });

    document.getElementById('ms-select-all').addEventListener('click', () => {
        [...options.querySelectorAll('input')].forEach(cb => cb.checked = true);
        updateMsLabel();
    });
    document.getElementById('ms-clear').addEventListener('click', () => {
        [...options.querySelectorAll('input')].forEach(cb => cb.checked = false);
        updateMsLabel();
    });
    document.getElementById('ms-apply').addEventListener('click', () => {
        dropdown.classList.add('hidden');
        applyFilters();
    });
}

/* ════════════════════════════════════════════════════════════════
   YEAR FILTER SETUP
   ════════════════════════════════════════════════════════════════ */
function setupYearFilter() {
    document.getElementById('year-preset').addEventListener('change', e => {
        const custom = document.getElementById('custom-year-range');
        if (e.target.value === 'custom') {
            custom.classList.remove('hidden');
        } else {
            custom.classList.add('hidden');
        }
    });
}

function setupScrollToForecastResults() {
    const btn = document.getElementById('btn-scroll-to-results');
    const section = document.getElementById('forecast-results-section');
    if (!btn || !section) return;
    btn.addEventListener('click', () => {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
}

function getYearRange() {
    const preset = document.getElementById('year-preset').value;
    const now = 2024;
    if (preset === 'all') return { start: null, end: null };
    if (preset === '5') return { start: now - 4, end: now };
    if (preset === '10') return { start: now - 9, end: now };
    // custom
    const s = parseInt(document.getElementById('start-year').value) || null;
    const e = parseInt(document.getElementById('end-year').value) || null;
    return { start: s, end: e };
}

function buildFilterParams() {
    const { start, end } = getYearRange();
    const params = new URLSearchParams();
    const sel = State.selectedStates;
    if (sel.length > 0 && sel.length < State.allStates.length) {
        params.set('states', sel.join(','));
    }
    if (start) params.set('start_year', start);
    if (end) params.set('end_year', end);
    return params;
}

/* ════════════════════════════════════════════════════════════════
   LEAFLET MAP
   ════════════════════════════════════════════════════════════════ */
function initMap() {
    State.leafletMap = L.map('map', { center: [22.5, 82.5], zoom: 4.5 });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OSM | © CARTO', subdomains: 'abcd', maxZoom: 19,
    }).addTo(State.leafletMap);
}

function getRateColor(rate) {
    if (!rate || rate < 150) return '#10b981';
    if (rate <= 300) return '#f59e0b';
    return '#ef4444';
}

function updateMapLayer(predictedData) {
    if (!State.leafletMap) return;

    const isHighlighted = new Set(State.selectedStates);

    // Build lookup with case-insensitive fallback
    const { lookup, lowerLookup } = buildLookupWithFallback(predictedData);

    if (State.geoLayer) State.leafletMap.removeLayer(State.geoLayer);

    const geoUrls = [
        '/static/india_states.geojson',
        'https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson'
    ];

    const tryFetch = async (urls) => {
        for (const url of urls) {
            try {
                const r = await fetch(url);
                if (r.ok) return await r.json();
                console.error('[GeoJSON] Load failed:', url, 'status:', r.status, r.statusText);
            } catch (err) {
                console.error('[GeoJSON] Load failed:', url, err.message || err);
            }
        }
        throw new Error('GeoJSON unavailable');
    };

    tryFetch(geoUrls)
        .then(geojson => {
            State.geoLayer = L.geoJSON(geojson, {
                style: feat => {
                    const geoName = (feat.properties.NAME_1 || feat.properties.name || '').trim();
                    const entry = resolveEntry(geoName, lookup, lowerLookup);
                    /* resolved DB name for highlight check */
                    const dbName = entry ? entry.state_name : (STATE_ALIASES[geoName] || geoName);
                    const isSelected = isHighlighted.size === 0 || isHighlighted.has(dbName);
                    return {
                        fillColor: entry ? getRateColor(entry.predicted_crime_rate) : '#1e293b',
                        fillOpacity: entry ? (isSelected ? 0.78 : 0.28) : 0.2,
                        color: isSelected && isHighlighted.size > 0 ? '#60a5fa' : '#0f172a',
                        weight: isSelected && isHighlighted.size > 0 ? 2.5 : 1.2,
                    };
                },
                onEachFeature: (feat, layer) => {
                    const geoName = (feat.properties.NAME_1 || feat.properties.name || '').trim();
                    const entry = resolveEntry(geoName, lookup, lowerLookup);
                    const dbName = entry ? entry.state_name : (STATE_ALIASES[geoName] || geoName);
                    const rate = entry ? entry.predicted_crime_rate.toFixed(1) : 'N/A';
                    const lvl = entry ? entry.crime_level : 'No data';
                    const yr = entry ? entry.year : '–';
                    const color = entry ? getRateColor(entry.predicted_crime_rate) : '#64748b';

                    // Log unmatched states once so developers can extend the alias map
                    if (!entry) console.warn('[Map] No data for GeoJSON state:', geoName);

                    layer.bindPopup(`
                        <div style="min-width:190px;padding:6px 0;">
                          <div style="font-size:1rem;font-weight:700;margin-bottom:6px;">${dbName}</div>
                          <div style="font-size:0.8rem;color:#94a3b8;">Prediction Year: <strong style="color:#e2e8f0;">${yr}</strong></div>
                          <div style="font-size:0.8rem;color:#94a3b8;">Crime Rate: <strong style="color:#e2e8f0;">${rate} / 100k</strong></div>
                          <div style="font-size:0.8rem;color:#94a3b8;">Risk Level: <strong style="color:${color};">${lvl}</strong></div>
                        </div>`, { className: 'dark-popup' });

                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.95, weight: 2.5 }));
                    layer.on('mouseout', () => layer.setStyle({
                        fillOpacity: entry ? 0.78 : 0.2,
                        weight: isHighlighted.size > 0 && isHighlighted.has(dbName) ? 2.5 : 1.2,
                    }));
                }
            }).addTo(State.leafletMap);
        })
        .catch((err) => {
            console.error('[GeoJSON] All sources failed, using circle markers fallback.', err?.message || err);
            Object.entries(lookup).forEach(([name, entry]) => {
                const coords = STATE_COORDS[name]; if (!coords) return;
                L.circleMarker(coords, {
                    radius: Math.min(24, 8 + entry.predicted_crime_rate / 40),
                    fillColor: getRateColor(entry.predicted_crime_rate),
                    color: '#0f172a', weight: 1, fillOpacity: 0.85,
                }).addTo(State.leafletMap)
                    .bindPopup(`<b>${name}</b><br>${entry.predicted_crime_rate.toFixed(1)} / 100k<br>Risk: ${entry.crime_level}`);
            });
        });

    const maxYr = predictedData.length ? Math.max(...predictedData.map(d => d.year)) : '';
    document.getElementById('map-year-label').textContent = maxYr ? `Through ${maxYr}` : '';
}

/* ════════════════════════════════════════════════════════════════
   CHART BUILDERS
   ════════════════════════════════════════════════════════════════ */
function chartBase() {
    return {
        options: {
            responsive: true, maintainAspectRatio: false,
            animation: { duration: 500 },
            plugins: {
                legend: { labels: { color: '#94a3b8', padding: 16, usePointStyle: true } },
                tooltip: {
                    backgroundColor: '#131929', borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1, titleColor: '#f1f5f9', bodyColor: '#94a3b8',
                    padding: 12, cornerRadius: 8,
                },
            },
        }
    };
}

function buildTrendChart(labels, histSeries, predSeries, stateLabel) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (State.trendChart) State.trendChart.destroy();
    const cfg = chartBase();

    const gH = ctx.createLinearGradient(0, 0, 0, 300);
    gH.addColorStop(0, 'rgba(59,130,246,0.25)'); gH.addColorStop(1, 'rgba(59,130,246,0)');
    const gP = ctx.createLinearGradient(0, 0, 0, 300);
    gP.addColorStop(0, 'rgba(139,92,246,0.22)'); gP.addColorStop(1, 'rgba(139,92,246,0)');

    document.getElementById('trend-title').innerHTML =
        `<span class="icon">📉</span> ${stateLabel} – Historical &amp; Forecast`;

    State.trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Historical', data: histSeries, borderColor: COLORS.blue,
                    backgroundColor: gH, pointRadius: 3, pointHoverRadius: 6,
                    tension: 0.38, fill: true, borderWidth: 2
                },
                {
                    label: 'Forecast', data: predSeries, borderColor: COLORS.purple,
                    backgroundColor: gP, borderDash: [5, 4],
                    pointRadius: 3, pointHoverRadius: 6,
                    tension: 0.38, fill: true, borderWidth: 2
                },
            ],
        },
        options: {
            ...cfg.options,
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#475569', maxTicksLimit: 12 } },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#475569' },
                    title: { display: true, text: 'Crime Rate / 100k', color: '#475569', font: { size: 11 } }
                },
            }
        }
    });
}

function buildBarChart(labels, values) {
    const ctx = document.getElementById('barChart').getContext('2d');
    if (State.barChart) State.barChart.destroy();
    const colors = values.map(v => v > 300 ? COLORS.red : v > 150 ? COLORS.amber : COLORS.green);
    State.barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Avg Predicted Rate', data: values,
                backgroundColor: colors.map(c => c + 'cc'), borderColor: colors,
                borderWidth: 1.5, borderRadius: 6, borderSkipped: false
            }]
        },
        options: {
            ...chartBase().options, indexAxis: 'y',
            plugins: { ...chartBase().options.plugins, legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#475569' } },
                y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 11 } } }
            }
        }
    });
}

function buildRiskChart(high, med, low) {
    const ctx = document.getElementById('riskChart').getContext('2d');
    if (State.riskChart) State.riskChart.destroy();
    State.riskChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High (>300)', 'Medium (150–300)', 'Low (<150)'],
            datasets: [{
                data: [high, med, low],
                backgroundColor: ['rgba(239,68,68,0.8)', 'rgba(245,158,11,0.8)', 'rgba(16,185,129,0.8)'],
                borderColor: ['#ef4444', '#f59e0b', '#10b981'],
                borderWidth: 2, hoverOffset: 8
            }]
        },
        options: {
            ...chartBase().options, cutout: '65%',
            plugins: {
                ...chartBase().options.plugins,
                legend: { position: 'bottom', labels: { color: '#94a3b8', padding: 12, usePointStyle: true } }
            }
        }
    });
}

function buildFeatureChart(historicalData, selectedState) {
    const ctx = document.getElementById('featureChart').getContext('2d');
    if (State.featureChart) State.featureChart.destroy();

    if (State.featureImportance && typeof State.featureImportance === 'object') {
        const entries = Object.entries(State.featureImportance).sort((a, b) => b[1] - a[1]);
        const labels = entries.map(([k]) => k.replace(/_/g, ' '));
        const values = entries.map(([, v]) => Math.min(100, Number(v) * 100));
        State.featureChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Importance',
                    data: values,
                    backgroundColor: PALETTE.slice(0, labels.length).map(c => c + 'cc'),
                    borderColor: PALETTE.slice(0, labels.length),
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                ...chartBase().options,
                indexAxis: 'y',
                plugins: { ...chartBase().options.plugins, legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#475569', max: 100 } },
                    y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } }
                }
            }
        });
        return;
    }

    let data = historicalData;
    if (selectedState && selectedState !== 'All') {
        data = historicalData.filter(d => d.state_name === selectedState);
    }
    if (!data.length) return;

    const avg = key => data.reduce((a, r) => a + (r[key] || 0), 0) / data.length;
    const uRate = Math.min(100, avg('unemployment_rate') * 5);
    const litRate = avg('literacy_rate');
    const urbRate = avg('urbanization_rate');
    const polRate = Math.min(100, avg('police_strength_per_100k') / 2);
    const crRate = Math.min(100, avg('crime_rate_per_100k') / 6);

    State.featureChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Unemployment×5', 'Literacy %', 'Urbanization %', 'Police/50', 'Crime/6'],
            datasets: [{
                label: selectedState || 'National Avg',
                data: [uRate, litRate, urbRate, polRate, crRate],
                backgroundColor: 'rgba(59,130,246,0.18)', borderColor: COLORS.blue,
                pointBackgroundColor: COLORS.blue, pointRadius: 5, borderWidth: 2
            }]
        },
        options: {
            ...chartBase().options,
            scales: {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.07)' },
                    grid: { color: 'rgba(255,255,255,0.07)' },
                    pointLabels: { color: '#94a3b8', font: { size: 11 } },
                    ticks: { color: '#475569', backdropColor: 'transparent', stepSize: 25 },
                    min: 0, max: 100
                }
            }
        }
    });
}

function buildGrowthChart(historicalData) {
    const ctx = document.getElementById('growthChart');
    if (!ctx) return;
    if (State.growthChart) State.growthChart.destroy();
    if (!historicalData.length) return;

    const byState = {};
    historicalData.forEach(d => {
        if (!byState[d.state_name]) byState[d.state_name] = [];
        byState[d.state_name].push({ year: d.year, rate: d.crime_rate_per_100k });
    });
    const growthList = [];
    Object.entries(byState).forEach(([state, points]) => {
        points.sort((a, b) => a.year - b.year);
        const first = points[0];
        const last = points[points.length - 1];
        if (first && last && first.year < last.year && first.rate > 0) {
            const pct = ((last.rate - first.rate) / first.rate) * 100;
            growthList.push({ state, pct, years: last.year - first.year });
        }
    });
    growthList.sort((a, b) => b.pct - a.pct);
    const topGrowth = growthList.slice(0, 10);
    const labels = topGrowth.map(x => x.state);
    const values = topGrowth.map(x => x.pct);
    const colors = values.map(v => v > 0 ? COLORS.red : COLORS.green);

    State.growthChart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '10-Year Growth %',
                data: values,
                backgroundColor: colors.map(c => c + 'cc'),
                borderColor: colors,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            ...chartBase().options,
            indexAxis: 'y',
            plugins: { ...chartBase().options.plugins, legend: { display: false } },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#475569', callback: v => v + '%' }
                },
                y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } }
            }
        }
    });
}

/* ════════════════════════════════════════════════════════════════
   KPI WIDGETS
   ════════════════════════════════════════════════════════════════ */
function updateKPIs(predictedData) {
    if (!predictedData.length) return;
    const maxYear = Math.max(...predictedData.map(d => d.year));
    const latest = predictedData.filter(d => d.year === maxYear);
    if (!latest.length) return;

    const sorted = [...latest].sort((a, b) => b.predicted_crime_rate - a.predicted_crime_rate);
    const topState = sorted[0];
    document.getElementById('w-top-state').textContent = topState.state_name;
    document.getElementById('w-top-state-sub').textContent =
        `${topState.predicted_crime_rate.toFixed(1)} / 100k in ${topState.year}`;
    document.getElementById('w-highest-rate').textContent = topState.predicted_crime_rate.toFixed(1);

    const avg = latest.reduce((a, d) => a + d.predicted_crime_rate, 0) / latest.length;
    document.getElementById('w-avg-rate').textContent = avg.toFixed(1);

    const lowCount = latest.filter(d => d.crime_level === 'Low').length;
    const highCount = latest.filter(d => d.crime_level === 'High').length;
    document.getElementById('w-low-count').textContent = lowCount;
    document.getElementById('w-low-sub').textContent = `out of ${latest.length} states`;

    document.getElementById('si-states').textContent = latest.length;
    document.getElementById('si-years').textContent = maxYear;
    document.getElementById('si-high').textContent = highCount;
    document.getElementById('model-info').classList.remove('hidden');
}

/* Forecast Results table removed — these stubs prevent runtime errors
   in any code paths that still call updateTable / renderTable.        */
function sortTable() { }
function renderTable(data) { State.tableData = data || []; }
function updateTable(data) { renderTable(data); }

/* ════════════════════════════════════════════════════════════════
   REFRESH ALL CHARTS
   ════════════════════════════════════════════════════════════════ */
function refreshAllCharts() {
    const { historicalData, predictedData } = State;
    const sel = State.selectedStates;
    const label = sel.length === 0 ? 'India (All States)' :
        sel.length === 1 ? sel[0] : `${sel.length} States`;

    const histByYear = {}, predByYear = {};
    historicalData.forEach(d => { (histByYear[d.year] = histByYear[d.year] || []).push(d.crime_rate_per_100k); });
    if (predictedData.length) {
        predictedData.forEach(d => { (predByYear[d.year] = predByYear[d.year] || []).push(d.predicted_crime_rate); });
    }
    const avg = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
    const hYears = Object.keys(histByYear).map(Number).sort((a, b) => a - b);
    const pYears = Object.keys(predByYear).map(Number).sort((a, b) => a - b);
    const allYears = [...new Set([...hYears, ...pYears])].sort((a, b) => a - b);
    const hSeries = allYears.map(y => histByYear[y] ? +avg(histByYear[y]).toFixed(2) : null);
    const pSeries = allYears.map(y => predByYear[y] ? +avg(predByYear[y]).toFixed(2) : null);
    buildTrendChart(allYears, hSeries, pSeries, label);

    if (predictedData.length) {
        const maxPredYear = Math.max(...predictedData.map(d => d.year));
        const latest = predictedData.filter(d => d.year === maxPredYear);
        const stateAvg = {};
        latest.forEach(d => (stateAvg[d.state_name] = stateAvg[d.state_name] || []).push(d.predicted_crime_rate));
        const ranked = Object.entries(stateAvg)
            .map(([s, vals]) => ({ state: s, avg: +avg(vals).toFixed(2) }))
            .sort((a, b) => b.avg - a.avg).slice(0, 5);
        buildBarChart(ranked.map(r => r.state), ranked.map(r => r.avg));
        const high = latest.filter(d => d.crime_level === 'High').length;
        const med = latest.filter(d => d.crime_level === 'Medium').length;
        const low = latest.filter(d => d.crime_level === 'Low').length;
        buildRiskChart(high, med, low);
        updateKPIs(predictedData);
        updateMapLayer(latest);
    } else {
        buildBarChart([], []);
        buildRiskChart(0, 0, 0);
        updateMapLayer([]);
    }
    buildFeatureChart(historicalData, sel.length === 1 ? sel[0] : null);
    buildGrowthChart(historicalData);
    updateExportLinks();
}

function updateExportLinks() {
    const qs = buildFilterParams().toString();
    const histLink = document.getElementById('export-csv-btn');
    const predLink = document.getElementById('export-predictions-csv-btn');
    if (histLink) histLink.setAttribute('href', qs ? `/export-csv?${qs}` : '/export-csv');
    if (predLink) predLink.setAttribute('href', qs ? `/export-predictions-csv?${qs}` : '/export-predictions-csv');
}

/* ════════════════════════════════════════════════════════════════
   API CALLS
   ════════════════════════════════════════════════════════════════ */
async function loadHistoricalData(params) {
    try {
        const url = params ? `/api/data/historical?${params}` : '/api/data/historical';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        State.historicalData = data;
        return data;
    } catch (err) {
        console.warn('Historical load failed:', err.message);
        return [];
    }
}

async function loadPredictedData(params) {
    try {
        const url = params ? `/api/data/predicted?${params}` : '/api/data/predicted';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        State.predictedData = data;
        return data;
    } catch (err) {
        console.warn('Predicted load failed:', err.message);
        return [];
    }
}

async function loadStates() {
    try {
        const res = await fetch('/api/states');
        if (!res.ok) return [];
        return await res.json();
    } catch { return []; }
}

async function loadFeatureImportance() {
    try {
        const res = await fetch('/api/feature-importance');
        if (!res.ok) return;
        const data = await res.json();
        State.featureImportance = data.feature_importance || null;
    } catch (_) { State.featureImportance = null; }
}

/* ════════════════════════════════════════════════════════════════
   APPLY FILTERS
   ════════════════════════════════════════════════════════════════ */
async function applyFilters() {
    const params = buildFilterParams();
    showLoadingOverlay('Applying filters…');
    try {
        const [hist, pred] = await Promise.all([
            loadHistoricalData(params),
            loadPredictedData(params),
        ]);
        refreshAllCharts();
        if (hist.length || pred.length) {
            showToast(`Filters applied (${hist.length} hist · ${pred.length} pred records)`, 'info');
        } else {
            showToast('No data matches the selected filters.', 'warning');
        }
    } catch (err) {
        showToast(`Filter error: ${err.message}`, 'error');
    } finally {
        hideLoadingOverlay();
    }
}

/* ════════════════════════════════════════════════════════════════
   FORECAST
   ════════════════════════════════════════════════════════════════ */
async function runForecast() {
    const selYears = parseInt(document.getElementById('years-select').value, 10);
    const sel = State.selectedStates;

    setForecastBtnLoading(true);
    setSideMsg('Calling forecast API…');

    try {
        const params = new URLSearchParams({ years: selYears });
        if (sel.length > 0 && sel.length < State.allStates.length) {
            params.set('states', sel.join(','));
        }

        const res = await fetch(`/predict?${params}`);
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        // Reload fresh from DB with current filters
        const filterParams = buildFilterParams();
        await loadPredictedData(filterParams.toString() || undefined);

        refreshAllCharts();
        setSideMsg(`✅ Forecast done (${selYears}yr)`, 'success');
        showToast(`Forecast generated for ${sel.length === 0 ? 'all states' : sel.join(', ')}!`, 'success');
    } catch (err) {
        setSideMsg(`❌ ${err.message}`, 'error');
        showToast(err.message, 'error');
    } finally {
        setForecastBtnLoading(false);
    }
}

/* ════════════════════════════════════════════════════════════════
   PDF REPORT
   ════════════════════════════════════════════════════════════════ */
async function downloadReport() {
    const sel = State.selectedStates;
    if (sel.length !== 1) {
        showToast('Please select exactly ONE state to generate a PDF report.', 'warning');
        return;
    }
    showToast(`Generating PDF for ${sel[0]}…`, 'info');
    window.open(`/report/${encodeURIComponent(sel[0])}`, '_blank');
}

/* ════════════════════════════════════════════════════════════════
   INIT
   ════════════════════════════════════════════════════════════════ */
async function init() {
    initMap();
    setupMultiSelectUI();
    setupYearFilter();
    await loadFeatureImportance();

    const states = await loadStates();
    if (states.length) initMultiSelect(states);

    showLoadingOverlay('Loading data…');
    try {
        const [hist, pred] = await Promise.all([
            loadHistoricalData(null),
            loadPredictedData(null),
        ]);

        if (pred.length > 0) {
            refreshAllCharts();
            showToast('Dashboard loaded with existing predictions!', 'success');
        } else if (hist.length > 0) {
            // Auto-generate 5-year forecast
            showToast('Auto-generating 5-year forecast…', 'info', 5000);
            setSideMsg('Auto-generating forecast…');
            setForecastBtnLoading(true);
            try {
                const r = await fetch('/predict?years=5');
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                const d = await r.json();
                if (d.error) throw new Error(d.error);
                await loadPredictedData(null);
                if (State.predictedData.length) {
                    refreshAllCharts();
                    setSideMsg('✅ Auto-forecast complete (5yr)', 'success');
                    showToast('5-year forecast auto-generated!', 'success');
                }
            } catch (err) {
                setSideMsg(`⚠️ Auto-forecast failed: ${err.message}`, 'error');
                showToast(`Auto-forecast failed: ${err.message}`, 'warning', 6000);
                buildFeatureChart(hist, null);
            } finally {
                setForecastBtnLoading(false);
            }
        } else {
            showToast('No data found. Go to Home → Generate → Train first.', 'warning', 8000);
        }
    } finally {
        hideLoadingOverlay();
    }
}

document.addEventListener('DOMContentLoaded', init);
