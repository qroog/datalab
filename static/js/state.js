export const state = {
    columns: [],
    dtypes:  {},
    rows:    0,
    cols:    0,
};

export function updateState(d) {
    state.columns = d.columns || [];
    state.dtypes  = d.dtypes  || {};
    state.rows    = d.rows    || 0;
    state.cols    = d.cols    || 0;
}
