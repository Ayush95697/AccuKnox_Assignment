"""
Problem 3: CSV Data Import to a Database
------------------------------------------
Reads user records (name, email) from a CSV file and inserts them into a
SQLite database.

A CSV-import script that just loops and INSERTs is trivial but wrong in
three ways that actually matter in production, all fixed here:

1. No validation -> a malformed row (empty email, garbage string) silently
   becomes a bad row in the database. `is_valid_email` filters those out
   and they're reported, not swallowed.
2. No uniqueness constraint -> re-running the script on the same file (or
   an overlapping export) duplicates every user. `email` is UNIQUE and the
   insert uses `INSERT OR IGNORE`, so re-runs are idempotent.
3. Row-by-row `execute()` in autocommit mode -> one bad row partway through
   a large file leaves the DB in a half-imported state with no easy way to
   tell what happened. This uses a single transaction (`executemany` inside
   a `with conn:` block) so the whole import commits or nothing does.
"""

import csv
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path

CSV_PATH = Path(__file__).parent / "sample_users.csv"
DB_PATH = Path(__file__).parent / "users.db"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_RE.match(email.strip()))


def read_csv(path: Path) -> tuple[list[tuple[str, str]], int]:

    valid_rows = []
    skipped = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):  # header is line 1
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip().lower()
            if not name or not is_valid_email(email):
                log.warning("Skipping line %d — invalid row: %s", line_num, row)
                skipped += 1
                continue
            valid_rows.append((name, email))
    return valid_rows, skipped


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
        """
    )


def insert_users(conn: sqlite3.Connection, rows: list[tuple[str, str]]) -> int:

    with conn:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)", rows
        )
    return cur.rowcount if cur.rowcount != -1 else len(rows)


def display_users(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT id, name, email FROM users ORDER BY id")
    print(f"{'ID':4} {'Name':20} {'Email'}")
    print("-" * 55)
    for uid, name, email in cur.fetchall():
        print(f"{uid:<4} {name[:19]:20} {email}")


def main() -> None:
    rows, skipped = read_csv(CSV_PATH)
    log.info("Parsed %d valid rows (%d skipped) from %s", len(rows), skipped, CSV_PATH)

    with closing(sqlite3.connect(DB_PATH)) as conn:
        init_db(conn)
        inserted = insert_users(conn, rows)
        log.info("Inserted %d new rows into %s (duplicates ignored)", inserted, DB_PATH)
        display_users(conn)


if __name__ == "__main__":
    main()
