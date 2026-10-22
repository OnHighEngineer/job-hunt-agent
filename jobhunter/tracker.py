"""SQLite tracker: one row per job, statuses update themselves from replies.

Local file by default; export to CSV for a spreadsheet view.
"""
from __future__ import annotations

import csv
import sqlite3
import time
from typing import List, Optional

from .models import JobPosting, Status

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    url TEXT PRIMARY KEY,
    first_seen REAL NOT NULL,
    source TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT DEFAULT '',
    status TEXT NOT NULL,
    fit_score INTEGER,
    fit_reason TEXT DEFAULT '',
    skip_reason TEXT DEFAULT '',
    next_step TEXT DEFAULT '',
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sends (
    day TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT DEFAULT '',
    sent_at REAL NOT NULL
);
"""


class Tracker:
    def __init__(self, path: str = ":memory:", now=None):
        self._now = now or time.time
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)

    def close(self) -> None:
        self._db.close()

    def has(self, url: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
        return row is not None

    def add(self, posting: JobPosting, status: Status,
            fit_score=None, fit_reason="", skip_reason="", next_step="") -> None:
        now = self._now()
        self._db.execute(
            "INSERT OR REPLACE INTO jobs "
            "(url, first_seen, source, company, title, location, status, "
            " fit_score, fit_reason, skip_reason, next_step, updated_at) "
            "VALUES (?, COALESCE((SELECT first_seen FROM jobs WHERE url = ?), ?), "
            "        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (posting.url, posting.url, now, posting.source, posting.company,
             posting.title, posting.location, status.value,
             fit_score, fit_reason, skip_reason, next_step, now))
        self._db.commit()

    def set_status(self, url: str, status: Status, next_step: str = "") -> bool:
        cur = self._db.execute(
            "UPDATE jobs SET status = ?, next_step = ?, updated_at = ? WHERE url = ?",
            (status.value, next_step, self._now(), url))
        self._db.commit()
        return cur.rowcount > 0

    def by_status(self, status: Status) -> List[sqlite3.Row]:
        return list(self._db.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY updated_at DESC",
            (status.value,)))

    def all(self) -> List[sqlite3.Row]:
        return list(self._db.execute("SELECT * FROM jobs ORDER BY updated_at DESC"))

    def find_by_company_token(self, token: str) -> Optional[sqlite3.Row]:
        return self._db.execute(
            "SELECT * FROM jobs WHERE lower(company) LIKE ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (f"%{token.lower()}%",)).fetchone()

    def record_send(self, recipient: str, subject: str, day: str) -> None:
        self._db.execute(
            "INSERT INTO sends (day, recipient, subject, sent_at) VALUES (?, ?, ?, ?)",
            (day, recipient, subject, self._now()))
        self._db.commit()

    def sends_today(self, day: str) -> int:
        row = self._db.execute(
            "SELECT COUNT(*) AS n FROM sends WHERE day = ?", (day,)).fetchone()
        return row["n"]

    def export_csv(self, path: str) -> int:
        rows = self.all()
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["url", "first_seen", "source", "company", "title",
                             "location", "status", "fit_score", "fit_reason",
                             "skip_reason", "next_step", "updated_at"])
            for r in rows:
                writer.writerow([r[c] for c in r.keys()])
        return len(rows)
