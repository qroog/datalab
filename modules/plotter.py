import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import json

AGG_TO_SQL = {
    "avg": "AVG",
    "mean": "AVG",
    "sum": "SUM",
    "min": "MIN",
    "max": "MAX",
    "count": "COUNT",
    "nunique": "COUNT(DISTINCT",
    "median": "MEDIAN",
}

AGG_TO_PANDAS = {
    "avg": "mean",
    "mean": "mean",
    "sum": "sum",
    "min": "min",
    "max": "max",
    "count": "count",
    "nunique": "nunique",
    "median": "median",
}


def apply_aggregation(df, x, y, color, aggregation, custom_agg_expr=None):

    agg = (aggregation or "none").lower()
    
    if agg == "none" or not x or x not in df.columns:
        return df, y, None

    group_cols = [x]
    if color and color in df.columns and color != x:
        group_cols.append(color)

    if agg == "count" and not y:
        grouped = df.groupby(group_cols).size().reset_index(name="count")
        sql = f"SELECT {', '.join(group_cols)}, COUNT(*) AS count FROM data GROUP BY {', '.join(group_cols)}"
        return grouped, "count", sql

    if agg == "custom" and custom_agg_expr:
        try:
            sql = f"SELECT {', '.join(group_cols)}, {custom_agg_expr} AS agg_result FROM data GROUP BY {', '.join(group_cols)}"
            return df, y, sql 
        except Exception:
            return df, y, None

    if agg not in AGG_TO_PANDAS:
        return df, y, None

    if not y or y not in df.columns:
        return df, y, None

    pandas_agg = AGG_TO_PANDAS[agg]
    grouped = df.groupby(group_cols)[y].agg(pandas_agg).reset_index()
    
    sql_agg_name = AGG_TO_SQL.get(agg, agg.upper())
    if sql_agg_name == "COUNT(DISTINCT":
        sql_expr = f"COUNT(DISTINCT {y})"
    else:
        sql_expr = f"{sql_agg_name}({y})"
    
    sql = f"SELECT {', '.join(group_cols)}, {sql_expr} AS {y} FROM data GROUP BY {', '.join(group_cols)}"
    return grouped, y, sql


def _build_sql_like_query(df, params, grouped_sql=None):
    if grouped_sql:
        return grouped_sql

    chart_type = params.get("type", "scatter")
    x = params.get("x")
    y = params.get("y")
    color = params.get("color")
    nbins = params.get("nbins", 30)
    cols = params.get("columns", [])

    fields = [c for c in [x, y, color] if c]
    if chart_type in ("heatmap", "parallel", "scatter_matrix"):
        fields = cols if cols else df.select_dtypes(include=np.number).columns.tolist()[:6]

    if chart_type == "histogram":
        return f"SELECT {x} FROM data; -- HISTOGRAM({x}) WITH {nbins} bins"
    if chart_type == "density":
        return f"SELECT {x} FROM data; -- DENSITY({x})"
    if chart_type == "pie":
        return f"SELECT {x}, COUNT(*) AS count FROM data GROUP BY {x} ORDER BY count DESC;"
    if chart_type == "heatmap":
        return "SELECT numeric_columns FROM data; -- CORRELATION_MATRIX(numeric_columns)"
    if chart_type == "parallel":
        return f"SELECT {', '.join(fields)} FROM data; -- PARALLEL_COORDINATES"
    if chart_type == "scatter_matrix":
        return f"SELECT {', '.join(fields)} FROM data; -- SCATTER_MATRIX"

    if fields:
        return f"SELECT {', '.join(fields)} FROM data;"
    return "SELECT * FROM data;"


