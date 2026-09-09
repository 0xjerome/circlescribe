from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import GroupState, MeetingExtraction
from .workflow import DemoRunState


@dataclass(frozen=True)
class StoredRunRecord:
    run_id: str
    created_at: str
    updated_at: str
    state: DemoRunState


class LocalRunStore:
    """SQLite-backed persistence for the local hackathon development workflow.

    This deliberately mirrors the durable-state boundary we will move to
    DynamoDB for the AWS deployment. It stores only structured workflow state;
    microphone audio remains ephemeral in local development.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @classmethod
    def from_env(cls) -> "LocalRunStore":
        default_path = Path(__file__).resolve().parents[1] / ".circlescribe" / "runs.sqlite3"
        return cls(os.getenv("CIRCLESCRIBE_RUN_DB", str(default_path)))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_demo_runs_updated_at ON demo_runs(updated_at DESC)"
            )

    @staticmethod
    def _serialize(state: DemoRunState) -> str:
        return json.dumps(
            {
                "extraction": state.extraction.model_dump(mode="json"),
                "group": state.group.model_dump(mode="json"),
                "resolved_event_ids": sorted(state.resolved_event_ids),
                "discarded_event_ids": sorted(state.discarded_event_ids),
            },
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize(payload: str) -> DemoRunState:
        data = json.loads(payload)
        return DemoRunState(
            extraction=MeetingExtraction.model_validate(data["extraction"]),
            group=GroupState.model_validate(data["group"]),
            resolved_event_ids=set(data.get("resolved_event_ids", [])),
            discarded_event_ids=set(data.get("discarded_event_ids", [])),
        )

    def save(self, run_id: str, state: DemoRunState) -> StoredRunRecord:
        now = datetime.now(timezone.utc).isoformat()
        payload = self._serialize(state)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO demo_runs (run_id, created_at, updated_at, state_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    state_json = excluded.state_json
                """,
                (run_id, now, now, payload),
            )
        record = self.get(run_id)
        if record is None:  # defensive: the row was just written
            raise RuntimeError("Failed to persist local demo run.")
        return record

    def get(self, run_id: str) -> StoredRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id, created_at, updated_at, state_json FROM demo_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredRunRecord(
            run_id=row["run_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            state=self._deserialize(row["state_json"]),
        )

    def list_runs(self, limit: int = 10) -> list[StoredRunRecord]:
        safe_limit = max(1, min(limit, 50))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, created_at, updated_at, state_json
                FROM demo_runs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            StoredRunRecord(
                run_id=row["run_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                state=self._deserialize(row["state_json"]),
            )
            for row in rows
        ]
