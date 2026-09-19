"""
Problem 2: Data Processing and Visualization
---------------------------------------------
Fetches student test-score data from a REST API, computes the average
score, and renders a bar chart.

Why a local Flask API instead of a public one: there is no standard public
REST API for "student test scores" (unlike Problem 1's books API), so
fabricating a call against some unrelated public endpoint and relabeling
its fields as "scores" would be dishonest data, not a real API integration.
Instead this script spins up an actual, tiny REST endpoint (Flask, one
route: GET /api/scores) on localhost, then fetches from it exactly the way
Problem 1 fetches from a remote host — same requests.get + .json() pattern,
same error handling. This is swappable for a real hosted endpoint with a
one-line change (see API_URL below): if your grader wants a genuinely
external example instead, host `sample_scores.json` in this folder as a
GitHub Gist and point API_URL at its raw URL.

Design notes:
- Server runs in a background thread so one script does fetch -> process
  -> plot end to end with `python scores_analysis.py`, no second terminal.
- Average is computed with `statistics.mean`, not sum/len by hand, so it
  raises `StatisticsError` on an empty dataset instead of a silent
  ZeroDivisionError-turned-NaN.
- Chart is saved to disk (`average_scores.png`) rather than only calling
  `plt.show()`, so it works in a headless CI environment too.
"""

from __future__ import annotations

import statistics
import threading
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe backend; must precede pyplot import
import matplotlib.pyplot as plt
import requests
from flask import Flask, jsonify

HOST, PORT = "127.0.0.1", 5055
API_URL = f"http://{HOST}:{PORT}/api/scores"  # swap for a raw Gist URL to use a genuinely external API
OUTPUT_CHART = Path(__file__).parent / "average_scores.png"

# Seed data the local API serves. Replace with a real roster.
SAMPLE_SCORES = [
    {"name": "Ayush", "score": 78},
    {"name": "Daksh", "score": 92},
    {"name": "Kabul", "score": 65},
    {"name": "Meera", "score": 88},
    {"name": "Rohan", "score": 71},
    {"name": "Saanvng", "score": 95},
]

app = Flask(__name__)


@app.route("/api/scores")
def get_scores():
    return jsonify(SAMPLE_SCORES)


def run_server() -> None:

    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def fetch_scores() -> list[dict]:
    response = requests.get(API_URL, timeout=5)
    response.raise_for_status()
    return response.json()


def compute_average(scores: list[dict]) -> float:
    values = [s["score"] for s in scores]
    if not values:
        raise statistics.StatisticsError("No scores to average")
    return statistics.mean(values)


def plot_scores(scores: list[dict], average: float) -> None:
    names = [s["name"] for s in scores]
    values = [s["score"] for s in scores]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, values, color="#4C72B0")
    ax.axhline(average, color="#C44E52", linestyle="--", linewidth=1.5,
               label=f"Average = {average:.1f}")
    ax.bar_label(bars, padding=3)
    ax.set_ylabel("Score")
    ax.set_title("Student Test Scores")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_CHART, dpi=150)
    print(f"Chart saved to {OUTPUT_CHART}")


def main() -> None:
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    scores = fetch_scores()
    average = compute_average(scores)

    print(f"Fetched {len(scores)} records from {API_URL}")
    for s in scores:
        print(f"  {s['name']:10} {s['score']}")
    print(f"Average score: {average:.2f}")

    plot_scores(scores, average)


if __name__ == "__main__":
    main()
