"""
Dashboard model and CRUD via pyodbc + Postgres.
layout_json stores the full widget configuration as a JSON string so the entire
dashboard state can be round-tripped without any additional tables.
"""
from dataclasses import dataclass, field
from typing import Optional
from .base import get_meta_conn


@dataclass
class Dashboard:
    id: Optional[int]
    name: str
    layout_json: str = field(default="[]")   # JSON list[dict] — see dashboard page
    created_at: Optional[str] = None


def _row_to_dash(row) -> Dashboard:
    return Dashboard(
        id=row[0], name=row[1],
        layout_json=row[2] or "[]",
        created_at=str(row[3]) if row[3] else None,
    )


def list_dashboards() -> list[Dashboard]:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id,name,layout_json,created_at FROM dashboards ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dash(r) for r in rows]


def get_dashboard(dash_id: int) -> Optional[Dashboard]:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id,name,layout_json,created_at FROM dashboards WHERE id=?", dash_id)
    row = cur.fetchone()
    conn.close()
    return _row_to_dash(row) if row else None


def save_dashboard(dash: Dashboard) -> Dashboard:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO dashboards (name,layout_json) VALUES (?,?) RETURNING id",
        dash.name, dash.layout_json,
    )
    dash.id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return dash


def update_dashboard(dash: Dashboard) -> None:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE dashboards SET name=?, layout_json=? WHERE id=?",
        dash.name, dash.layout_json, dash.id,
    )
    conn.commit()
    conn.close()


def delete_dashboard(dash_id: int) -> None:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM dashboards WHERE id=?", dash_id)
    conn.commit()
    conn.close()
