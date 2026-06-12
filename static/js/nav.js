const PAGE_TITLES = {
    load:       'Загрузка данных',
    columns:    'Структура данных',
    preprocess: 'Предобработка',
    stats:      'Статистика',
    charts:     'Визуализация',
    ml:         'Обучение ML',
};

export function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${pageId}`).classList.add('active');

    document.querySelectorAll('nav ul li a').forEach(a => {
        a.classList.remove('active');
        if (a.dataset.page === pageId) a.classList.add('active');
    });

    document.getElementById('pageTitle').textContent = PAGE_TITLES[pageId] || pageId;
}

export function initNav() {
    document.querySelectorAll('nav ul li a').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            showPage(link.dataset.page);
        });
    });
}
