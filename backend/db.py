# Database access. Two engine-level protections, independent of sql_guard.py:
#   1. The SQLite file is opened with mode=ro, so any write is refused.
#   2. An authorizer callback lets a query read ONLY the whitelisted tables and
#      denies everything except SELECT (no PRAGMA, ATTACH, system tables...).

import sqlite3

import pandas as pd

from config import ALLOWED_TABLES, DB_PATH

_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}


def _authorizer(action, arg1, arg2, db_name, source):
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if arg1.lower() in ALLOWED_TABLES else sqlite3.SQLITE_DENY
    if action in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _connect(restricted: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    if restricted:
        conn.set_authorizer(_authorizer)
    return conn


def run_readonly_sql(sql: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def get_schema_ddl() -> list[str]:
    # Trusted internal call used for training only; never exposed to user SQL.
    conn = _connect(restricted=False)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]
