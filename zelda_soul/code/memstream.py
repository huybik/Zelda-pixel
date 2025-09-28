from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Sequence


class MemoryStream:
    """SQLite-backed persistence layer for NPC observations and summaries."""

    def __init__(self, db_name: str = "memory.db"):
        base_dir = Path(__file__).resolve().parent.parent / "memory"
        base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = base_dir / db_name
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_entity_type ON memories(entity_id, type, id)"
            )

    def write_observations(self, entity_id: str, entries: Iterable[dict]) -> None:
        payloads = [
            (
                entity_id,
                "observation",
                entry.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
                json.dumps(entry, ensure_ascii=False),
            )
            for entry in entries
        ]
        if not payloads:
            return
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO memories (entity_id, type, timestamp, data) VALUES (?, ?, ?, ?)",
                payloads,
            )

    def write_summary(self, entity_id: str, summary_entry: dict) -> None:
        payload = (
            entity_id,
            "summary",
            summary_entry.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            json.dumps(summary_entry, ensure_ascii=False),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memories (entity_id, type, timestamp, data) VALUES (?, ?, ?, ?)",
                payload,
            )

    def read_recent(self, entity_id: str, limit: int, entry_type: str = "observation") -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT data FROM memories
                WHERE entity_id = ? AND type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (entity_id, entry_type, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def read_last_summary(self, entity_id: str) -> dict | None:
        summaries = self.read_recent(entity_id, 1, entry_type="summary")
        return summaries[-1] if summaries else None

    def query_observations(self, entity_id: str, keywords: Sequence[str], limit: int = 5) -> list[dict]:
        filtered = [kw.lower() for kw in keywords if kw]
        if not filtered:
            return self.read_recent(entity_id, limit)

        clauses = " OR ".join(["LOWER(data) LIKE ?" for _ in filtered])
        params: list[str | int] = [entity_id, "observation", *[f"%{kw}%" for kw in filtered], limit]
        query = (
            "SELECT data FROM memories WHERE entity_id = ? AND type = ? AND ("
            + clauses
            + ") ORDER BY id DESC LIMIT ?"
        )
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        if not rows:
            return self.read_recent(entity_id, limit)
        return [json.loads(row[0]) for row in reversed(rows)]

    def clear_entity(self, entity_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM memories WHERE entity_id = ?", (entity_id,))
