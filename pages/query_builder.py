"""
Query Builder page — write SQL, run it against a saved datasource, view
the result as a DataFrame, and save named queries for reuse on dashboards.
"""
import param
import panel as pn
import pandas as pd

from models.datasource import (
    list_datasources,
    list_queries,
    save_query,
    delete_query,
    SavedQuery,
)
from services.query_runner import run_query


class QueryBuilderPage(param.Parameterized):
    # Reactive state ────────────────────────────────────────────────────────
    refresh    = param.Integer(default=0)       # bumped after any query save/delete
    result_df  = param.DataFrame(default=pd.DataFrame())
    run_error  = param.String(default="")

    def __init__(self, **params):
        super().__init__(**params)
        self._ds_map: dict = {}   # { display_name: DataSource }
        self._refresh_ds()

        # ── widgets ─────────────────────────────────────────────────────────
        self.ds_select = pn.widgets.Select(
            name="Data Source",
            options=list(self._ds_map.keys()),
            sizing_mode="stretch_width",
        )
        self.editor = pn.widgets.CodeEditor(
            name="SQL Editor",
            language="sql",
            value="SELECT 1",
            height=220,
            sizing_mode="stretch_width",
        )
        self.run_btn = pn.widgets.Button(
            name="▶ Run Query", button_type="primary", width=130
        )
        self.query_name_w = pn.widgets.TextInput(
            name="Query Name", placeholder="e.g. Monthly Revenue", width=220
        )
        self.save_q_btn = pn.widgets.Button(
            name="Save Query", button_type="success", width=120
        )
        self.status = pn.pane.Alert("", alert_type="light", visible=False,
                                    sizing_mode="stretch_width")

        self.run_btn.on_click(self._on_run)
        self.save_q_btn.on_click(self._on_save_query)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _refresh_ds(self):
        sources = list_datasources()
        self._ds_map = {ds.name: ds for ds in sources}

    def _alert(self, msg: str, kind: str = "success"):
        self.status.object     = msg
        self.status.alert_type = kind
        self.status.visible    = True

    # ── button callbacks ──────────────────────────────────────────────────────

    def _on_run(self, _):
        self._refresh_ds()
        # Sync widget options in case new datasources were added on another tab
        self.ds_select.options = list(self._ds_map.keys())
        ds = self._ds_map.get(self.ds_select.value)
        if not ds:
            self._alert("Select a datasource first.", "warning")
            return
        df, err = run_query(ds, self.editor.value)
        if err:
            self.run_error = err
            self.result_df = pd.DataFrame()
        else:
            self.run_error = ""
            self.result_df = df

    def _on_save_query(self, _):
        self._refresh_ds()
        ds   = self._ds_map.get(self.ds_select.value)
        name = self.query_name_w.value.strip()
        if not ds:
            self._alert("Select a datasource first.", "warning")
            return
        if not name:
            self._alert("Enter a name for the query.", "warning")
            return
        try:
            save_query(SavedQuery(
                id=None, name=name,
                datasource_id=ds.id,
                sql=self.editor.value,
            ))
            self._alert(f"Query '{name}' saved.", "success")
            self.refresh += 1
        except Exception as e:
            self._alert(f"Save failed: {e}", "danger")

    # ── reactive panels ───────────────────────────────────────────────────────

    @pn.depends("result_df", "run_error")
    def _result_view(self):
        if self.run_error:
            return pn.pane.Alert(f"**Query error:** {self.run_error}",
                                 alert_type="danger", sizing_mode="stretch_width")
        if self.result_df.empty:
            return pn.pane.Markdown(
                "_Run a query to see results here._",
                sizing_mode="stretch_width",
            )
        return pn.widgets.DataFrame(
            self.result_df,
            sizing_mode="stretch_width",
            auto_edit=False,
        )

    @pn.depends("refresh")
    def _saved_queries(self):
        queries = list_queries()
        if not queries:
            return pn.pane.Markdown("_No saved queries yet._")

        items = []
        for q in queries:
            load_btn = pn.widgets.Button(name="Load", button_type="default", width=65)
            del_btn  = pn.widgets.Button(name="Del",  button_type="danger",  width=50)

            def _load(_, qsql=q.sql, qdsid=q.datasource_id):
                self.editor.value = qsql
                # Switch datasource selector to the query's datasource
                for name, ds in self._ds_map.items():
                    if ds.id == qdsid:
                        self.ds_select.value = name
                        break

            def _del(_, qid=q.id, qname=q.name):
                delete_query(qid)
                self._alert(f"Deleted '{qname}'.", "warning")
                self.refresh += 1

            load_btn.on_click(_load)
            del_btn.on_click(_del)

            items.append(pn.Row(
                pn.pane.Markdown(f"**{q.name}**", width=220),
                load_btn, del_btn,
            ))
        return pn.Column(*items)

    # ── public view ───────────────────────────────────────────────────────────

    def view(self) -> pn.Column:
        editor_section = pn.Column(
            pn.pane.Markdown("## Query Builder"),
            self.ds_select,
            self.editor,
            pn.Row(self.run_btn, self.query_name_w, self.save_q_btn),
            self.status,
            pn.pane.Markdown("### Results"),
            self._result_view,
            sizing_mode="stretch_width",
        )
        saved_section = pn.Column(
            pn.pane.Markdown("## Saved Queries"),
            self._saved_queries,
            sizing_mode="stretch_width",
        )
        return pn.Column(
            editor_section,
            pn.layout.Divider(),
            saved_section,
            sizing_mode="stretch_width",
        )