def _sanitize_fig_json(fig) -> str:

    import json, base64, struct

    def _decode_typed(obj):
        if isinstance(obj, dict):
            if "bdata" in obj and "dtype" in obj:
                dtype = obj["dtype"]
                raw = base64.b64decode(obj["bdata"])
                fmt_map = {
                    "i1": "b", "i2": "h", "i4": "i", "i8": "q",
                    "u1": "B", "u2": "H", "u4": "I", "u8": "Q",
                    "f4": "f", "f8": "d",
                }
                fmt = fmt_map.get(dtype, "h")
                size = struct.calcsize(fmt)
                count = len(raw) // size
                return list(struct.unpack("<" + fmt * count, raw))
            return {k: _decode_typed(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_decode_typed(i) for i in obj]
        return obj

    parsed = json.loads(fig.to_json())
    sanitized = _decode_typed(parsed)
    return json.dumps(sanitized)


def build_chart(df, params):
    """
    Построить Plotly график.
    Возвращает (json_фигуры, sql_запрос)
    """
    chart_type = params.get("type", "scatter")
    x = params.get("x")
    y = params.get("y")
    color = params.get("color")
    size = params.get("size")
    title = params.get("title", "")
    nbins = params.get("nbins", 30)
    cols = params.get("columns", [])
    aggregation = params.get("aggregation", "none")
    custom_agg_expr = params.get("custom_agg_expression", "")

    if chart_type == "pie" and not y:
        df_work, y_work, grouped_sql = df, None, None
    else:
        df_work, y_work, grouped_sql = apply_aggregation(
            df, x, y, color, aggregation, custom_agg_expr
        )
    sql_query = _build_sql_like_query(df, params, grouped_sql)


    try:
        if chart_type == "scatter":
            fig = px.scatter(df_work, x=x, y=y_work, color=color, size=size,
                             title=title, opacity=0.7, template="plotly_white")

        elif chart_type == "line":
            fig = px.line(df_work, x=x, y=y_work, color=color, title=title, template="plotly_white")

        elif chart_type == "bar":
            if x and x in df_work.columns and df_work[x].nunique() <= 100:
                if y_work and y_work in df_work.columns:
                    fig = px.bar(df_work, x=x, y=y_work, color=color, title=title, template="plotly_white")
                else:
                    vc = df[x].value_counts().reset_index()
                    vc.columns = [x, "count"]
                    fig = px.bar(vc, x=x, y="count", title=title, template="plotly_white")
            else:
                fig = px.histogram(df_work, x=x, title=title, template="plotly_white")

        elif chart_type == "histogram":
            fig = px.histogram(df_work, x=x, nbins=nbins, color=color,
                               title=title, template="plotly_white", marginal="box")

        elif chart_type == "box":
            fig = px.box(df_work, x=x, y=y_work, color=color,
                         title=title, template="plotly_white", points="outliers")

        elif chart_type == "violin":
            fig = px.violin(df_work, x=x, y=y_work, color=color,
                            title=title, template="plotly_white", box=True)

        elif chart_type == "pie":
            if not x or x not in df.columns:
                fig = go.Figure()
                fig.add_annotation(text="Выберите столбец для оси X", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            else:
                if y_work and y_work in df_work.columns and aggregation != "none" and len(df_work) < len(df):
                    pie_df = df_work[[x, y_work]].copy()
                    pie_df.columns = ["label", "value"]
                else:
                    vc = df[x].value_counts().reset_index()
                    vc.columns = ["label", "value"]
                    pie_df = vc
                if len(pie_df) > 20:
                    pie_df = pie_df.head(20)
                labels = pie_df["label"].astype(str).tolist()
                values = [int(v) for v in pie_df["value"]]
                fig = go.Figure(go.Pie(labels=labels, values=values))
                fig.update_layout(title=title, template="plotly_white")

        elif chart_type == "heatmap":
            num_cols = cols if cols else df.select_dtypes(include=np.number).columns.tolist()
            corr = df[num_cols].corr()
            fig = go.Figure(go.Heatmap(
                z=corr.values.tolist(),
                x=corr.columns.tolist(),
                y=corr.index.tolist(),
                colorscale="RdBu",
                zmid=0,
                text=[[f"{v:.2f}" for v in row] for row in corr.values],
                texttemplate="%{text}",
            ))
            fig.update_layout(title=title or "Correlation Heatmap", template="plotly_white")

        elif chart_type == "parallel":
            num_cols = cols if cols else df.select_dtypes(include=np.number).columns.tolist()
            sample = df[num_cols].dropna().sample(min(1000, len(df)))
            fig = px.parallel_coordinates(sample, color=color if color in num_cols else None,
                                          title=title, template="plotly_white")

        elif chart_type == "density":
            numeric_data = df[x].dropna()
            try:
                fig = ff.create_distplot([numeric_data.values], [x], show_hist=True, show_rug=False)
                fig.update_layout(title=title or f"Density: {x}", template="plotly_white")
            except Exception:
                fig = px.histogram(df, x=x, nbins=nbins, title=title, template="plotly_white")

        elif chart_type == "scatter_matrix":
            num_cols = cols if cols else df.select_dtypes(include=np.number).columns.tolist()[:6]
            extra = [color] if color and color in df.columns and color not in num_cols else []
            sample = df[num_cols + extra].dropna().sample(min(500, len(df)))
            fig = px.scatter_matrix(sample, dimensions=num_cols, color=color if color in sample.columns else None,
                                    title=title, template="plotly_white")

        else:
            fig = px.scatter(df_work, x=x, y=y_work, title=title, template="plotly_white")

        fig.update_layout(
            font_family="system-ui, sans-serif",
            margin=dict(l=40, r=20, t=50, b=40),
        )
        return _sanitize_fig_json(fig), sql_query

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Ошибка: {e}", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=14))
        fig.update_layout(template="plotly_white")
        return fig.to_json(), f"-- chart build error: {e}"