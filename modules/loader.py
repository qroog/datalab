import pandas as pd


def load_file(path: str, ext: str, sep: str = ",", nrows=None):
    """Load CSV, XLSX, Parquet or JSON into a DataFrame."""
    try:
        if ext == "csv":
            df = pd.read_csv(path, sep=sep, nrows=nrows, low_memory=False,
                             encoding_errors="replace")
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(path, nrows=nrows)
        elif ext == "parquet":
            df = pd.read_parquet(path)
            if nrows:
                df = df.head(nrows)
        elif ext == "json":
            df = pd.read_json(path, nrows=nrows)
        else:
            return None, f"Неподдерживаемый формат: {ext}"

        df.columns = [str(c).strip() for c in df.columns]
        return df, None
    except Exception as e:
        return None, str(e)


def connect_db(url: str, query: str):
    """Connect to a SQLAlchemy-compatible database and run a query."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        return df, None
    except Exception as e:
        return None, str(e)
