"""
Problem 1: API Data Retrieval and Storage
------------------------------------------
Fetches book data (title, authors, publication year) from a public REST API
(An API of Ice and Fire - https://anapioficeandfire.com/api/books), persists
it in a local SQLite database with an idempotent upsert, and prints the
stored rows back out.

Why this API: it is a genuine, unauthenticated public REST endpoint that
returns exactly the shape the assignment asks for (title, author(s),
publication year) without needing an API key, so the script is runnable
by anyone who clones the repo.

Design notes (why it's written this way, not just "it works"):
- Uses a `requests.Session` with a mounted `Retry` adapter instead of a bare
  `requests.get`, because a single flaky call shouldn't kill the whole job.
- Schema uses `release_date` as TEXT (ISO date) rather than trying to force
  it into an INTEGER year column at fetch time — the API returns full dates,
  and coercing at ingestion time silently drops information. Year extraction
  happens at the display/query layer instead.
- `book_id` (the API's own id, parsed out of the `url` field) is the PRIMARY
  KEY, so re-running this script is idempotent (`INSERT ... ON CONFLICT DO
  UPDATE`) instead of appending duplicate rows on every run.
- Authors is a JSON list in the API -> stored as a delimited string with a
  documented separator, with a note on the normalized alternative below.
"""

import json
import logging
import sqlite3
from contextlib import closing
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://www.anapioficeandfire.com/api/books"
DB_PATH = Path(__file__).parent / "books.db"
AUTHOR_SEP = "; "

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def get_session() -> requests.Session:

    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_books() -> list[dict]:

    session = get_session()
    response = session.get(API_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def init_db(conn: sqlite3.Connection) -> None:

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            book_id       INTEGER PRIMARY KEY,
            title         TEXT NOT NULL,
            authors       TEXT,
            publisher     TEXT,
            country       TEXT,
            release_date  TEXT,      -- ISO date string, e.g. 1996-08-01
            num_pages     INTEGER
        )
        """
    )


def upsert_books(conn: sqlite3.Connection, books: list[dict]) -> int:

    rows = []
    for b in books:
        try:
            book_id = int(b["url"].rstrip("/").split("/")[-1])
        except (KeyError, ValueError):
            log.warning("Skipping record with unparsable id: %s", b.get("url"))
            continue
        rows.append(
            (
                book_id,
                b.get("name"),
                AUTHOR_SEP.join(b.get("authors", [])) or None,
                b.get("publisher"),
                b.get("country"),
                b.get("released", "")[:10] or None,  # trim time component
                b.get("numberOfPages"),
            )
        )

    conn.executemany(
        """
        INSERT INTO books (book_id, title, authors, publisher, country, release_date, num_pages)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(book_id) DO UPDATE SET
            title=excluded.title,
            authors=excluded.authors,
            publisher=excluded.publisher,
            country=excluded.country,
            release_date=excluded.release_date,
            num_pages=excluded.num_pages
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def display_books(conn: sqlite3.Connection) -> None:

    cur = conn.execute(
        """
        SELECT title, authors, substr(release_date, 1, 4) AS year
        FROM books
        ORDER BY release_date
        """
    )
    print(f"{'Title':45} {'Author(s)':35} {'Year'}")
    print("-" * 90)
    for title, authors, year in cur.fetchall():
        print(f"{title[:44]:45} {(authors or '—')[:34]:35} {year or '—'}")


def main() -> None:
    log.info("Fetching from %s", API_URL)
    books = fetch_books()
    log.info("Retrieved %d records", len(books))

    with closing(sqlite3.connect(DB_PATH)) as conn:
        init_db(conn)
        n = upsert_books(conn, books)
        log.info("Upserted %d rows into %s", n, DB_PATH)
        display_books(conn)


if __name__ == "__main__":
    main()
