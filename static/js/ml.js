import { toast, setLoading, typeBadge, applyPlotlyTheme } from './utils.js';
import { state } from './state.js';

export function initMLSelectors(cols, dtypes) {
    const targetSelect    = document.getElementById('mlTarget');
    targetSelect.innerHTML = cols.map(c => `<option value="${c}">${c}</option>`).join('');
    updateFeatureList();
}

export function updateFeatureList() {
    const target    = document.getElementById('mlTarget').value;
    const allCols   = state.columns || [];
    const dtypes    = state.dtypes  || {};
    const container = document.getElementById('mlFeatureList');

    container.innerHTML = allCols
        .filter(c => c !== target)
        .map(c => `
            <label class="col-check-item">
                <input type="checkbox" class="ml-feat-cb" value="${c}"/>
                <span>${c}</span> ${typeBadge(dtypes[c] || 'text')}
            </label>
        `).join('');
}

function selectAllFeatures() {
    document.querySelectorAll('.ml-feat-cb').forEach(cb => cb.checked = true);
}
function clearFeatures() {
    document.querySelectorAll('.ml-feat-cb').forEach(cb => cb.checked = false);
}

function updateMLFields() {
    const m = document.getElementById('mlModel').value;
    document.getElementById('mlTargetGroup').style.display   = m === 'kmeans' ? 'none' : '';
    document.getElementById('mlClustersGroup').style.display = m === 'kmeans' ? ''     : 'none';
    updateHyperparamsVisibility();
}

function updateHyperparamsVisibility() {
    const model   = document.getElementById('mlModel').value;
    const block   = document.getElementById('hyperparamsBlock');
    const showFor = [
        'random_forest_clf', 'random_forest_reg',
        'logistic', 'decision_tree_clf', 'decision_tree_reg', 'gradient_boost',
    ];

    block.style.display = showFor.includes(model) ? 'block' : 'none';

    const isLogistic = model === 'logistic';
    document.getElementById('hp_c_group').style.display     = isLogistic ? 'block' : 'none';
    document.getElementById('hp_n_group').style.display     = isLogistic ? 'none'  : 'block';
    document.getElementById('hp_depth_group').style.display = isLogistic ? 'none'  : 'block';
}

async function trainModel() {
    const model     = document.getElementById('mlModel').value;
    const target    = document.getElementById('mlTarget').value;
    const features  = [...document.querySelectorAll('.ml-feat-cb:checked')].map(cb => cb.value);
    const testSize  = parseInt(document.getElementById('mlTestSize').value) / 100;
    const nClusters = parseInt(document.getElementById('mlClusters').value);
    const hyperparams = {
        n_estimators: parseInt(document.getElementById('hp_n_estimators').value),
        max_depth:    document.getElementById('hp_max_depth').value
                          ? parseInt(document.getElementById('hp_max_depth').value)
                          : null,
        C: parseFloat(document.getElementById('hp_c').value),
    };

    if (model !== 'kmeans') {
        if (!target)          { toast('Выберите целевую переменную', 'error'); return; }
        if (!features.length) { toast('Выберите хотя бы один признак', 'error'); return; }
    }

    const statusEl   = document.getElementById('mlStatus');
    const statusText = document.getElementById('mlStatusText');
    statusEl.style.display = '';
    statusText.textContent  = 'Обучение модели...';
    statusText.style.color  = 'var(--text-secondary)';
    document.getElementById('mlMetrics').innerHTML = '';
    document.getElementById('mlCharts').innerHTML  = '';

    const trainBtn = document.getElementById('trainModelBtn');
    setLoading(trainBtn, true);

    try {
        const r = await fetch('/api/train', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                model, target, features,
                test_size:  testSize,
                n_clusters: nClusters,
                hyperparams,
            }),
        });
        const d = await r.json();

        if (d.error) {
            statusText.textContent  = d.error;
            statusText.style.color  = 'var(--danger)';
            return;
        }

        statusText.innerHTML   = `<span style="color:var(--accent2)"></span> 
            Модель: <strong>${d.model}</strong>
            &nbsp;·&nbsp; train=${d.samples_train}
            &nbsp;·&nbsp; test=${d.samples_test}`;
        statusText.style.color = 'var(--text)';

        if (d.warning) {
            statusText.innerHTML += `<br><span style="color:var(--warning)">⚠ ${d.warning}</span>`;
        }

        const metrics    = d.metrics || {};
        const metricsHtml = Object.entries(metrics)
            .filter(([, v]) => v !== null)
            .map(([k, v]) =>
                `<div class="metric-tile">
                    <div class="mt-label">${k}</div>
                    <div class="mt-value">${typeof v === 'number' ? v.toFixed(4) : v}</div>
                </div>`
            ).join('');

        document.getElementById('mlMetrics').innerHTML = metricsHtml
            ? `<div class="metrics-row" style="margin-top:16px;margin-bottom:0;">${metricsHtml}</div>`
            : '';

        const chartsDiv = document.getElementById('mlCharts');
        chartsDiv.innerHTML = '';

        for (const [name, json] of Object.entries(d.charts || {})) {
            const fig = applyPlotlyTheme(JSON.parse(json));

            const wrapper  = document.createElement('div');
            wrapper.className  = 'panel';
            wrapper.style.marginTop = '16px';

            const titleBar = document.createElement('div');
            titleBar.className = 'panel-header';
            titleBar.innerHTML = `<span class="panel-title">${name.replace(/_/g, ' ')}</span>`;

            const inner        = document.createElement('div');
            inner.style.height = '380px';

            wrapper.appendChild(titleBar);
            wrapper.appendChild(inner);
            chartsDiv.appendChild(wrapper);
            Plotly.newPlot(inner, fig.data, fig.layout, { responsive: true });
        }

        toast('Модель обучена!', 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(trainBtn, false);
    }
}

async function saveModel() {
    const name = document.getElementById('modelName').value.trim();
    if (!name) { toast('Введите имя модели', 'error'); return; }

    const saveBtn = document.getElementById('saveModelBtn');
    setLoading(saveBtn, true);

    try {
        const r = await fetch('/api/save_model', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ name }),
        });
        const d = await r.json();
        if (d.error) toast(d.error, 'error');
        else         toast(d.message, 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(saveBtn, false);
    }
}

async function loadModel() {
    const name = document.getElementById('modelName').value.trim();
    if (!name) { toast('Введите имя модели', 'error'); return; }

    const loadBtn = document.getElementById('loadModelBtn');
    setLoading(loadBtn, true);

    try {
        const r = await fetch('/api/load_model', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ name }),
        });
        const d = await r.json();
        if (d.error) toast(d.error, 'error');
        else         toast(`Модель ${name} загружена`, 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(loadBtn, false);
    }
}

export function initML() {
    document.getElementById('mlModel').addEventListener('change',    updateMLFields);
    document.getElementById('mlTarget').addEventListener('change',   updateFeatureList);
    document.getElementById('selectAllFeaturesBtn').addEventListener('click', selectAllFeatures);
    document.getElementById('clearFeaturesBtn').addEventListener('click',     clearFeatures);
    document.getElementById('trainModelBtn').addEventListener('click',        trainModel);
    document.getElementById('saveModelBtn').addEventListener('click',         saveModel);
    document.getElementById('loadModelBtn').addEventListener('click',         loadModel);

    updateMLFields();
    updateHyperparamsVisibility();
}
