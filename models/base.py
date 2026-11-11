"""
PyBI metadata store — all persistence goes through a dedicated Postgres database
accessed via pyodbc so the entire stack uses a single driver.

Connection details are read from environment variables (see docker-compose.yml).
"""
import os
import pyodbc

# ── connection config (override via env for prod) ──────────────────────────────
META_HOST   = os.getenv("PYBI_META_HOST",     "postgres")
META_PORT   = os.getenv("PYBI_META_PORT",     "5432")
META_DB     = os.getenv("PYBI_META_DATABASE", "pybi")
META_USER   = os.getenv("PYBI_META_USER",     "pybi")
META_PASS   = os.getenv("PYBI_META_PASSWORD", "pybi")

# ODBC driver name for the metadata Postgres instance.
# The docker image installs 'PostgreSQL Unicode' via odbc-postgresql.
PG_DRIVER = os.getenv("PYBI_PG_DRIVER", "PostgreSQL Unicode")


def get_meta_conn() -> pyodbc.Connection:
    """Return a live pyodbc connection to the PyBI metadata database."""
    conn_str = (
        f"DRIVER={{{PG_DRIVER}}};"
        f"SERVER={META_HOST};"
        f"PORT={META_PORT};"
        f"DATABASE={META_DB};"
        f"UID={META_USER};"
        f"PWD={META_PASS}"
    )
    return pyodbc.connect(conn_str, autocommit=False)


def init_db() -> None:
    """Create metadata tables if they do not exist (safe to call on every startup)."""
    conn = get_meta_conn()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS datasources (
            id                 SERIAL PRIMARY KEY,
            name               TEXT    UNIQUE NOT NULL,
            db_type            TEXT    NOT NULL,         -- postgres | mysql | mssql
            host               TEXT    NOT NULL,
            port               INTEGER NOT NULL,
            database           TEXT    NOT NULL,
            username           TEXT    NOT NULL,
            encrypted_password TEXT    NOT NULL,         -- Fernet token
            created_at         TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_queries (
            id            SERIAL PRIMARY KEY,
            name          TEXT    NOT NULL,
            datasource_id INTEGER NOT NULL REFERENCES datasources(id) ON DELETE CASCADE,
            sql           TEXT    NOT NULL,
            created_at    TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dashboards (
            id          SERIAL PRIMARY KEY,
            name        TEXT UNIQUE NOT NULL,
            layout_json TEXT DEFAULT '[]',              -- JSON list of widget configs
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    conn.close()
