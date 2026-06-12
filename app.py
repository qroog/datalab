from flask import Flask, render_template, request, jsonify, session, Response
import os
import uuid
import json
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from threading import Lock
from modules.loader import load_file, connect_db
from modules.preprocessor import detect_types, apply_preprocessing
from modules.stats import compute_stats
from modules.plotter import build_chart
from modules.ml_engine import train_model
import concurrent.futures
import re

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

os.makedirs("uploads", exist_ok=True)
os.makedirs("models", exist_ok=True)

DATASETS = {}
ORIGINALS = {}
MODELS = {}
ACCESS_TIMES = {}
CLEANUP_LOCK = Lock()
SESSION_TIMEOUT_MINUTES = 60

def run_with_timeout(func, timeout, *args, **kwargs):
    """Запускает функцию с таймаутом. Возвращает результат или выбрасывает TimeoutError."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Operation exceeded {timeout} seconds")

def cleanup_old_sessions():
    now = datetime.now()
    with CLEANUP_LOCK:
        expired = [sid for sid, ts in ACCESS_TIMES.items() if now - ts > timedelta(minutes=SESSION_TIMEOUT_MINUTES)]
        for sid in expired:
            DATASETS.pop(sid, None)
            ORIGINALS.pop(sid, None)
            MODELS.pop(sid, None)
            ACCESS_TIMES.pop(sid, None)

def touch_session(sid):
    if sid:
        ACCESS_TIMES[sid] = datetime.now()
        cleanup_old_sessions()

def get_df():
    sid = session.get("sid")
    if sid and sid in DATASETS:
        touch_session(sid)
        return DATASETS[sid]
    return None

def is_safe_sql(query: str) -> bool:
    """Проверяет, что запрос содержит только SELECT и не содержит модифицирующих команд."""
    query_upper = query.upper().strip()
    dangerous = re.compile(r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH)\b', re.IGNORECASE)
    if dangerous.search(query_upper):
        return False
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        return False
    return True

@app.route("/")
def index():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    touch_session(session["sid"])
    return render_template("index.html")

@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls", "parquet", "json"):
        return jsonify({"error": "Unsupported file format"}), 400

    tmp_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4()}.{ext}")
    f.save(tmp_path)

    sep = request.form.get("sep", ",")
    nrows = request.form.get("nrows")
    nrows = int(nrows) if nrows else None

    try:
        df, err = run_with_timeout(load_file, 15, tmp_path, ext, sep=sep, nrows=nrows)
    except TimeoutError:
        os.unlink(tmp_path)
        return jsonify({"error": "File loading timeout (>15 sec). Try smaller file."}), 408
    finally:
        os.unlink(tmp_path)

    if err:
        return jsonify({"error": err}), 400

    sid = session["sid"]
    DATASETS[sid] = df
    ORIGINALS[sid] = df.copy()
    touch_session(sid)

    return jsonify({
        "rows": len(df),
        "cols": len(df.columns),
        "columns": df.columns.tolist(),
        "dtypes": detect_types(df),
        "preview": df.head(10).fillna("").to_dict(orient="records"),
    })

@app.route("/api/connect_db", methods=["POST"])
def connect_database():
    data = request.json
    url = data.get("url", "")
    query = data.get("query", "")
    try:
        df, err = run_with_timeout(connect_db, 15, url, query)
    except TimeoutError:
        return jsonify({"error": "Database query timeout (>15 sec)"}), 408
    if err:
        return jsonify({"error": err}), 400
    sid = session["sid"]
    DATASETS[sid] = df
    ORIGINALS[sid] = df.copy()
    touch_session(sid)
    return jsonify({
        "rows": len(df),
        "cols": len(df.columns),
        "columns": df.columns.tolist(),
        "dtypes": detect_types(df),
        "preview": df.head(10).fillna("").to_dict(orient="records"),
    })

@app.route("/api/columns")
def columns():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    return jsonify({
        "columns": df.columns.tolist(),
        "dtypes": detect_types(df),
        "nulls": df.isnull().sum().to_dict(),
        "uniques": {c: int(df[c].nunique()) for c in df.columns},
    })

@app.route("/api/preprocess", methods=["POST"])
def preprocess():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    ops = request.json.get("ops", [])
    df, log = apply_preprocessing(df, ops)
    sid = session["sid"]
    DATASETS[sid] = df
    touch_session(sid)
    return jsonify({
        "rows": len(df),
        "cols": len(df.columns),
        "columns": df.columns.tolist(),
        "dtypes": detect_types(df),
        "log": log,
    })

@app.route("/api/reset", methods=["POST"])
def reset_data():
    sid = session.get("sid")
    if sid and sid in ORIGINALS:
        DATASETS[sid] = ORIGINALS[sid].copy()
        df = DATASETS[sid]
        touch_session(sid)
        return jsonify({
            "rows": len(df),
            "cols": len(df.columns),
            "columns": df.columns.tolist(),
            "dtypes": detect_types(df),
            "message": "Reset to original data"
        })
    return jsonify({"error": "No original data to reset"}), 400

@app.route("/api/stats", methods=["POST"])
def stats():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    cols = request.json.get("columns", df.columns.tolist())
    return jsonify(compute_stats(df, cols))

# ----------------------------------------------------------------------
# Histogram endpoint (new)
# ----------------------------------------------------------------------
@app.route("/api/histogram", methods=["POST"])
def histogram():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    col = request.json.get("column")
    if not col or col not in df.columns:
        return jsonify({"error": "Column not found"}), 400
    if not pd.api.types.is_numeric_dtype(df[col]):
        return jsonify({"error": "Column is not numeric"}), 400

    # Use build_chart to generate histogram
    params = {
        "type": "histogram",
        "x": col,
        "title": f"Distribution of {col}",
        "nbins": 30
    }
    fig_json, _ = build_chart(df, params)
    return jsonify({"chart": fig_json})


@app.route("/api/transform_sql", methods=["POST"])
def transform_sql():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    sql = request.json.get("query", "").strip()
    if not sql:
        return jsonify({"error": "Empty SQL query"}), 400

    if not is_safe_sql(sql):
        return jsonify({"error": "Only SELECT queries are allowed. No DROP, DELETE, UPDATE, etc."}), 400

    try:
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///:memory:")
        df.to_sql("df", engine, index=False, if_exists="replace")
        try:
            new_df = run_with_timeout(pd.read_sql, 15, sql, engine)
        except TimeoutError:
            engine.dispose()
            return jsonify({"error": "SQL query timeout (>15 sec)"}), 408
        engine.dispose()
    except Exception as e:
        return jsonify({"error": f"SQL error: {str(e)}"}), 400

    if new_df.empty:
        return jsonify({"error": "Resulting DataFrame is empty"}), 400

    # Replace current dataset
    sid = session["sid"]
    DATASETS[sid] = new_df
    # Keep original unchanged (reset will go back to uploaded state)
    touch_session(sid)

    return jsonify({
        "rows": len(new_df),
        "cols": len(new_df.columns),
        "columns": new_df.columns.tolist(),
        "dtypes": detect_types(new_df),
        "preview": new_df.head(10).fillna("").to_dict(orient="records"),
        "message": "Data replaced by SQL query result"
    })


@app.route("/api/chart", methods=["POST"])
def chart():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    params = request.json

    custom_sql = params.get("custom_sql", "").strip()
    if custom_sql:
        try:
            from sqlalchemy import create_engine
            engine = create_engine("sqlite:///:memory:")
            df.to_sql("df", engine, index=False, if_exists="replace")
            try:
                df = run_with_timeout(pd.read_sql, 15, custom_sql, engine)
            except TimeoutError:
                engine.dispose()
                return jsonify({"error": "SQL query timeout (>15 sec)"}), 408
            engine.dispose()
        except Exception as e:
            return jsonify({"error": f"SQL error: {str(e)}"}), 400

    fig_json, generated_sql = build_chart(df, params)
    sql_query = custom_sql if custom_sql else generated_sql
    return jsonify({"chart": fig_json, "sql_query": sql_query})

@app.route("/api/export")
def export():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400

    fmt = request.args.get("format", "csv")
    if fmt == "csv":
        data = df.to_csv(index=False)
        return Response(data, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})
    elif fmt == "parquet":
        import io
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        return Response(buf.read(), mimetype="application/octet-stream", headers={"Content-Disposition": "attachment; filename=data.parquet"})
    else:
        return jsonify({"error": f"Unsupported format: {fmt}"}), 400

@app.route("/api/train", methods=["POST"])
def train():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400
    params = request.json

    try:
        result = run_with_timeout(train_model, 15, df, params)
    except TimeoutError:
        return jsonify({"error": "Training timeout (>15 sec). Try reducing data or test size."}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if "error" in result:
        return jsonify(result), 400

    # Strip private keys (prefixed with _) before sending to client
    model_obj = result.pop("_model_object", None)
    encoders  = result.pop("_encoders", {})

    if model_obj is not None:
        sid = session.get("sid")
        if sid not in MODELS:
            MODELS[sid] = {}
        MODELS[sid]["model"]      = model_obj
        MODELS[sid]["features"]   = params.get("features", [])
        MODELS[sid]["target"]     = params.get("target")
        MODELS[sid]["model_type"] = result.get("task", "classification")
        MODELS[sid]["encoders"]   = encoders
        touch_session(sid)

    return jsonify(result)

@app.route("/api/save_model", methods=["POST"])
def save_model():
    data = request.json
    model_name = data.get("name", "model")
    sid = session.get("sid")
    user_model = MODELS.get(sid, {}).get("model")
    if user_model is None:
        return jsonify({"error": "No trained model to save"}), 400

    model_data = {
        "model": user_model,
        "features": MODELS[sid].get("features"),
        "target": MODELS[sid].get("target"),
        "model_type": MODELS[sid].get("model_type"),
        "encoders": MODELS[sid].get("encoders", {})
    }
    path = os.path.join("models", f"{model_name}.pkl")
    with open(path, "wb") as f:
        pickle.dump(model_data, f)
    return jsonify({"message": f"Model saved as {model_name}.pkl", "path": path})

@app.route("/api/load_model", methods=["POST"])
def load_model():
    data = request.json
    model_name = data.get("name")
    if not model_name:
        return jsonify({"error": "Model name required"}), 400
    path = os.path.join("models", f"{model_name}.pkl")
    if not os.path.exists(path):
        return jsonify({"error": f"Model {model_name}.pkl not found"}), 400
    with open(path, "rb") as f:
        model_data = pickle.load(f)

    sid = session.get("sid")
    if sid not in MODELS:
        MODELS[sid] = {}
    MODELS[sid]["model"] = model_data["model"]
    MODELS[sid]["features"] = model_data.get("features")
    MODELS[sid]["target"] = model_data.get("target")
    MODELS[sid]["model_type"] = model_data.get("model_type")
    MODELS[sid]["encoders"] = model_data.get("encoders", {})
    touch_session(sid)
    return jsonify({
        "message": f"Model {model_name} loaded",
        "model_type": str(type(model_data["model"]))
    })

@app.route("/api/predict", methods=["POST"])
def predict():
    df = get_df()
    if df is None:
        return jsonify({"error": "Data not loaded"}), 400

    sid = session.get("sid")
    model_data = MODELS.get(sid, {})
    model = model_data.get("model")
    if model is None:
        return jsonify({"error": "No model loaded or trained"}), 400

    features = model_data.get("features")
    if not features:
        return jsonify({"error": "Model has no feature information. Please retrain."}), 400

    X = df[features].copy()
    encoders = model_data.get("encoders", {})
    for col in X.select_dtypes(include="object").columns:
        if col in encoders:
            encoder = encoders[col]
            X[col] = X[col].map(lambda s: encoder.transform([s])[0] if s in encoder.classes_ else -1)
        else:
            from sklearn.preprocessing import LabelEncoder
            X[col] = LabelEncoder().fit_transform(X[col].astype(str))

    preds = model.predict(X)
    result = {"predictions": preds.tolist()}
    if hasattr(model, "predict_proba") and model_data.get("model_type") != "regression":
        proba = model.predict_proba(X)
        result["probabilities"] = proba.tolist()
    return jsonify(result)

@app.route("/api/clear_session", methods=["POST"])
def clear_session():
    sid = session.get("sid")
    if sid:
        with CLEANUP_LOCK:
            DATASETS.pop(sid, None)
            ORIGINALS.pop(sid, None)
            MODELS.pop(sid, None)
            ACCESS_TIMES.pop(sid, None)
        return jsonify({"message": "Session data cleared"})
    return jsonify({"error": "No active session"}), 400

if __name__ == "__main__":
    pass