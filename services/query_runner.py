"""
Execute SQL against a user datasource and return a pandas DataFrame.
Uses a raw pyodbc connection; pandas.read_sql accepts any DBAPI-2 connection.
"""
import pandas as pd
import pyodbc
from services.db_connector import get_connection


def run_query(ds, sql: str) -> tuple[pd.DataFrame, str | None]:
    """
    Run `sql` against `ds` (a DataSource instance).
    Returns (DataFrame, None) on success or (empty DataFrame, error_str) on failure.
    """
    conn = None
    try:
        conn = get_connection(ds)
        # pandas.read_sql works with any DBAPI-2 connection object
        df = pd.read_sql(sql, conn)
        return df, None
    except pyodbc.Error as e:
        return pd.DataFrame(), _clean_error(e)
    except Exception as e:
        return pd.DataFrame(), str(e)
    finally:
        if conn:
            conn.close()


def _clean_error(exc: Exception) -> str:
    """Extract the human-readable part of a pyodbc error."""
    msg = str(exc)
    # pyodbc errors look like: ('42S02', "[42S02] table not found ...")
    if msg.startswith("('"):
        try:
            # Take the part after the SQLSTATE code
            return msg.split("]", 1)[1].strip(" ')")
        except IndexError:
            pass
    return msg
