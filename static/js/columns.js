import { typeBadge } from './utils.js';

export async function populateColumnsPage(cols, dtypes, nulls = {}, uniques = {}) {
    const r = await fetch('/api/columns');
    const d = await r.json();
    if (d.error) {
        console.error(d.error);
        document.getElementById('columnsTable').innerHTML = '<div class="text-red">Ошибка загрузки структуры</div>';
        return;
    }

    const columns = d.columns;
    const types   = d.dtypes;
    const nullCnt = d.nulls;
    const uniqCnt = d.uniques;

    let html = `<div class="table-wrap">
        <table>
            <thead><tr><th>#</th><th>Колонка</th><th>Тип</th><th>Пропуски</th><th>Уникальных</th></tr></thead>
            <tbody>`;
    columns.forEach((c, i) => {
        const nullCount = nullCnt[c] || 0;
        html += `<tr>
            <td style="color:var(--text-disabled)">${i+1}</td>
            <td>${c}</td>
            <td>${typeBadge(types[c] || 'text')}</td>
            <td style="color:${nullCount > 0 ? 'var(--danger)' : 'var(--accent2)'}">${nullCount}</td>
            <td>${uniqCnt[c] ?? ''}</td>
        </tr>`;
    });
    html += `</tbody></table></div>`;
    document.getElementById('columnsTable').innerHTML = html;
}