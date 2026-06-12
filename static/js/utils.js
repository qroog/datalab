let _toastTimer = null;

export function toast(msg, type = 'info') {
    const el      = document.getElementById('toast');
    const typeEl  = document.getElementById('toastType');
    const msgEl   = document.getElementById('toastMsg');
    el.className  = type;
    typeEl.textContent =
        type === 'error'   ? 'Ошибка'     :
        type === 'success' ? 'Успешно'    : 'Информация';
    msgEl.textContent = msg;
    el.classList.add('show');
    if (_toastTimer) clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => el.classList.remove('show'), 3500);
}

export function setLoading(btn, isLoading) {
    if (isLoading) {
        btn._originalText = btn.innerHTML;
        btn.disabled      = true;
        btn.innerHTML     = '<span class="spinner"></span> Загрузка...';
    } else {
        btn.disabled  = false;
        btn.innerHTML = btn._originalText || btn.innerHTML;
    }
}

export function typeBadge(t) {
    const map = {
        integer:    'blue',
        float:      'blue',
        boolean:    'red',
        categorical:'green',
        datetime:   'yellow',
        text:       'gray',
    };
    const key = Object.keys(map).find(k => t && t.toLowerCase().startsWith(k)) || 'gray';
    return `<span class="tag tag-${map[key]}">${t}</span>`;
}

export function fmt(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'number')
        return Math.abs(v) > 9999
            ? v.toLocaleString('ru', { maximumFractionDigits: 0 })
            : v.toFixed(4).replace(/\.?0+$/, '');
    return v;
}

export function applyPlotlyTheme(fig) {
    fig.layout = fig.layout || {};
    fig.layout.paper_bgcolor = 'rgba(0,0,0,0)';
    fig.layout.plot_bgcolor  = '#f8f8f8';
    fig.layout.font = { color: '#161616', family: 'IBM Plex Sans, sans-serif', size: 12 };
    return fig;
}
