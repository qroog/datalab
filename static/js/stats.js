import { toast, setLoading, typeBadge, fmt, applyPlotlyTheme } from './utils.js';

export function populateStatsCols(cols, dtypes) {
    const el = document.getElementById('statsColList');
    el.innerHTML = cols.map(c => `
        <label class="col-check-item">
            <input type="checkbox" class="stats-col-cb" value="${c}" checked/>
            <span>${c}</span> ${typeBadge(dtypes[c] || 'text')}
        </label>
    `).join('');
}

function selectAllStatsCols() {
    document.querySelectorAll('.stats-col-cb').forEach(cb => cb.checked = true);
}
function clearStatsCols() {
    document.querySelectorAll('.stats-col-cb').forEach(cb => cb.checked = false);
}

async function runStats() {
    const cols = [...document.querySelectorAll('.stats-col-cb:checked')].map(cb => cb.value);
    if (!cols.length) { toast('Выберите хотя бы одну колонку', 'error'); return; }

    const statsBtn = document.getElementById('runStatsBtn');
    setLoading(statsBtn, true);
    toast('Вычисление статистик...');

    try {
        const r = await fetch('/api/stats', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ columns: cols }),
        });
        const d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }
        renderStats(d);
        toast('Готово', 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(statsBtn, false);
    }
}

function renderStats(d) {
    const container = document.getElementById('statsResult');
    let html = '';

    for (const [col, s] of Object.entries(d)) {
        if (col === '__correlation__') continue;

        html += `<div class="panel" style="margin-bottom:16px;">
            <div class="panel-header"><span class="panel-title">${col}</span> ${typeBadge(s.type)}</div>
            <div class="panel-body" style="padding:0;">`;

        if (s.type === 'numeric') {
            const normalColor = s.is_normal ? 'var(--accent2)' : 'var(--danger)';
            const normalLabel = s.is_normal === null ? '—' : s.is_normal ? 'Да' : 'Нет';
            const nullColor   = s.nulls > 0 ? 'var(--danger)' : 'var(--text)';

            html += `<div class="stat-grid">
                <div class="stat-tile"><div class="st-label">Среднее</div><div class="st-value">${fmt(s.mean)}</div></div>
                <div class="stat-tile"><div class="st-label">Медиана</div><div class="st-value">${fmt(s.median)}</div></div>
                <div class="stat-tile"><div class="st-label">Std</div><div class="st-value">${fmt(s.std)}</div></div>
                <div class="stat-tile"><div class="st-label">Min</div><div class="st-value">${fmt(s.min)}</div></div>
                <div class="stat-tile"><div class="st-label">Max</div><div class="st-value">${fmt(s.max)}</div></div>
                <div class="stat-tile"><div class="st-label">Q25 / Q75</div><div class="st-value">${fmt(s.q25)} / ${fmt(s.q75)}</div></div>
                <div class="stat-tile">
                    <div class="st-label">Асимметрия</div>
                    <div class="st-value">${fmt(s.skewness)}</div>
                    <div class="st-sub">${Math.abs(s.skewness || 0) < 0.5 ? 'симметрично' : 'асимметрично'}</div>
                </div>
                <div class="stat-tile"><div class="st-label">Эксцесс</div><div class="st-value">${fmt(s.kurtosis)}</div></div>
                <div class="stat-tile">
                    <div class="st-label">Норм. распр.</div>
                    <div class="st-value" style="color:${normalColor}">${normalLabel}</div>
                    <div class="st-sub">p=${fmt(s.normality_p)}</div>
                </div>
                <div class="stat-tile">
                    <div class="st-label">Пропуски</div>
                    <div class="st-value" style="color:${nullColor}">${s.nulls}</div>
                </div>
                <div class="stat-tile" style="grid-column:span 2;display:flex;justify-content:space-between;align-items:center;">
                    <span class="st-label">Гистограмма</span>
                    <button class="btn btn-sm btn-secondary hist-btn" data-col="${col}">Показать</button>
                </div>
            </div>`;
        } else {
            const topItems = Object.entries(s.top_values || {}).slice(0, 8).map(([k, v]) =>
                `<div style="display:flex;justify-content:space-between;padding:8px 16px;
                             border-bottom:1px solid var(--border);font-size:13px;">
                    <span class="text-mono">${k}</span>
                    <span class="tag tag-blue">${v.toLocaleString()}</span>
                </div>`
            ).join('');

            html += `<div class="stat-grid">
                <div class="stat-tile"><div class="st-label">Уникальных</div><div class="st-value">${s.unique}</div></div>
                <div class="stat-tile">
                    <div class="st-label">Пропуски</div>
                    <div class="st-value" style="color:${s.nulls > 0 ? 'var(--danger)' : 'var(--text)'}">${s.nulls}</div>
                </div>
                <div class="stat-tile"><div class="st-label">Мода</div><div class="st-value" style="font-size:14px;">${s.mode || '—'}</div></div>
            </div>
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.06em;color:var(--text-secondary);padding:12px 16px 4px;">
                Топ-8 значений
            </div>
            ${topItems}`;
        }

        html += '</div></div>';
    }

    if (d.__correlation__) {
        const corr = d.__correlation__;
        html += `<div class="panel">
            <div class="panel-header"><span class="panel-title">Матрица корреляции</span></div>
            <div class="panel-body"><div id="corrHeatmap" style="height:420px;"></div></div>
        </div>`;
        container.innerHTML = html;

        Plotly.newPlot('corrHeatmap', [{
            type:          'heatmap',
            z:             corr.matrix,
            x:             corr.columns,
            y:             corr.columns,
            colorscale:    'RdBu',
            zmid:          0,
            text:          corr.matrix.map(row => row.map(v => v !== null ? v.toFixed(2) : '')),
            texttemplate:  '%{text}',
        }], {
            margin:         { l: 120, r: 20, t: 10, b: 120 },
            paper_bgcolor:  'rgba(0,0,0,0)',
            plot_bgcolor:   '#f8f8f8',
            font:           { family: 'IBM Plex Mono, monospace', size: 11 },
        });
    } else {
        container.innerHTML = html;
    }

    container.querySelectorAll('.hist-btn').forEach(btn => {
        btn.addEventListener('click', () => showHistogram(btn.dataset.col));
    });
}

async function showHistogram(col) {
    const modal     = document.getElementById('histModal');
    const container = document.getElementById('histChart');
    if (!modal || !container) { toast('Модальное окно не найдено', 'error'); return; }

    modal.classList.add('show');
    container.innerHTML = '<div class="spinner" style="margin:40px auto;"></div>';

    try {
        const r = await fetch('/api/histogram', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ column: col }),
        });
        const d = await r.json();
        if (d.error) {
            container.innerHTML = `<div class="text-red" style="padding:20px;">${d.error}</div>`;
            return;
        }
        const fig = applyPlotlyTheme(JSON.parse(d.chart));
        Plotly.newPlot(container, fig.data, fig.layout, { responsive: true });
    } catch (e) {
        container.innerHTML = `<div class="text-red" style="padding:20px;">Ошибка: ${e}</div>`;
    }
}

export function initStats() {
    document.getElementById('selectAllStatsBtn').addEventListener('click', selectAllStatsCols);
    document.getElementById('clearStatsBtn').addEventListener('click',     clearStatsCols);
    document.getElementById('runStatsBtn').addEventListener('click',       runStats);

    const histModal = document.getElementById('histModal');
    if (histModal) {
        histModal.addEventListener('click', e => {
            if (e.target === histModal) histModal.classList.remove('show');
        });
    }
}
