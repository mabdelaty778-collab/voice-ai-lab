"""SQLite transactions teach durable writes and safe retries without cloud credentials."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from voice_ai_lab.models import LeadInput


class PersistenceUnavailable(Exception):
    pass


class RequestConflict(Exception):
    pass


class Store:
    def __init__(self, path: Path, fail_writes: bool = False):
        self.path = path
        self.fail_writes = fail_writes

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=3)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE,
                    payload_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL,
                    elapsed_ms REAL,
                    created_at TEXT NOT NULL
                );
            """)

    def capture(self, lead: LeadInput) -> tuple[dict, bool]:
        """Commit the lead and event atomically; never acknowledge a failed write."""
        payload = lead.model_dump(mode="json", exclude={"request_id"})
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        try:
            with closing(self._connect()) as db, db:
                # Serialize writers before checking the idempotency key.
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT * FROM leads WHERE request_id = ?", (str(lead.request_id),)
                ).fetchone()
                if row:
                    if row["payload_hash"] != digest:
                        raise RequestConflict("Request ID already used with different data")
                    return self._public(row), False
                if self.fail_writes:
                    raise PersistenceUnavailable("Simulated write failure")
                now = datetime.now(UTC).isoformat()
                cur = db.execute(
                    "INSERT INTO leads(request_id,payload_hash,name,email,course_id,created_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (str(lead.request_id), digest, lead.name, lead.email, lead.course_id, now),
                )
                db.execute("INSERT INTO events(kind,created_at) VALUES(?,?)", ("lead_saved", now))
                row = db.execute("SELECT * FROM leads WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._public(row), True
        except sqlite3.Error as exc:
            raise PersistenceUnavailable("Local persistence unavailable") from exc

    @staticmethod
    def _public(row) -> dict:
        return {key: row[key] for key in ("id", "name", "email", "course_id", "created_at")}

    def leads(self, limit: int, offset: int) -> tuple[list[dict], int]:
        with closing(self._connect()) as db:
            total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            rows = db.execute(
                "SELECT * FROM leads ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        return [self._public(row) for row in rows], total

    def record_retrieval(self, elapsed_ms: float):
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO events(kind,elapsed_ms,created_at) VALUES(?,?,?)",
                ("retrieval", elapsed_ms, datetime.now(UTC).isoformat()),
            )

    def metrics(self) -> dict:
        with closing(self._connect()) as db:
            leads = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            questions = db.execute("SELECT COUNT(*) FROM events WHERE kind='retrieval'").fetchone()[
                0
            ]
        return {"persisted_test_leads": leads, "retrieval_requests": questions}
