import { toast, setLoading, typeBadge } from './utils.js';
import { updateState }                  from './state.js';

let pendingOps = [];

export function populatePreprocessCols(cols) {
    const sel = document.getElementById('ppCol');
    sel.innerHTML =
        '<option value="">— все —</option>' +
        cols.map(c => `<option>${c}</option>`).join('');
}

function updatePPExtra() {
    const op = document.getElementById('ppOp').value;
    let html = '';
    if (op === 'fill_value')
        html = `<div class="form-group"><label class="form-label">Значение</label>
                    <input type="text" id="ppVal" placeholder="0"/></div>`;
    if (op === 'rename')
        html = `<div class="form-group"><label class="form-label">Новое имя</label>
                    <input type="text" id="ppNewName"/></div>`;
    document.getElementById('ppExtra').innerHTML = html;
}

function addOp() {
    const col    = document.getElementById('ppCol').value;
    const op     = document.getElementById('ppOp').value;
    const params = {};
    const valEl  = document.getElementById('ppVal');
    const nameEl = document.getElementById('ppNewName');
    if (valEl)  params.value    = valEl.value;
    if (nameEl) params.new_name = nameEl.value;

    pendingOps.push({ type: op, column: col || null, params });

    document.getElementById('opsCard').style.display = '';
    const list = document.getElementById('opsList');
    const item = document.createElement('div');
    item.className   = 'op-item';
    const idx        = pendingOps.length - 1;
    item.innerHTML   = `
        <span><code>${op}</code> ${col ? `→ <strong>${col}</strong>` : '(все колонки)'}</span>
        <button class="btn btn-secondary btn-sm" data-idx="${idx}">Удалить</button>`;
    item.querySelector('button').addEventListener('click', () => {
        pendingOps.splice(idx, 1);
        item.remove();
        if (!pendingOps.length) document.getElementById('opsCard').style.display = 'none';
    });
    list.appendChild(item);
}

export async function runPreprocess(onDone) {
    if (!pendingOps.length) return;
    const applyBtn = document.getElementById('applyPreprocessBtn');
    setLoading(applyBtn, true);

    try {
        const r = await fetch('/api/preprocess', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ ops: pendingOps }),
        });
        const d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }

        updateState(d);
        document.getElementById('dataInfo').textContent = `${d.rows.toLocaleString()} × ${d.cols}`;
        document.getElementById('ppLogCard').style.display = '';
        document.getElementById('ppLog').innerHTML = d.log.map(l => `> ${l}`).join('\n');

        pendingOps = [];
        document.getElementById('opsList').innerHTML = '';
        document.getElementById('opsCard').style.display = 'none';

        onDone?.(d);
        toast('Предобработка применена', 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(applyBtn, false);
    }
}

export async function resetData(onDone) {
    const resetBtn = document.getElementById('resetDataBtn');
    setLoading(resetBtn, true);

    try {
        const r = await fetch('/api/reset', { method: 'POST' });
        const d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }
        updateState(d);
        onDone?.(d);
        toast('Данные сброшены к исходному состоянию', 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(resetBtn, false);
    }
}

export async function exportData(format) {
    const r = await fetch(`/api/export?format=${format}`);
    if (r.status === 400) {
        const err = await r.json();
        toast(err.error, 'error');
        return;
    }
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `data.${format === 'csv' ? 'csv' : 'parquet'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast(`Экспорт ${format.toUpperCase()} завершён`, 'success');
}

export function initPreprocess(onDone) {
    document.getElementById('ppOp').addEventListener('change', updatePPExtra);
    document.getElementById('addOpBtn').addEventListener('click', addOp);
    document.getElementById('applyPreprocessBtn').addEventListener('click', () => runPreprocess(onDone));
    document.getElementById('resetDataBtn').addEventListener('click',      () => resetData(onDone));
    document.getElementById('exportCsvBtn').addEventListener('click',      () => exportData('csv'));
    document.getElementById('exportParquetBtn').addEventListener('click',  () => exportData('parquet'));
}   