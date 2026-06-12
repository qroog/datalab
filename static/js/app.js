import { initNav }               from './nav.js';
import { initLoader, renderPreview, setOnDataLoaded } from './loader.js';
import { populateColumnsPage }   from './columns.js';
import { populatePreprocessCols, initPreprocess } from './preprocess.js';
import { populateStatsCols, initStats }           from './stats.js';
import { populateColPalette, initCharts }         from './charts.js';
import { initMLSelectors, initML }                from './ml.js';
import { updateState }                            from './state.js';

function onDataLoaded(d) {
    updateState(d);

    document.getElementById('dataInfo').textContent      = `${d.rows.toLocaleString()} × ${d.cols}`;
    document.getElementById('navDataStatus').textContent = `${d.rows.toLocaleString()} строк · ${d.cols} кол.`;

    populateColumnsPage(d.columns, d.dtypes, d.nulls || {}, d.uniques || {});
    populatePreprocessCols(d.columns);
    populateStatsCols(d.columns, d.dtypes);
    populateColPalette(d.columns, d.dtypes);
    initMLSelectors(d.columns, d.dtypes);
}

document.addEventListener('DOMContentLoaded', () => {
    setOnDataLoaded(onDataLoaded);

    initNav();
    initLoader();
    initPreprocess(onDataLoaded);   
    initStats();
    initCharts();
    initML();
});