import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

from app.models.schemas import EvaluationRun, EvaluationSummary


class EvaluationStore:
    """Small SQLite run store. Use a managed DB for multi-instance production."""

    def __init__(self, db_path: str) -> None:
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS evaluation_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    total_cases INTEGER NOT NULL,
                    passed_cases INTEGER NOT NULL,
                    failed_cases INTEGER NOT NULL,
                    pass_rate REAL NOT NULL,
                    avg_latency_ms REAL NOT NULL,
                    p95_latency_ms REAL NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    payload_json TEXT NOT NULL
                )"""
            )

    def save(self, run: EvaluationRun) -> None:
        payload = run.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO evaluation_runs
                (run_id, created_at, provider, model, total_cases, passed_cases,
                 failed_cases, pass_rate, avg_latency_ms, p95_latency_ms,
                 total_tokens, estimated_cost_usd, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(run.run_id), run.created_at.isoformat(), run.provider, run.model,
                    run.total_cases, run.passed_cases, run.failed_cases, run.pass_rate,
                    run.avg_latency_ms, run.p95_latency_ms, run.total_tokens,
                    run.estimated_cost_usd, payload,
                ),
            )

    def get(self, run_id: UUID) -> EvaluationRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM evaluation_runs WHERE run_id = ?", (str(run_id),)
            ).fetchone()
        return EvaluationRun.model_validate_json(row["payload_json"]) if row else None

    def list_summaries(self, limit: int = 20) -> list[EvaluationSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT run_id, created_at, provider, model, total_cases, passed_cases,
                failed_cases, pass_rate, avg_latency_ms, p95_latency_ms, total_tokens,
                estimated_cost_usd FROM evaluation_runs
                ORDER BY created_at DESC LIMIT ?""", (limit,)
            ).fetchall()
        return [EvaluationSummary.model_validate(dict(row) | {"run_id": UUID(row["run_id"])}) for row in rows]
