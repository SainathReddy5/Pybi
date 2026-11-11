"""
DataSource and SavedQuery models with CRUD operations backed by pyodbc + Postgres.
Plain dataclasses are used instead of an ORM — each function opens, uses, and
closes its own connection to stay thread-safe with Panel's async callbacks.
"""
from dataclasses import dataclass
from typing import Optional
from .base import get_meta_conn


@dataclass
class DataSource:
    id: Optional[int]
    name: str
    db_type: str          # postgres | mysql | mssql
    host: str
    port: int
    database: str
    username: str
    encrypted_password: str
    created_at: Optional[str] = None


@dataclass
class SavedQuery:
    id: Optional[int]
    name: str
    datasource_id: int
    sql: str
    created_at: Optional[str] = None


# ── helpers ───────────────────────────────────────────────────────────────────

def _row_to_ds(row) -> DataSource:
    return DataSource(
        id=row[0], name=row[1], db_type=row[2], host=row[3],
        port=row[4], database=row[5], username=row[6],
        encrypted_password=row[7], created_at=str(row[8]) if row[8] else None,
    )

def _row_to_query(row) -> SavedQuery:
    return SavedQuery(
        id=row[0], name=row[1], datasource_id=row[2],
        sql=row[3], created_at=str(row[4]) if row[4] else None,
    )


# ── DataSource CRUD ───────────────────────────────────────────────────────────

def list_datasources() -> list[DataSource]:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id,name,db_type,host,port,database,username,encrypted_password,created_at FROM datasources ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_ds(r) for r in rows]


def get_datasource(ds_id: int) -> Optional[DataSource]:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id,name,db_type,host,port,database,username,encrypted_password,created_at FROM datasources WHERE id=?", ds_id)
    row = cur.fetchone()
    conn.close()
    return _row_to_ds(row) if row else None


def save_datasource(ds: DataSource) -> DataSource:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute(
        """INSERT INTO datasources (name,db_type,host,port,database,username,encrypted_password)
           VALUES (?,?,?,?,?,?,?) RETURNING id""",
        ds.name, ds.db_type, ds.host, ds.port, ds.database, ds.username, ds.encrypted_password,
    )
    ds.id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return ds


def delete_datasource(ds_id: int) -> None:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM datasources WHERE id=?", ds_id)
    conn.commit()
    conn.close()


# ── SavedQuery CRUD ───────────────────────────────────────────────────────────

def list_queries() -> list[SavedQuery]:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id,name,datasource_id,sql,created_at FROM saved_queries ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_query(r) for r in rows]


def get_query(query_id: int) -> Optional[SavedQuery]:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id,name,datasource_id,sql,created_at FROM saved_queries WHERE id=?", query_id)
    row = cur.fetchone()
    conn.close()
    return _row_to_query(row) if row else None


def save_query(q: SavedQuery) -> SavedQuery:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO saved_queries (name,datasource_id,sql) VALUES (?,?,?) RETURNING id",
        q.name, q.datasource_id, q.sql,
    )
    q.id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return q


def delete_query(query_id: int) -> None:
    conn = get_meta_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM saved_queries WHERE id=?", query_id)
    conn.commit()
    conn.close()
