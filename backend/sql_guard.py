# Validates AI-generated SQL before it touches the database.
# Layer 1 of defence (code). Layer 2 is the read-only, table-whitelisted connection in db.py.

import re

from config import ALLOWED_TABLES

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|"
    r"call|exec|execute|load|outfile|infile|sleep|benchmark|set|use|"
    r"pragma|attach|detach|vacuum|load_extension)\b",
    re.IGNORECASE,
)
TABLE_REF = re.compile(r"\b(?:from|join)\s+`?([\w.]+)`?", re.IGNORECASE)
CTE_NAME = re.compile(r"`?(\w+)`?\s+as\s*\(", re.IGNORECASE)


class UnsafeSQLError(ValueError):
    pass


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"(--|#)[^\n]*", " ", sql)
    return sql.strip()


def validate_sql(sql: str) -> str:
    """Return cleaned SQL if it is a single read-only SELECT on allowed tables, else raise."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty SQL.")

    sql = re.sub(r"^\s*```\w*\s*|\s*```\s*$", "", sql.strip())
    sql = re.sub(r"^\s*(sqlite|sql)\s*\n", "", sql, flags=re.IGNORECASE)
    cleaned = _strip_comments(sql).rstrip(";").strip()

    if ";" in cleaned:
        raise UnsafeSQLError("Multiple statements are not allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    match = FORBIDDEN.search(cleaned)
    if match:
        raise UnsafeSQLError(f"Forbidden keyword: {match.group(1).upper()}.")

    ctes = {c.lower() for c in CTE_NAME.findall(cleaned)}
    for table in TABLE_REF.findall(cleaned):
        name = table.lower()
        if name not in ALLOWED_TABLES and name not in ctes:
            raise UnsafeSQLError(f"Table not allowed: {table}.")

    return cleaned
