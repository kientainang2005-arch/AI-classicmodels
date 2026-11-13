# Converts the MySQL dump (classicmodels_utf8.sql) into a SQLite file (data/classicmodels.db).
# Run once:  python scripts/build_sqlite.py

import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "classicmodels_utf8.sql")
DST = os.path.join(ROOT, "data", "classicmodels.db")

TYPE_MAP = [
    (r"^(int|smallint)$", "INTEGER"),
    (r"^(varchar\(\d+\)|text|mediumtext)$", "TEXT"),
    (r"^decimal\(\d+,\d+\)$", "REAL"),
    (r"^date$", "TEXT"),
    (r"^mediumblob$", "BLOB"),
]
ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "", "Z": "\x1a"}


def sqlite_type(mysql_type: str) -> str:
    for pattern, target in TYPE_MAP:
        if re.match(pattern, mysql_type, re.IGNORECASE):
            return target
    raise ValueError(f"Unmapped MySQL type: {mysql_type}")


def convert_create(name: str, body: str) -> str:
    lines = []
    for raw in body.strip().splitlines():
        line = raw.strip().rstrip(",")
        if line.startswith("KEY ") or line.startswith("UNIQUE KEY "):
            continue
        col = re.match(r"^(`\w+`)\s+(\w+(?:\(\d+(?:,\d+)?\))?)(.*)$", line)
        if col:
            line = f"{col.group(1)} {sqlite_type(col.group(2))}{col.group(3)}"
        lines.append(line)
    return f"CREATE TABLE `{name}` (\n  " + ",\n  ".join(lines) + "\n);"


def convert_insert(stmt: str) -> str:
    """Rewrite MySQL backslash escapes inside string literals into SQLite-safe text."""
    out, in_str, i = [], False, 0
    while i < len(stmt):
        ch = stmt[i]
        if in_str and ch == "\\" and i + 1 < len(stmt):
            nxt = stmt[i + 1]
            out.append("''" if nxt == "'" else ESCAPES.get(nxt, nxt))
            i += 2
            continue
        if ch == "'":
            if in_str and i + 1 < len(stmt) and stmt[i + 1] == "'":
                out.append("''")
                i += 2
                continue
            in_str = not in_str
        out.append(ch)
        i += 1
    return "".join(out)


def main():
    with open(SRC, encoding="utf-8") as f:
        dump = f.read()

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    if os.path.exists(DST):
        os.remove(DST)
    conn = sqlite3.connect(DST)

    for name, body in re.findall(r"CREATE TABLE `(\w+)` \((.*?)\n\) ENGINE", dump, re.DOTALL):
        conn.execute(convert_create(name, body))

    for stmt in re.findall(r"^INSERT INTO `\w+` VALUES .*;$", dump, re.MULTILINE):
        conn.execute(convert_insert(stmt))

    conn.commit()
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        count = conn.execute(f"SELECT COUNT(*) FROM `{table}`").fetchone()[0]
        print(f"{table:<14}{count:>6} rows")
    conn.close()
    print(f"Created {DST}")


if __name__ == "__main__":
    main()
