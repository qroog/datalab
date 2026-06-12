import { toast, setLoading, typeBadge, applyPlotlyTheme } from './utils.js';

const axisValues = { x: null, y: null, color: null };

export function populateColPalette(cols, dtypes) {
    const el = document.getElementById('colPalette');
    el.innerHTML = cols.map(c => `
        <div class="draggable-col" draggable="true" data-col="${c}">
            ${typeBadge(dtypes[c] || 'text')} <span>${c}</span>
        </div>
    `).join('');

    el.querySelectorAll('.draggable-col').forEach(item => {
        item.addEventListener('dragstart', e => {
            e.dataTransfer.setData('col', item.dataset.col);
        });
    });
}

function onDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('over');
}
function onDragLeave(e) {
    e.currentTarget.classList.remove('over');
}
function onDrop(e, zone) {
    e.preventDefault();
    zone.classList.remove('over');
    const col  = e.dataTransfer.getData('col');
    const axis = zone.dataset.axis;
    if (!['x', 'y', 'color'].includes(axis)) return;

    axisValues[axis] = col;
    zone.querySelectorAll('.drop-tag').forEach(t => t.remove());

    const tag      = document.createElement('span');
    tag.className  = 'drop-tag';
    tag.innerHTML  = `${col} <span class="rm">✕</span>`;
    tag.querySelector('.rm').addEventListener('click', () => clearAxis(axis, tag, zone));

    const hint = zone.querySelector('span:not(.drop-tag)');
    if (hint) hint.style.display = 'none';
    zone.appendChild(tag);
}

function clearAxis(axis, tagEl, zone) {
    axisValues[axis] = null;
    tagEl.remove();
    const hint = zone.querySelector('span');
    if (hint) hint.style.display = '';
}

function updateChartFields() {
    const t = document.getElementById('chartType').value;
    const hideXFor    = ['heatmap', 'parallel', 'scatter_matrix'];
    const hideYFor    = ['histogram', 'pie', 'density', 'heatmap', 'parallel', 'scatter_matrix'];
    const showNbins   = ['histogram', 'density'];
    const showAgg     = ['scatter', 'line', 'bar', 'box', 'violin', 'pie'];

    document.getElementById('axisX').style.display     = hideXFor.includes(t)  ? 'none' : '';
    document.getElementById('axisY').style.display     = hideYFor.includes(t)  ? 'none' : '';
    document.getElementById('nbinsGroup').style.display = showNbins.includes(t) ? ''     : 'none';
    document.getElementById('aggGroup').style.display   = showAgg.includes(t)   ? ''     : 'none';
}

async function buildChart() {
    const chartType = document.getElementById('chartType').value;

    const rawAgg = document.getElementById('chartAggregation').value;
    const aggregation = rawAgg && rawAgg !== '' ? rawAgg : 'none';

    const colorVal = chartType === 'pie' ? null : axisValues.color;

    const params = {
        type:        chartType,
        x:           axisValues.x,
        y:           axisValues.y,
        color:       colorVal,
        aggregation: aggregation,
        nbins:       parseInt(document.getElementById('nbins').value) || 30,
    };

    const chartBtn = document.getElementById('buildChartBtn');
    setLoading(chartBtn, true);
    toast('Строим график...');

    try {
        const r = await fetch('/api/chart', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(params),
        });
        const d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }

        const fig = applyPlotlyTheme(JSON.parse(d.chart));
        fig.layout.colorway = ['#0f62fe', '#198038', '#b28600', '#da1e28', '#6929c4', '#005d5d'];
        Plotly.newPlot('chartDiv', fig.data, fig.layout, { responsive: true });
        const queryEl = document.getElementById('chartQuery');
        if (queryEl) queryEl.textContent = d.sql_query || 'График построен';
        toast('Готово', 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(chartBtn, false);
    }
}

export function initCharts() {
    document.getElementById('chartType').addEventListener('change', updateChartFields);
    document.getElementById('buildChartBtn').addEventListener('click', buildChart);

    ['dropX', 'dropY', 'dropColor'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('dragover',  onDragOver);
        el.addEventListener('dragleave', onDragLeave);
        el.addEventListener('drop',      e => onDrop(e, el));
    });

    updateChartFields();
}