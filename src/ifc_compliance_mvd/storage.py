from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Iterator

from .paths import DATABASE_PATH

SCHEMA_VERSION = 2
DEFAULT_PROJECT_ID = "project-egress-research"

MIGRATIONS = {
    1: """
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE models (
            model_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            name TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            source TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            element_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE check_runs (
            run_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            model_id TEXT NOT NULL REFERENCES models(model_id),
            status TEXT NOT NULL CHECK (
                status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED')
            ),
            started_at TEXT NOT NULL,
            completed_at TEXT,
            duration_ms REAL,
            checker_version TEXT NOT NULL,
            rule_count INTEGER NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            status_counts_json TEXT NOT NULL DEFAULT '{}',
            error_json TEXT
        );

        CREATE INDEX check_runs_model_started_idx
            ON check_runs(model_id, started_at DESC);

        CREATE TABLE results (
            run_id TEXT NOT NULL REFERENCES check_runs(run_id) ON DELETE CASCADE,
            rule_id TEXT NOT NULL,
            element_guid TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (run_id, rule_id, element_guid)
        );

        CREATE INDEX results_status_idx ON results(run_id, status);
        CREATE INDEX results_element_idx ON results(element_guid, run_id);
        CREATE INDEX results_rule_idx ON results(rule_id, run_id);
    """,
    2: """
        CREATE TABLE query_history (
            query_id TEXT PRIMARY KEY,
            original_utterance TEXT NOT NULL,
            locale TEXT NOT NULL CHECK (locale IN ('zh-CN', 'en')),
            dsl_json TEXT NOT NULL,
            result_count INTEGER NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE INDEX query_history_created_idx
            ON query_history(created_at DESC);
    """,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ComplianceStore:
    """Versioned SQLite audit store for projects, models and check runs."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied = {
                row["version"]
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            unknown = [version for version in applied if version > SCHEMA_VERSION]
            if unknown:
                raise RuntimeError(
                    f"Database schema {max(unknown)} is newer than supported {SCHEMA_VERSION}."
                )
            for version in range(1, SCHEMA_VERSION + 1):
                if version in applied:
                    continue
                connection.executescript(MIGRATIONS[version])
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, utc_now()),
                )

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
        return int(row["version"])

    def seed_fixture(
        self,
        *,
        model_id: str,
        model_name: str,
        schema_version: str,
        source: str,
        model_path: Path,
        element_count: int,
    ) -> None:
        now = utc_now()
        model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects(project_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (
                    DEFAULT_PROJECT_ID,
                    "IBC egress research",
                    "Local research project created from the reproducible IFC fixture.",
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO models(
                    model_id, project_id, name, schema_version, source,
                    source_sha256, element_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    name = excluded.name,
                    schema_version = excluded.schema_version,
                    source = excluded.source,
                    source_sha256 = excluded.source_sha256,
                    element_count = excluded.element_count
                """,
                (
                    model_id,
                    DEFAULT_PROJECT_ID,
                    model_name,
                    schema_version,
                    source,
                    model_hash,
                    element_count,
                    now,
                ),
            )

    def save_completed_run(
        self,
        *,
        execution_id: str,
        model_id: str,
        checker_version: str,
        rule_count: int,
        results: list[dict],
        started_at: str | None = None,
        duration_ms: float | None = None,
    ) -> str:
        run_id = f"run-{uuid.uuid4().hex}"
        start = started_at or utc_now()
        end = utc_now()
        counts = dict(sorted(Counter(result["status"] for result in results).items()))
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO check_runs(
                    run_id, execution_id, project_id, model_id, status,
                    started_at, completed_at, duration_ms, checker_version,
                    rule_count, result_count, status_counts_json
                )
                VALUES (?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    execution_id,
                    DEFAULT_PROJECT_ID,
                    model_id,
                    start,
                    end,
                    duration_ms,
                    checker_version,
                    rule_count,
                    len(results),
                    json.dumps(counts, sort_keys=True),
                ),
            )
            connection.executemany(
                """
                INSERT INTO results(run_id, rule_id, element_guid, status, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        result["rule_id"],
                        result["element_guid"],
                        result["status"],
                        json.dumps(result, sort_keys=True),
                    )
                    for result in results
                ],
            )
        return run_id

    def run_and_save(self, engine) -> tuple[str, list[dict]]:
        started_at = utc_now()
        start = perf_counter()
        results = engine.run(persist=True)
        duration_ms = round((perf_counter() - start) * 1000, 3)
        run_id = self.save_completed_run(
            execution_id=engine.execution_id,
            model_id="ibc-egress-demo",
            checker_version=engine.checker_version,
            rule_count=len(engine.rules),
            results=results,
            started_at=started_at,
            duration_ms=duration_ms,
        )
        return run_id, results

    @staticmethod
    def _decode_run(row: sqlite3.Row) -> dict:
        item = dict(row)
        item["status_counts"] = json.loads(item.pop("status_counts_json"))
        error_json = item.pop("error_json")
        item["error"] = json.loads(error_json) if error_json else None
        return item

    def list_projects(self) -> list[dict]:
        with self.connect() as connection:
            projects = connection.execute(
                """
                SELECT p.*,
                    COUNT(DISTINCT m.model_id) AS model_count,
                    COUNT(DISTINCT r.run_id) AS run_count
                FROM projects p
                LEFT JOIN models m ON m.project_id = p.project_id
                LEFT JOIN check_runs r ON r.project_id = p.project_id
                GROUP BY p.project_id
                ORDER BY p.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in projects]

    def list_models(self) -> list[dict]:
        with self.connect() as connection:
            models = connection.execute(
                "SELECT * FROM models ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in models]

    def list_runs(
        self,
        *,
        model_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        clauses = []
        parameters: list[object] = []
        if model_id:
            clauses.append("model_id = ?")
            parameters.append(model_id)
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS total FROM check_runs {where}",
                parameters,
            ).fetchone()["total"]
            rows = connection.execute(
                f"""
                SELECT * FROM check_runs
                {where}
                ORDER BY started_at DESC, run_id DESC
                LIMIT ? OFFSET ?
                """,
                [*parameters, limit, offset],
            ).fetchall()
        return {
            "items": [self._decode_run(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_run(self, run_id: str, *, include_results: bool = True) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM check_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                return None
            item = self._decode_run(row)
            if include_results:
                results = connection.execute(
                    """
                    SELECT payload_json FROM results
                    WHERE run_id = ?
                    ORDER BY rule_id, element_guid
                    """,
                    (run_id,),
                ).fetchall()
                item["results"] = [json.loads(result["payload_json"]) for result in results]
        return item

    def compare_runs(self, base_run_id: str, target_run_id: str) -> dict | None:
        base = self.get_run(base_run_id)
        target = self.get_run(target_run_id)
        if base is None or target is None:
            return None
        base_by_key = {
            (result["rule_id"], result["element_guid"]): result
            for result in base["results"]
        }
        target_by_key = {
            (result["rule_id"], result["element_guid"]): result
            for result in target["results"]
        }
        changes = []
        for key in sorted(base_by_key.keys() | target_by_key.keys()):
            before = base_by_key.get(key)
            after = target_by_key.get(key)
            if before == after:
                continue
            changes.append(
                {
                    "rule_id": key[0],
                    "element_guid": key[1],
                    "before": before,
                    "after": after,
                    "change": (
                        "ADDED" if before is None else "REMOVED" if after is None else "CHANGED"
                    ),
                }
            )
        return {
            "base_run_id": base_run_id,
            "target_run_id": target_run_id,
            "unchanged_count": len(base_by_key.keys() & target_by_key.keys())
            - sum(change["change"] == "CHANGED" for change in changes),
            "change_count": len(changes),
            "changes": changes,
        }

    def save_query(
        self,
        *,
        original_utterance: str,
        locale: str,
        dsl: dict,
        result_count: int,
        warnings: list[str],
    ) -> str:
        query_id = f"query-{uuid.uuid4().hex}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO query_history(
                    query_id, original_utterance, locale, dsl_json,
                    result_count, warnings_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    original_utterance,
                    locale,
                    json.dumps(dsl, sort_keys=True),
                    result_count,
                    json.dumps(warnings, sort_keys=True),
                    utc_now(),
                ),
            )
        return query_id

    def list_queries(self, *, limit: int = 20, offset: int = 0) -> dict:
        with self.connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) AS total FROM query_history"
            ).fetchone()["total"]
            rows = connection.execute(
                """
                SELECT * FROM query_history
                ORDER BY created_at DESC, query_id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["dsl"] = json.loads(item.pop("dsl_json"))
            item["warnings"] = json.loads(item.pop("warnings_json"))
            items.append(item)
        return {"items": items, "total": total, "limit": limit, "offset": offset}
