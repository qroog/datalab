import pandas as pd
import numpy as np


def detect_types(df: pd.DataFrame) -> dict:
    result = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_bool_dtype(s):
            result[col] = "boolean"
        elif pd.api.types.is_integer_dtype(s):
            result[col] = "integer"
        elif pd.api.types.is_float_dtype(s):
            result[col] = "float"
        elif pd.api.types.is_datetime64_any_dtype(s):
            result[col] = "datetime"
        else:
            sample = s.dropna().head(100)
            try:
                pd.to_datetime(sample)
                result[col] = "datetime (inferred)"
            except Exception:
                n_unique = s.nunique()
                if n_unique / max(len(s), 1) < 0.05 and n_unique <= 50:
                    result[col] = "categorical"
                else:
                    result[col] = "text"
    return result


def apply_preprocessing(df: pd.DataFrame, ops: list):

    log = []
    df = df.copy()

    for op in ops:
        t = op.get("type")
        col = op.get("column")  
        params = op.get("params", {})

        try:
            if t == "drop_column":
                df.drop(columns=[col], inplace=True)
                log.append(f"Удалена колонка: {col}")

            elif t == "drop_nulls":
                before = len(df)
                subset = [col] if col else None
                df.dropna(subset=subset, inplace=True)
                log.append(f"Удалено строк с пропусками: {before - len(df)}")

            elif t == "fill_mean":
                v = df[col].mean()
                df[col].fillna(v, inplace=True)
                log.append(f"{col}: заполнено средним ({v:.4f})")

            elif t == "fill_median":
                v = df[col].median()
                df[col].fillna(v, inplace=True)
                log.append(f"{col}: заполнено медианой ({v:.4f})")

            elif t == "fill_mode":
                v = df[col].mode()[0]
                df[col].fillna(v, inplace=True)
                log.append(f"{col}: заполнено модой ({v})")

            elif t == "fill_value":
                v = params.get("value", 0)
                df[col].fillna(v, inplace=True)
                log.append(f"{col}: заполнено значением {v}")

            elif t == "cast_int":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                log.append(f"{col}: преобразован в integer")

            elif t == "cast_float":
                df[col] = pd.to_numeric(df[col], errors="coerce")
                log.append(f"{col}: преобразован в float")

            elif t == "cast_datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce")
                log.append(f"{col}: преобразован в datetime")

            elif t == "cast_category":
                df[col] = df[col].astype("category")
                log.append(f"{col}: преобразован в category")

            elif t == "label_encode":
                codes, uniques = pd.factorize(df[col])
                df[col + "_encoded"] = codes
                log.append(f"{col}: label encoding → {col}_encoded ({len(uniques)} категорий)")

            elif t == "one_hot":
                dummies = pd.get_dummies(df[col], prefix=col)
                df = pd.concat([df, dummies], axis=1)
                log.append(f"{col}: one-hot encoding → {list(dummies.columns)}")

            elif t == "normalize_minmax":
                mn, mx = df[col].min(), df[col].max()
                if mx > mn:
                    df[col + "_norm"] = (df[col] - mn) / (mx - mn)
                    log.append(f"{col}: min-max нормализация → {col}_norm")

            elif t == "normalize_zscore":
                mean, std = df[col].mean(), df[col].std()
                if std > 0:
                    df[col + "_zscore"] = (df[col] - mean) / std
                    log.append(f"{col}: z-score стандартизация → {col}_zscore")

            elif t == "remove_outliers_iqr":
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                before = len(df)
                df = df[(df[col] >= Q1 - 1.5 * IQR) & (df[col] <= Q3 + 1.5 * IQR)]
                log.append(f"{col}: удалено выбросов по IQR: {before - len(df)} строк")

            elif t == "rename":
                new_name = params.get("new_name", col + "_renamed")
                df.rename(columns={col: new_name}, inplace=True)
                log.append(f"Переименована: {col} → {new_name}")

            else:
                log.append(f"Неизвестная операция: {t}")

        except Exception as e:
            log.append(f"Ошибка в операции {t} для {col}: {e}")

    return df, log
