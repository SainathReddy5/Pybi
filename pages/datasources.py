"""
Data Sources page — add, test, and delete database connections.

Panel reactivity pattern used here:
  - param.Integer `refresh` is incremented after any write operation.
  - Methods decorated with @pn.depends("refresh") are re-evaluated and the
    Panel layout is updated automatically whenever `refresh` changes.
"""
import param
import panel as pn
from models.datasource import (
    DataSource,
    list_datasources,
    save_datasource,
    delete_datasource,
)
from services.db_connector import encrypt_password, test_connection


class DataSourcesPage(param.Parameterized):
    # Bumping this int causes the datasource table to re-render reactively.
    refresh = param.Integer(default=0)

    def __init__(self, **params):
        super().__init__(**params)

        # ── form widgets ──────────────────────────────────────────────────────
        self.name_w = pn.widgets.TextInput(
            name="Connection Name", placeholder="My Postgres DB", width=220
        )
        self.type_w = pn.widgets.Select(
            name="DB Type", options=["postgres", "mysql", "mssql"], width=140
        )
        self.host_w = pn.widgets.TextInput(
            name="Host", value="localhost", width=200
        )
        self.port_w = pn.widgets.IntInput(
            name="Port", value=5432, start=1, end=65535, width=100
        )
        self.db_w   = pn.widgets.TextInput(name="Database", width=200)
        self.user_w = pn.widgets.TextInput(name="Username", width=180)
        self.pass_w = pn.widgets.PasswordInput(name="Password", width=180)

        # Update default port when db_type changes
        self.type_w.param.watch(self._on_type_change, "value")

        # ── action buttons ────────────────────────────────────────────────────
        self.test_btn = pn.widgets.Button(
            name="Test Connection", button_type="default", width=160
        )
        self.save_btn = pn.widgets.Button(
            name="Save", button_type="primary", width=100
        )
        self.status = pn.pane.Alert("", alert_type="light", visible=False, sizing_mode="stretch_width")

        self.test_btn.on_click(self._on_test)
        self.save_btn.on_click(self._on_save)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _on_type_change(self, event):
        defaults = {"postgres": 5432, "mysql": 3306, "mssql": 1433}
        self.port_w.value = defaults.get(event.new, 5432)

    def _build_ds(self) -> DataSource:
        return DataSource(
            id=None,
            name=self.name_w.value.strip(),
            db_type=self.type_w.value,
            host=self.host_w.value.strip(),
            port=self.port_w.value,
            database=self.db_w.value.strip(),
            username=self.user_w.value.strip(),
            encrypted_password=encrypt_password(self.pass_w.value),
        )

    def _alert(self, msg: str, kind: str = "success"):
        self.status.object    = msg
        self.status.alert_type = kind
        self.status.visible   = True

    # ── button callbacks ──────────────────────────────────────────────────────

    def _on_test(self, _):
        ok, msg = test_connection(self._build_ds())
        self._alert(msg, "success" if ok else "danger")

    def _on_save(self, _):
        ds = self._build_ds()
        if not ds.name:
            self._alert("Connection name is required.", "warning")
            return
        try:
            save_datasource(ds)
            self._alert(f"Datasource '{ds.name}' saved.", "success")
            self.refresh += 1          # triggers _table() to re-render
        except Exception as e:
            self._alert(f"Save failed: {e}", "danger")

    # ── reactive table ────────────────────────────────────────────────────────

    @pn.depends("refresh")
    def _table(self):
        """Re-rendered every time `refresh` is bumped."""
        sources = list_datasources()
        if not sources:
            return pn.pane.Markdown("_No datasources saved yet._")

        header = pn.Row(
            pn.pane.Markdown("**Name**",         width=180),
            pn.pane.Markdown("**Type**",         width=90),
            pn.pane.Markdown("**Host:Port/DB**", width=260),
            pn.pane.Markdown("**Action**",       width=80),
        )
        rows = [header]
        for ds in sources:
            del_btn = pn.widgets.Button(name="Delete", button_type="danger", width=75)

            def _del(_, did=ds.id, dname=ds.name):
                delete_datasource(did)
                self._alert(f"Deleted '{dname}'.", "warning")
                self.refresh += 1

            del_btn.on_click(_del)
            rows.append(pn.Row(
                pn.pane.Markdown(f"**{ds.name}**",                 width=180),
                pn.pane.Markdown(f"`{ds.db_type}`",                width=90),
                pn.pane.Markdown(f"{ds.host}:{ds.port}/{ds.database}", width=260),
                del_btn,
            ))
        return pn.Column(*rows)

    # ── public view ───────────────────────────────────────────────────────────

    def view(self) -> pn.Column:
        form = pn.Column(
            pn.pane.Markdown("## Add Data Source"),
            pn.Row(self.name_w, self.type_w),
            pn.Row(self.host_w, self.port_w),
            pn.Row(self.db_w, self.user_w, self.pass_w),
            pn.Row(self.test_btn, self.save_btn),
            self.status,
        )
        table = pn.Column(
            pn.pane.Markdown("## Saved Data Sources"),
            self._table,           # Panel resolves @pn.depends at render time
        )
        return pn.Column(form, pn.layout.Divider(), table, sizing_mode="stretch_width")
