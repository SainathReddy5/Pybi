"""
Analyzer page — Pentaho-style drag-and-drop pivot table builder.

Flow:
  1. Pick a datasource and a table → Load Table
  2. Assign columns to Row Fields, Column Fields, Value Field + Aggregation
  3. Click Build Pivot → see pivot table + auto chart
  4. Change Chart Type to slice the result differently

Panel does not have native HTML drag-and-drop between widgets, so field
assignment is done via MultiChoice selectors — functionally equivalent.
"""
import param
import panel as pn
import pandas as pd

from models.datasource import list_datasources
from services.query_runner import run_query
from services.chart_builder import build_chart


AGG_OPTIONS = ["sum", "count", "mean", "min", "max", "median"]

# SQL to list user tables — works on Postgres, MySQL, MSSQL via information_schema
_TABLE_SQL = {
    "postgres": "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1",
    "mysql":    "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY 1",
    "mssql":    "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' ORDER BY 1",
}


class AnalyzerPage(param.Parameterized):
    pivot_df    = param.DataFrame(default=pd.DataFrame())
    build_error = param.String(default="")

    def __init__(self, **params):
        super().__init__(**params)
        self._ds_map: dict = {}
        self._raw_df = pd.DataFrame()
        self._refresh_ds()

        # ── datasource / table bar ────────────────────────────────────────────
        self.ds_select    = pn.widgets.Select(
            name="Datasource", options=list(self._ds_map.keys()), width=210
        )
        self.table_select = pn.widgets.Select(
            name="Table", options=[], width=200
        )
        self.load_schema_btn = pn.widgets.Button(
            name="Load Tables", button_type="default", width=120
        )
        self.load_table_btn  = pn.widgets.Button(
            name="Load Data", button_type="primary", width=110
        )
        self.row_count_md = pn.pane.Markdown("", width=200)

        # ── field wells (the "drag zones") ────────────────────────────────────
        self.rows_w = pn.widgets.MultiChoice(
            name="🔲 Row Fields",
            options=[], value=[],
            sizing_mode="stretch_width",
        )
        self.cols_w = pn.widgets.MultiChoice(
            name="📋 Column Fields  (optional — creates a cross-tab)",
            options=[], value=[],
            sizing_mode="stretch_width",
        )
        self.value_w = pn.widgets.Select(
            name="📊 Value Field",
            options=[],
            sizing_mode="stretch_width",
        )
        self.agg_w = pn.widgets.Select(
            name="Aggregation", options=AGG_OPTIONS, value="sum", width=130
        )
        self.chart_type_w = pn.widgets.Select(
            name="Chart Type",
            options=["bar", "line", "area", "pie", "table"],
            value="bar", width=130,
        )
        self.build_btn = pn.widgets.Button(
            name="⚙  Build Pivot", button_type="success",
            sizing_mode="stretch_width",
        )
        self.status = pn.pane.Alert(
            "", alert_type="light", visible=False,
            sizing_mode="stretch_width",
        )

        # ── wire callbacks ────────────────────────────────────────────────────
        self.load_schema_btn.on_click(self._on_load_schema)
        self.load_table_btn.on_click(self._on_load_table)
        self.build_btn.on_click(self._on_build)
        # Re-render chart when chart type changes without rebuilding the pivot
        self.chart_type_w.param.watch(lambda _: self.param.trigger("pivot_df"), "value")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _refresh_ds(self):
        sources = list_datasources()
        self._ds_map = {ds.name: ds for ds in sources}

    def _alert(self, msg: str, kind: str = "success"):
        self.status.object     = msg
        self.status.alert_type = kind
        self.status.visible    = True

    def _current_ds(self):
        self._refresh_ds()
        return self._ds_map.get(self.ds_select.value)

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _on_load_schema(self, _):
        self._refresh_ds()
        self.ds_select.options = list(self._ds_map.keys())
        ds = self._current_ds()
        if not ds:
            self._alert("Select a datasource first.", "warning")
            return
        sql = _TABLE_SQL.get(ds.db_type, _TABLE_SQL["postgres"])
        df, err = run_query(ds, sql)
        if err:
            self._alert(f"Schema load error: {err}", "danger")
            return
        tables = df.iloc[:, 0].tolist() if not df.empty else []
        self.table_select.options = tables
        if tables:
            self.table_select.value = tables[0]
        self._alert(f"Found {len(tables)} tables.", "info")

    def _on_load_table(self, _):
        ds    = self._current_ds()
        table = self.table_select.value
        if not ds:
            self._alert("Select a datasource first.", "warning")
            return
        if not table:
            self._alert("Select a table first.", "warning")
            return
        # Load up to 10 000 rows for in-memory pivoting
        df, err = run_query(ds, f'SELECT * FROM "{table}" LIMIT 10000')
        if err:
            self._alert(f"Load error: {err}", "danger")
            return
        self._raw_df = df
        cols     = list(df.columns)
        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(exclude="number").columns.tolist()

        # Populate field wells
        for w in (self.rows_w, self.cols_w):
            w.options = cols
            w.value   = []
        self.value_w.options = cols

        # Auto-suggest sensible defaults
        if cat_cols:
            self.rows_w.value = [cat_cols[0]]
        if num_cols:
            self.value_w.value = num_cols[0]

        self.row_count_md.object = f"**{len(df):,}** rows loaded"
        self._alert(f"Loaded {len(df):,} rows from `{table}`.", "success")

    def _on_build(self, _):
        if self._raw_df.empty:
            self._alert("Load a table first.", "warning")
            return
        rows  = self.rows_w.value
        cols  = self.cols_w.value
        value = self.value_w.value
        agg   = self.agg_w.value
        if not rows:
            self._alert("Add at least one Row Field.", "warning")
            return
        if not value:
            self._alert("Select a Value Field.", "warning")
            return
        try:
            pivot = pd.pivot_table(
                self._raw_df,
                index  = rows,
                columns= cols if cols else None,
                values = value,
                aggfunc= agg,
                fill_value=0,
            ).reset_index()

            # Flatten tuple column names produced by cross-tab
            pivot.columns = [
                " | ".join(str(c) for c in col).strip(" | ")
                if isinstance(col, tuple) else str(col)
                for col in pivot.columns
            ]
            self.build_error = ""
            self.pivot_df    = pivot
        except Exception as e:
            self.build_error = str(e)
            self.pivot_df    = pd.DataFrame()

    # ── reactive result panel ─────────────────────────────────────────────────

    @pn.depends("pivot_df", "build_error")
    def _result_view(self):
        if self.build_error:
            return pn.pane.Alert(
                f"**Pivot error:** {self.build_error}",
                alert_type="danger", sizing_mode="stretch_width",
            )
        if self.pivot_df.empty:
            return pn.pane.Markdown(
                "### Results will appear here\n"
                "_Assign fields and click **Build Pivot**._",
                sizing_mode="stretch_width",
            )

        df          = self.pivot_df
        row_fields  = self.rows_w.value or [df.columns[0]]
        num_cols    = df.select_dtypes(include="number").columns.tolist()
        x_col       = row_fields[0]
        y_col       = num_cols[0] if num_cols else df.columns[-1]
        chart_type  = self.chart_type_w.value

        items = [
            pn.pane.Markdown(f"**{len(df):,} rows** in result"),
        ]

        if chart_type != "table" and len(df) <= 500:
            fig = build_chart(
                df, chart_type, x_col, y_col,
                title=f"{self.agg_w.value}({self.value_w.value}) by {x_col}",
            )
            items.append(pn.pane.Plotly(fig, sizing_mode="stretch_width"))

        items.append(
            pn.widgets.DataFrame(df, sizing_mode="stretch_width", auto_edit=False)
        )
        return pn.Column(*items, sizing_mode="stretch_width")

    # ── public view ───────────────────────────────────────────────────────────

    def view(self) -> pn.Column:
        top_bar = pn.Column(
            pn.pane.Markdown("## Analyzer"),
            pn.Row(
                self.ds_select,
                self.load_schema_btn,
                self.table_select,
                self.load_table_btn,
                self.row_count_md,
            ),
            self.status,
        )

        # Field wells sidebar — mirrors Pentaho's "Available Fields" panel
        field_panel = pn.Column(
            pn.pane.Markdown(
                "### Field Wells\n"
                "_Select columns for each zone, then click Build._"
            ),
            pn.layout.Divider(),
            self.rows_w,
            pn.layout.Divider(),
            self.cols_w,
            pn.layout.Divider(),
            self.value_w,
            pn.Row(self.agg_w, self.chart_type_w),
            self.build_btn,
            width=310,
            css_classes=["card"],
        )

        result_panel = pn.Column(
            self._result_view,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            top_bar,
            pn.layout.Divider(),
            pn.Row(field_panel, result_panel, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )
