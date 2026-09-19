# Assignment 1 — API, SQLite, and CSV Data Pipelines

Ayush Mishra

## Setup

```
python -m venv venv
venv\Scripts\activate          (cmd, Windows)
pip install -r requirements.txt
```

## Structure

| Folder | Problem | Run |
|---|---|---|
| `problem1_books_api_sqlite/` | Fetch books (title, author, year) from a public REST API, store in SQLite, display | `python fetch_books.py` |
| `problem2_scores_visualization/` | Fetch student scores from a REST API, compute average, bar chart | `python scores_analysis.py` |
| `problem3_csv_to_sqlite/` | Import `sample_users.csv` (name, email) into SQLite | `python csv_import.py` |

## Design decisions worth noting

- **Problem 1** uses [An API of Ice and Fire](https://anapioficeandfire.com/api/books) — a real, unauthenticated public REST API whose response shape matches the assignment (title/author/date) exactly, so the script needs no API key or mocking. Upserts on the API's own id, so re-running the script doesn't duplicate rows.
- **Problem 2** — there's no standard public REST API for "student test scores," so rather than relabeling an unrelated public dataset as scores (dishonest data), the script spins up a small real Flask API on `localhost:5055` and fetches from it the same way Problem 1 fetches from a remote host. Swap `API_URL` for a hosted JSON endpoint (e.g. a GitHub Gist raw URL) to point it at a genuinely external source instead — the fetch/compute/plot logic doesn't change.
- **Problem 3** validates every row (regex email check) before insert, uses `email UNIQUE` + `INSERT OR IGNORE` so re-imports are idempotent, and wraps the batch insert in a single transaction so a bad file can't leave the DB half-imported.

All three scripts use parameterized SQL throughout (never string-formatted queries), `contextlib.closing`/`with conn:` for connection lifecycle, and `logging` instead of bare `print` for status messages.

## Links (Assignment 1, items 4 & 5)

- Most complex Python code: `<paste your CrowdMind AI or ML Experiment AutoPilot repo link here>`
- Most complex database/SQL code: `<paste your Enterprise RAG Agent / LLM eval harness repo link here>`
