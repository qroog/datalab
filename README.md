# DataLab 

**Доступ:** [http://45.151.102.35](http://45.151.102.35)

**Вмдео** https://drive.google.com/file/d/1YP1PVocymVbzCKABOruu5NZIZpk5e9de/view?usp=sharing 

Веб-приложение для загрузки, анализа, визуализации и машинного обучения на данных.

## Стек

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.11, Flask 3, Gunicorn |
| Данные | pandas, pyarrow, openpyxl |
| Статистика | scipy, numpy |
| ML | scikit-learn |
| Визуализация | Plotly |
| БД | SQLAlchemy |
| Reverse proxy | Nginx |
| Контейнеризация | Docker, Docker Compose |

## Функциональность

- **Загрузка** CSV, XLSX, Parquet, JSON — до 500 МБ
- **Подключение к БД** (PostgreSQL, MySQL, SQLite)
- **Анализ колонок**: типы, пропуски, уникальные значения
- **Предобработка**: заполнение пропусков, кодирование, нормализация, удаление выбросов
- **Статистика**: среднее, медиана, квартили, асимметрия, тест нормальности, матрица корреляции
- **Графики** (drag & drop): scatter, line, bar, histogram, box, violin, pie, density, heatmap, scatter matrix, parallel coordinates
- **ML**: Random Forest, Logistic Regression, Decision Tree, Gradient Boosting, Linear Regression, K‑Means. Метрики, матрица ошибок, важность признаков, elbow chart.
