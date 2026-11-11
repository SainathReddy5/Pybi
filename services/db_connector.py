"""
pyodbc-based connection factory for user-defined datasources.

Fernet symmetric encryption protects passwords at rest.  The key is read from
the PYBI_FERNET_KEY env var on startup; if absent a new key is generated and
written to .key so it survives container restarts when the file is volume-mounted.
"""
import os
import pyodbc
from pathlib import Path
from cryptography.fernet import Fernet

KEY_FILE = Path(".key")

# One driver name per db_type — override via env vars if the installed driver
# has a different name (e.g. 'ODBC Driver 18 for SQL Server').
ODBC_DRIVERS = {
    "postgres": os.getenv("PYBI_PG_ODBC_DRIVER",    "PostgreSQL Unicode"),
    "mysql":    os.getenv("PYBI_MYSQL_ODBC_DRIVER",  "MySQL ODBC 8.0 Unicode Driver"),
    "mssql":    os.getenv("PYBI_MSSQL_ODBC_DRIVER",  "ODBC Driver 17 for SQL Server"),
}


# ── Fernet key management ─────────────────────────────────────────────────────

def _load_fernet() -> Fernet:
    """Load the Fernet key from env → .key file → generate a new one."""
    raw = os.getenv("PYBI_FERNET_KEY")
    if raw:
        return Fernet(raw.encode())
    if KEY_FILE.exists():
        return Fernet(KEY_FILE.read_bytes().strip())
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return Fernet(key)


def encrypt_password(plaintext: str) -> str:
    """Return a Fernet token (str) for the given plaintext password."""
    return _load_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypt a Fernet token back to the original password."""
    return _load_fernet().decrypt(token.encode()).decode()


# ── Connection string builders ────────────────────────────────────────────────

def _build_conn_str(db_type: str, host: str, port: int,
                    database: str, username: str, password: str) -> str:
    driver = ODBC_DRIVERS.get(db_type)
    if not driver:
        raise ValueError(f"Unsupported db_type '{db_type}'. Choose: postgres, mysql, mssql")

    if db_type == "mssql":
        # SQL Server uses SERVER=host,port syntax
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={host},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}"
        )

    # PostgreSQL and MySQL both use SERVER + PORT
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password}"
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_connection(ds) -> pyodbc.Connection:
    """
    Open and return a pyodbc connection for the given DataSource.
    Decrypts the stored password before connecting.
    Caller is responsible for closing the connection.
    """
    password = decrypt_password(ds.encrypted_password)
    conn_str = _build_conn_str(ds.db_type, ds.host, ds.port,
                               ds.database, ds.username, password)
    return pyodbc.connect(conn_str, autocommit=False)


def test_connection(ds) -> tuple[bool, str]:
    """
    Attempt a connection and immediately close it.
    Returns (success, message).
    """
    try:
        conn = get_connection(ds)
        conn.close()
        return True, "Connection successful"
    except pyodbc.Error as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
