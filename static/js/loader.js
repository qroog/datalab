import { toast, setLoading, typeBadge } from './utils.js';
import { updateState }                  from './state.js';

let _onDataLoaded = null;
export function setOnDataLoaded(fn) { _onDataLoaded = fn; }

export function renderPreview(rows, cols, dtypes) {
    let html = '<table><thead><tr>';
    cols.forEach(c => {
        html += `<th>${c}<br/>${typeBadge(dtypes[c] || 'text')}</th>`;
    });
    html += '</tr></thead><tbody>';

    rows.forEach(row => {
        html += '<tr>';
        cols.forEach(c => {
            const v      = row[c];
            const isNull = v === null || v === undefined || v === '';
            const display = isNull
                ? '<span class="td-null">null</span>'
                : String(v).replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html += `<td title="${isNull ? 'null' : v}">${display}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    document.getElementById('previewTable').innerHTML = html;
    document.getElementById('previewCard').style.display = '';
}

export async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files[0]) return;

    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    fd.append('sep',   document.getElementById('csvSep').value);
    fd.append('nrows', document.getElementById('nrows').value || '');

    const uploadBtn = document.getElementById('uploadBtn');
    setLoading(uploadBtn, true);
    toast('Загрузка файла...');

    try {
        const r = await fetch('/api/upload', { method: 'POST', body: fd });
        const d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }
        updateState(d);
        if (d.preview) renderPreview(d.preview, d.columns, d.dtypes);
        _onDataLoaded?.(d);
        toast(`Загружено: ${d.rows.toLocaleString()} строк, ${d.cols} колонок`, 'success');
    } catch (e) {
        toast('Ошибка сети: ' + e, 'error');
    } finally {
        setLoading(uploadBtn, false);
    }
}

export async function connectDB() {
    const url        = document.getElementById('dbUrl').value;
    const query      = document.getElementById('dbQuery').value;
    const connectBtn = document.getElementById('connectDbBtn');
    setLoading(connectBtn, true);
    toast('Подключение...');

    try {
        const r = await fetch('/api/connect_db', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ url, query }),
        });
        const d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }
        document.getElementById('dbModal').classList.remove('show');
        updateState(d);
        _onDataLoaded?.(d);
        toast('БД подключена!', 'success');
    } catch (e) {
        toast('Ошибка: ' + e, 'error');
    } finally {
        setLoading(connectBtn, false);
    }
}

export function initLoader() {
    const dropZone = document.getElementById('dropZone');
    dropZone.addEventListener('click',     () => document.getElementById('fileInput').click());
    dropZone.addEventListener('dragover',  e  => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) {
            document.getElementById('fileInput').files = e.dataTransfer.files;
            uploadFile();
        }
    });

    document.getElementById('fileInput').addEventListener('change', uploadFile);
    document.getElementById('uploadBtn').addEventListener('click',  uploadFile);

    document.getElementById('openDbModalBtn').addEventListener('click',
        () => document.getElementById('dbModal').classList.add('show'));
    document.getElementById('closeDbModalBtn').addEventListener('click',
        () => document.getElementById('dbModal').classList.remove('show'));
    document.getElementById('cancelDbModalBtn').addEventListener('click',
        () => document.getElementById('dbModal').classList.remove('show'));
    document.getElementById('connectDbBtn').addEventListener('click', connectDB);
}
