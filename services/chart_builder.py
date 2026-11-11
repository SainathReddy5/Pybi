"""
Build Plotly figures from a pandas DataFrame.
Supported chart types: bar, line, area, pie, kpi, table.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure


def build_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    title: str = "",
) -> Figure:
    """
    Return a Plotly Figure for the given chart_type.

    chart_type values
    -----------------
    bar   — vertical bar chart
    line  — line chart
    area  — filled area chart
    pie   — pie / donut chart  (x_col = labels, y_col = values)
    kpi   — single big number (first row, y_col value)
    table — scrollable grid of all columns
    """
    if df.empty:
        return _empty_figure(title or chart_type)

    chart_type = chart_type.lower().strip()

    if chart_type == "bar":
        return px.bar(df, x=x_col, y=y_col, title=title)

    if chart_type == "line":
        return px.line(df, x=x_col, y=y_col, title=title)

    if chart_type == "area":
        return px.area(df, x=x_col, y=y_col, title=title)

    if chart_type == "pie":
        return px.pie(df, names=x_col, values=y_col, title=title)

    if chart_type == "kpi":
        raw   = df[y_col].iloc[0]
        value = float(raw) if isinstance(raw, (int, float)) else 0
        fig   = go.Figure(go.Indicator(
            mode  = "number",
            value = value,
            title = {"text": title or y_col, "font": {"size": 20}},
            number= {"font": {"size": 64}},
        ))
        fig.update_layout(height=220, margin=dict(t=60, b=20, l=20, r=20))
        return fig

    if chart_type == "table":
        fig = go.Figure(go.Table(
            header=dict(
                values     = list(df.columns),
                fill_color = "#2c7be5",
                font       = dict(color="white", size=13),
                align      = "left",
            ),
            cells=dict(
                values    = [df[c].tolist() for c in df.columns],
                fill_color= [["#f9f9f9", "#ffffff"] * (len(df) // 2 + 1)],
                align     = "left",
            ),
        ))
        fig.update_layout(title=title, margin=dict(t=40, b=10, l=10, r=10))
        return fig

    raise ValueError(f"Unknown chart_type '{chart_type}'. "
                     f"Choose: bar, line, area, pie, kpi, table")


def _empty_figure(title: str) -> Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[dict(text="No data", x=0.5, y=0.5,
                          xref="paper", yref="paper",
                          showarrow=False, font_size=16)],
    )
    return fig
