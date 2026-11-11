"""
Dashboard Builder page.

Widget config schema (one entry in layout_json list):
{
    "query_id":  int,
    "chart_type": str,   # bar | line | area | pie | kpi | table
    "x_col":     str,
    "y_col":     str,
    "title":     str,
    "row":       int,    # GridSpec row (0-indexed, each widget spans 4 rows)
    "col":       int,    # GridSpec col start (0 or 6)
}

Widgets are arranged two-per-row in a 12-column GridSpec.
"""
import json
import param
import panel as pn
import pandas as pd
from typing import Optional

from models.datasource import list_queries, get_query, get_datasource
from models.dashboard import (
    Dashboard, list_dashboards, get_dashboard,
    save_dashboard, update_dashboard,
)
from services.query_runner import run_query
from services.chart_builder import build_chart


CHART_TYPES = ["bar", "line", "area", "pie", "kpi", "table"]
WIDGET_ROW_HEIGHT = 4   # GridSpec rows consumed per widget row


class DashboardBuilderPage(param.Parameterized):
    refresh = param.Integer(default=0)

    def __init__(self, **params):
        super().__init__(**params)
        self._widgets: list[dict] = []   # current canvas state

        # ── Add-widget form ──────────────────────────────────────────────────
        self.q_select     = pn.widgets.Select(
            name="Query", options=self._query_options(), sizing_mode="stretch_width"
        )
        self.chart_select = pn.widgets.Select(
            name="Chart Type", options=CHART_TYPES, width=160
        )
        self.x_select     = pn.widgets.Select(name="X Column", options=[], width=160)
        self.y_select     = pn.widgets.Select(name="Y Column", options=[], width=160)
        self.title_w      = pn.widgets.TextInput(
            name="Widget Title", placeholder="Revenue by Month", width=220
        )
        self.preview_btn  = pn.widgets.Button(
            name="Load Columns", button_type="default", width=130
        )
        self.add_btn      = pn.widgets.Button(
            name="+ Add Widget", button_type="primary", width=130
        )

        # ── Dashboard save / load ────────────────────────────────────────────
        self.dash_name_w   = pn.widgets.TextInput(
            name="Dashboard Name", placeholder="Sales Overview", width=220
        )
        self.save_dash_btn = pn.widgets.Button(
            name="Save Dashboard", button_type="success", width=150
        )
        self.load_select   = pn.widgets.Select(
            name="Saved Dashboards",
            options=self._dash_options(),
            sizing_mode="stretch_width",
        )
        self.load_btn      = pn.widgets.Button(
            name="Load", button_type="default", width=80
        )
        self.clear_btn     = pn.widgets.Button(
            name="Clear Canvas", button_type="warning", width=130
        )
        self.status = pn.pane.Alert(
            "", alert_type="light", visible=False, sizing_mode="stretch_width"
        )

        # ── Canvas placeholder ───────────────────────────────────────────────
        self._canvas_col = pn.Column(
            pn.pane.Markdown("_Add widgets using the form on the left._"),
            sizing_mode="stretch_width",
        )

        # Wire callbacks
        self.preview_btn.on_click(self._on_preview_cols)
        self.add_btn.on_click(self._on_add_widget)
        self.save_dash_btn.on_click(self._on_save)
        self.load_btn.on_click(self._on_load)
        self.clear_btn.on_click(self._on_clear)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _query_options(self) -> dict:
        return {f"{q.name}": q.id for q in list_queries()} or {"(no queries)": None}

    def _dash_options(self) -> dict:
        return {d.name: d.id for d in list_dashboards()} or {"(none)": None}

    def _alert(self, msg: str, kind: str = "success"):
        self.status.object     = msg
        self.status.alert_type = kind
        self.status.visible    = True

    def _fetch_df(self, query_id: int) -> tuple[pd.DataFrame, Optional[str]]:
        q  = get_query(query_id)
        if not q:
            return pd.DataFrame(), "Query not found"
        ds = get_datasource(q.datasource_id)
        if not ds:
            return pd.DataFrame(), "Datasource not found"
        return run_query(ds, q.sql)

    # ── form callbacks ────────────────────────────────────────────────────────

    def _on_preview_cols(self, _):
        qid = self.q_select.value
        if not qid:
            self._alert("Select a query first.", "warning")
            return
        df, err = self._fetch_df(qid)
        if err:
            self._alert(f"Preview error: {err}", "danger")
            return
        cols = list(df.columns)
        self.x_select.options = cols
        self.y_select.options = cols
        if len(cols) >= 2:
            self.x_select.value = cols[0]
            self.y_select.value = cols[1]

    def _on_add_widget(self, _):
        qid = self.q_select.value
        if not qid:
            self._alert("Select a query first.", "warning")
            return
        if not self.x_select.value or not self.y_select.value:
            self._alert("Load columns first, then choose X and Y.", "warning")
            return

        idx = len(self._widgets)
        cfg = {
            "query_id":   qid,
            "chart_type": self.chart_select.value,
            "x_col":      self.x_select.value,
            "y_col":      self.y_select.value,
            "title":      self.title_w.value or self.chart_select.value,
            "row":        (idx // 2) * WIDGET_ROW_HEIGHT,
            "col":        (idx % 2) * 6,
        }
        self._widgets.append(cfg)
        self._rebuild_canvas()

    def _on_save(self, _):
        name = self.dash_name_w.value.strip()
        if not name:
            self._alert("Enter a dashboard name.", "warning")
            return
        layout_json = json.dumps(self._widgets)
        existing = {d.name: d for d in list_dashboards()}
        try:
            if name in existing:
                d = existing[name]
                d.layout_json = layout_json
                update_dashboard(d)
            else:
                save_dashboard(Dashboard(id=None, name=name, layout_json=layout_json))
            self._alert(f"Dashboard '{name}' saved.", "success")
            self.load_select.options = self._dash_options()
        except Exception as e:
            self._alert(f"Save error: {e}", "danger")

    def _on_load(self, _):
        dash_id = self.load_select.value
        if not dash_id:
            return
        d = get_dashboard(dash_id)
        if not d:
            return
        self._widgets = json.loads(d.layout_json)
        self.dash_name_w.value = d.name
        self._rebuild_canvas()
        self._alert(f"Loaded '{d.name}'.", "info")

    def _on_clear(self, _):
        self._widgets = []
        self._rebuild_canvas()

    # ── canvas rendering ──────────────────────────────────────────────────────

    def _rebuild_canvas(self):
        """
        Re-populate _canvas_col from the current self._widgets list.
        Uses pn.GridSpec for a 12-column layout; each widget occupies 6 columns
        and 4 rows (two widgets per row).
        """
        if not self._widgets:
            self._canvas_col.objects = [
                pn.pane.Markdown("_Canvas is empty — add widgets using the left panel._")
            ]
            return

        grid = pn.GridSpec(sizing_mode="stretch_width", min_height=600)

        for i, cfg in enumerate(self._widgets):
            df, err = self._fetch_df(cfg["query_id"])
            if err:
                cell = pn.pane.Alert(f"Widget error: {err}", alert_type="danger")
            else:
                fig  = build_chart(df, cfg["chart_type"],
                                   cfg["x_col"], cfg["y_col"], cfg["title"])
                plotly_pane = pn.pane.Plotly(fig, sizing_mode="stretch_width")

                remove_btn = pn.widgets.Button(name="✕ Remove", button_type="danger", width=100)

                def _remove(_, idx=i):
                    self._widgets.pop(idx)
                    # Re-number row/col after removal
                    for j, w in enumerate(self._widgets):
                        w["row"] = (j // 2) * WIDGET_ROW_HEIGHT
                        w["col"] = (j % 2) * 6
                    self._rebuild_canvas()

                remove_btn.on_click(_remove)
                cell = pn.Card(
                    plotly_pane,
                    title=cfg["title"],
                    header=pn.Row(
                        pn.pane.Markdown(f"### {cfg['title']}"),
                        remove_btn,
                    ),
                    sizing_mode="stretch_width",
                    collapsible=False,
                )

            row_s = cfg["row"]
            row_e = row_s + WIDGET_ROW_HEIGHT
            col_s = cfg["col"]
            col_e = col_s + 6
            grid[row_s:row_e, col_s:col_e] = cell

        self._canvas_col.objects = [grid]

    # ── public view ───────────────────────────────────────────────────────────

    def view(self) -> pn.Row:
        sidebar = pn.Column(
            pn.pane.Markdown("### Add Widget"),
            self.q_select,
            self.preview_btn,
            pn.Row(self.x_select, self.y_select),
            self.chart_select,
            self.title_w,
            self.add_btn,
            pn.layout.Divider(),
            pn.pane.Markdown("### Dashboard"),
            self.dash_name_w,
            self.save_dash_btn,
            pn.layout.Divider(),
            pn.pane.Markdown("### Load"),
            self.load_select,
            pn.Row(self.load_btn, self.clear_btn),
            self.status,
            width=300,
        )
        return pn.Row(sidebar, self._canvas_col, sizing_mode="stretch_width")
