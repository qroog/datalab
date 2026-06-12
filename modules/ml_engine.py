import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.cluster import KMeans
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, confusion_matrix,
    mean_squared_error, r2_score, mean_absolute_error,
)


# ── Helpers

def _safe(v):
    """Convert numpy scalars to plain Python for JSON serialisation."""
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return None if (np.isnan(v) or np.isinf(v)) else float(v)
    return v


def _get_model(model_type: str, hyperparams: dict | None = None):
    """Instantiate the requested sklearn estimator."""
    hp           = hyperparams or {}
    n_estimators = int(hp.get("n_estimators", 100))
    C            = float(hp.get("C", 1.0))

    raw_depth = hp.get("max_depth")
    if raw_depth in (None, "", 0):
        max_depth = None
    else:
        max_depth = int(raw_depth)

    models = {
        "linear_regression":   LinearRegression(),
        "random_forest_clf":   RandomForestClassifier(n_estimators=n_estimators,
                                                       max_depth=max_depth, random_state=42),
        "random_forest_reg":   RandomForestRegressor(n_estimators=n_estimators,
                                                      max_depth=max_depth, random_state=42),
        "logistic":            LogisticRegression(max_iter=500, random_state=42, C=C),
        "decision_tree_clf":   DecisionTreeClassifier(max_depth=max_depth or 6, random_state=42),
        "decision_tree_reg":   DecisionTreeRegressor(max_depth=max_depth or 6, random_state=42),
        "gradient_boost":      GradientBoostingClassifier(n_estimators=n_estimators,
                                                           max_depth=max_depth or 3, random_state=42),
    }
    return models.get(model_type,
                      RandomForestClassifier(n_estimators=50, random_state=42))


def _infer_task(model_type: str, y: pd.Series) -> str:
    if any(kw in model_type for kw in ("clf", "logistic", "gradient_boost")):
        return "classification"
    if any(kw in model_type for kw in ("reg", "linear_regression")):
        return "regression"
    return "regression" if (pd.api.types.is_numeric_dtype(y) and y.nunique() > 20) else "classification"


def _encode_features(X: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Label-encode all object columns. Returns (encoded_X, encoders)."""
    encoders = {}
    X = X.copy()
    for col in X.select_dtypes(include="object").columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        encoders[col] = le
    return X, encoders


def _feature_importance_chart(model, feature_cols: list) -> str | None:
    if not hasattr(model, "feature_importances_"):
        return None
    importances = model.feature_importances_
    if len(importances) != len(feature_cols):
        return None
    fi_df = (
        pd.DataFrame({"feature": feature_cols, "importance": importances})
        .sort_values("importance", ascending=True)
        .tail(30)
    )
    fig = px.bar(fi_df, x="importance", y="feature", orientation="h",
                 title="Feature Importance", template="plotly_white")
    return fig.to_json()


# ── Classification

def _classify(df, X, y, model_type, test_size, feature_cols, hyperparams):
    X, encoders = _encode_features(X)

    le_target     = LabelEncoder()
    y_enc         = le_target.fit_transform(y.astype(str))
    target_classes = le_target.classes_.tolist()

    unique, counts = np.unique(y_enc, return_counts=True)
    stratify    = None if np.any(counts < 2) else y_enc
    warning_msg = ("Stratification disabled because some classes have less than 2 samples."
                   if stratify is None else None)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=test_size, random_state=42, stratify=stratify
    )

    model = _get_model(model_type, hyperparams)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Metrics
    acc = accuracy_score(y_test, y_pred)
    f1  = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    roc = None
    if len(target_classes) == 2 and hasattr(model, "predict_proba"):
        roc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    cm_fig = go.Figure(go.Heatmap(
        z=cm.tolist(), x=target_classes, y=target_classes,
        colorscale="Blues", text=cm.tolist(), texttemplate="%{text}",
    ))
    cm_fig.update_layout(title="Confusion Matrix",
                         xaxis_title="Predicted", yaxis_title="Actual",
                         template="plotly_white")

    charts = {"confusion_matrix": cm_fig.to_json()}
    fi = _feature_importance_chart(model, feature_cols)
    if fi:
        charts["feature_importance"] = fi

    result = {
        "task":          "classification",
        "model":         model_type,
        "samples_train": len(X_train),
        "samples_test":  len(X_test),
        "metrics": {
            "accuracy":   _safe(acc),
            "f1_weighted": _safe(f1),
            "roc_auc":    _safe(roc),
        },
        "classes":        target_classes,
        "charts":         charts,
        "_model_object":  model,
        "_encoders":      encoders,
    }
    if warning_msg:
        result["warning"] = warning_msg
    return result


def _regress(df, X, y, model_type, test_size, feature_cols, hyperparams):
    X, encoders = _encode_features(X)

    y_num = pd.to_numeric(y, errors="coerce")
    mask  = y_num.notna()
    X, y_num = X[mask], y_num[mask]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_num, test_size=test_size, random_state=42
    )

    model = _get_model(model_type, hyperparams)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mse  = mean_squared_error(y_test, y_pred)
    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)
    rmse = float(np.sqrt(mse))

    avp_fig = px.scatter(
        x=y_test.values, y=y_pred,
        labels={"x": "Actual", "y": "Predicted"},
        title="Actual vs Predicted", opacity=0.6, template="plotly_white",
    )
    mn, mx = float(y_test.min()), float(y_test.max())
    avp_fig.add_shape(type="line", x0=mn, y0=mn, x1=mx, y1=mx,
                      line=dict(color="red", dash="dash"))

    res_fig = px.histogram(
        x=y_test.values - y_pred, nbins=30,
        title="Residuals Distribution", template="plotly_white",
        labels={"x": "Residual"},
    )

    charts = {
        "actual_vs_predicted": avp_fig.to_json(),
        "residuals":           res_fig.to_json(),
    }
    fi = _feature_importance_chart(model, feature_cols)
    if fi:
        charts["feature_importance"] = fi

    return {
        "task":          "regression",
        "model":         model_type,
        "samples_train": len(X_train),
        "samples_test":  len(X_test),
        "metrics": {
            "r2":   _safe(r2),
            "rmse": _safe(rmse),
            "mae":  _safe(mae),
        },
        "charts":        charts,
        # private
        "_model_object": model,
        "_encoders":     encoders,
    }


def _kmeans(df: pd.DataFrame, feature_cols: list, n_clusters: int) -> dict:
    if not feature_cols:
        feature_cols = df.select_dtypes(include=np.number).columns.tolist()[:10]

    X = df[feature_cols].dropna()
    if len(X) < n_clusters:
        return {"error": f"Not enough rows ({len(X)}) for {n_clusters} clusters"}

    scaler = StandardScaler()
    Xs     = scaler.fit_transform(X)

    model  = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(Xs)

    # Elbow chart
    k_range  = range(2, min(11, len(X)))
    inertias = [KMeans(n_clusters=k, random_state=42, n_init=10).fit(Xs).inertia_
                for k in k_range]

    elbow_fig = go.Figure(go.Scatter(x=list(k_range), y=inertias, mode="lines+markers"))
    elbow_fig.update_layout(title="Elbow Method", xaxis_title="k", yaxis_title="Inertia",
                            template="plotly_white")

    if Xs.shape[1] >= 2:
        pca     = PCA(n_components=2, random_state=42)
        X_pca   = pca.fit_transform(Xs)
        evr     = pca.explained_variance_ratio_
        title   = f"Clusters (PCA: {evr[0]:.1%} + {evr[1]:.1%} variance)"
        x_label, y_label = "PC1", "PC2"
        centers_pca = pca.transform(model.cluster_centers_)
    else:
        X_pca        = np.hstack([Xs, np.zeros_like(Xs)])
        centers_pca  = None
        title        = "Clusters (single feature)"
        x_label      = feature_cols[0] if feature_cols else "Component 1"
        y_label      = "Component 2"

    plot_df = pd.DataFrame(X_pca, columns=[x_label, y_label])
    plot_df["Cluster"] = labels.astype(str)

    scatter_fig = px.scatter(plot_df, x=x_label, y=y_label, color="Cluster",
                             title=title, template="plotly_white")
    if centers_pca is not None:
        centers_df = pd.DataFrame(centers_pca, columns=[x_label, y_label])
        scatter_fig.add_trace(go.Scatter(
            x=centers_df[x_label], y=centers_df[y_label],
            mode="markers",
            marker=dict(symbol="x", size=12, color="black", line_width=2),
            name="Centers",
        ))

    sizes = pd.Series(labels).value_counts().sort_index()

    return {
        "task":          "clustering",
        "model":         "kmeans",
        "n_clusters":    n_clusters,
        "cluster_sizes": {str(k): int(v) for k, v in sizes.items()},
        "inertia":       _safe(float(model.inertia_)),
        "charts": {
            "elbow":   elbow_fig.to_json(),
            "scatter": scatter_fig.to_json(),
        },
        # private
        "_model_object": model,
        "_encoders":     {},
    }


# ── Public entry point 

def train_model(df: pd.DataFrame, params: dict) -> dict:
    """
    Train a model and return a result dict.

    Private keys (_model_object, _encoders) must be stripped by the caller
    before serialising to JSON:

        result     = train_model(df, params)
        model_obj  = result.pop("_model_object", None)
        encoders   = result.pop("_encoders", {})
        return jsonify(result)
    """
    model_type   = params.get("model", "random_forest_clf")
    target_col   = params.get("target")
    feature_cols = params.get("features", [])
    test_size    = float(params.get("test_size", 0.2))
    n_clusters   = int(params.get("n_clusters", 3))
    hyperparams  = params.get("hyperparams", {})

    if model_type == "kmeans":
        return _kmeans(df, feature_cols, n_clusters)

    if not target_col or not feature_cols:
        return {"error": "Target variable and at least one feature required"}
    if target_col not in df.columns:
        return {"error": f"Column '{target_col}' not found in data"}

    X    = df[feature_cols].copy()
    y    = df[target_col].copy()
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]

    if len(X) < 10:
        return {"error": f"Only {len(X)} rows remain after dropping nulls. Need at least 10 samples."}

    task = _infer_task(model_type, y)
    if task == "classification":
        return _classify(df, X, y, model_type, test_size, feature_cols, hyperparams)
    return _regress(df, X, y, model_type, test_size, feature_cols, hyperparams)