import pandas as pd
import numpy as np
from scipy import stats as scipy_stats


def safe_val(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    return v


def compute_stats(df: pd.DataFrame, cols: list) -> dict:
    result = {}

    for col in cols:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        col_stat = {"name": col, "count": int(len(s)), "nulls": int(df[col].isnull().sum())}

        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            col_stat.update({
                "type": "numeric",
                "mean":   safe_val(s.mean()),
                "median": safe_val(s.median()),
                "std":    safe_val(s.std()),
                "min":    safe_val(s.min()),
                "max":    safe_val(s.max()),
                "q25":    safe_val(desc["25%"]),
                "q75":    safe_val(desc["75%"]),
                "skewness": safe_val(float(scipy_stats.skew(s))),
                "kurtosis": safe_val(float(scipy_stats.kurtosis(s))),
            })
            # Normality test (Shapiro for ≤5000 samples)
            sample = s if len(s) <= 5000 else s.sample(5000, random_state=42)
            try:
                stat, p = scipy_stats.shapiro(sample)
                col_stat["normality_p"] = safe_val(float(p))
                col_stat["is_normal"] = bool(p > 0.05)
            except Exception:
                col_stat["normality_p"] = None
                col_stat["is_normal"] = None

        else:
            vc = s.value_counts()
            col_stat.update({
                "type": "categorical",
                "unique": int(s.nunique()),
                "top_values": {str(k): int(v) for k, v in vc.head(10).items()},
                "mode": str(s.mode()[0]) if len(s) > 0 else None,
            })

        result[col] = col_stat

    num_cols = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        result["__correlation__"] = {
            "columns": num_cols,
            "matrix": [[safe_val(v) for v in row] for row in corr.values],
        }

    return result
