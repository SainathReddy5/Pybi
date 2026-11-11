"""
PyBI — Python BI tool entry point.

Startup sequence
----------------
1. pn.extension() initialises Panel with Plotly + CodeEditor support.
2. init_db() creates the three metadata tables in Postgres (idempotent).
3. Pages are instantiated (each carries its own param state).
4. FastListTemplate wires everything together.

Serve:
    panel serve app.py --show
"""
import panel as pn

# ── Panel extensions must be loaded before any widget is created ──────────────
pn.extension(
    "plotly",
    "codeeditor",
    sizing_mode="stretch_width",
)

# ── Bootstrap metadata tables ─────────────────────────────────────────────────
from models.base import init_db
init_db()

# ── Instantiate pages ─────────────────────────────────────────────────────────
from pages.datasources   import DataSourcesPage
from pages.query_builder import QueryBuilderPage
from pages.dashboard     import DashboardBuilderPage
from pages.analyzer      import AnalyzerPage

ds_page      = DataSourcesPage()
qb_page      = QueryBuilderPage()
dash_page    = DashboardBuilderPage()
analyzer_page = AnalyzerPage()

# ── Build template ────────────────────────────────────────────────────────────
# FastListTemplate gives a responsive sidebar + main area shell.
# Navigation is handled via pn.Tabs so all three pages load once and stay alive.
template = pn.template.FastListTemplate(
    title        = "PyBI",
    logo         = "",           # swap for a logo URL if desired
    sidebar_width= 0,            # no extra sidebar — nav lives in the Tabs bar
    main=[
        pn.Tabs(
            ("📁  Data Sources",      ds_page.view()),
            ("🔍  Query Builder",     qb_page.view()),
            ("🔬  Analyzer",          analyzer_page.view()),
            ("📊  Dashboard Builder", dash_page.view()),
            dynamic=True,        # tabs render lazily on first visit
        )
    ],
    main_max_width="1400px",
)

# ── servable ──────────────────────────────────────────────────────────────────
template.servable()
