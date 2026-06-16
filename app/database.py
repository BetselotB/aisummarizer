"""SQLite persistence for API keys and jobs."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.config import DB_PATH
from app.services.key_validation import is_valid_gemini_api_key


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL DEFAULT '',
                api_key TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                requests_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress REAL NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                error TEXT,
                source_files TEXT NOT NULL DEFAULT '[]',
                extra_context TEXT NOT NULL DEFAULT '',
                outline_json TEXT,
                document_json TEXT,
                pdf_path TEXT,
                stats_json TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                meta TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        _migrate(conn)
    seed_env_api_keys()


def seed_env_api_keys() -> None:
    """Load GEMINI_API_KEYS from env (comma or newline separated)."""
    raw = os.environ.get("GEMINI_API_KEYS", "")
    if not raw.strip():
        return

    with get_conn() as conn:
        existing = {
            row["api_key"]
            for row in conn.execute("SELECT api_key FROM api_keys").fetchall()
        }
        for i, line in enumerate(raw.replace(",", "\n").splitlines(), 1):
            key = line.strip()
            if not key or key in existing or not is_valid_gemini_api_key(key):
                continue
            key_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO api_keys (id, label, api_key, created_at) VALUES (?, ?, ?, ?)",
                (key_id, f"Env Key {i}", key, _utcnow()),
            )
            existing.add(key)


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "stats_json" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN stats_json TEXT")
    if "started_at" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN started_at TEXT")
    if "finished_at" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN finished_at TEXT")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_api_key(label: str, api_key: str) -> dict[str, Any]:
    key_id = str(uuid.uuid4())
    now = _utcnow()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, label, api_key, created_at) VALUES (?, ?, ?, ?)",
            (key_id, label, api_key, now),
        )
    return get_api_key(key_id)


def list_api_keys() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, label, enabled, requests_count, last_used_at, last_error, created_at, "
            "substr(api_key, 1, 8) || '…' || substr(api_key, -4) AS masked_key FROM api_keys ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def get_api_key(key_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    if not row:
        raise KeyError(key_id)
    d = dict(row)
    d["masked_key"] = d["api_key"][:8] + "…" + d["api_key"][-4:]
    return d


def get_enabled_api_keys() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM api_keys WHERE enabled = 1 ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_api_key(key_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))


def toggle_api_key(key_id: str, enabled: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE api_keys SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, key_id),
        )


def record_key_usage(key_id: str, error: str | None = None) -> None:
    with get_conn() as conn:
        if error:
            conn.execute(
                "UPDATE api_keys SET requests_count = requests_count + 1, last_used_at = ?, last_error = ? WHERE id = ?",
                (_utcnow(), error, key_id),
            )
        else:
            conn.execute(
                "UPDATE api_keys SET requests_count = requests_count + 1, last_used_at = ?, last_error = NULL WHERE id = ?",
                (_utcnow(), key_id),
            )


def create_job(
    title: str,
    source_files: list[str],
    extra_context: str = "",
    job_id: str | None = None,
) -> dict[str, Any]:
    job_id = job_id or str(uuid.uuid4())
    now = _utcnow()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (id, title, status, source_files, extra_context, created_at, updated_at)
               VALUES (?, ?, 'pending', ?, ?, ?, ?)""",
            (job_id, title, json.dumps(source_files), extra_context, now, now),
        )
    return get_job(job_id)


def get_job(job_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise KeyError(job_id)
    return _parse_job(dict(row))


def _parse_job(job: dict[str, Any]) -> dict[str, Any]:
    job["source_files"] = json.loads(job["source_files"])
    if job.get("stats_json"):
        try:
            job["stats"] = json.loads(job["stats_json"])
        except json.JSONDecodeError:
            job["stats"] = None
    else:
        job["stats"] = None
    return job


def list_jobs(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, status, progress, message, error, pdf_path, stats_json, "
            "started_at, finished_at, created_at, updated_at "
            "FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    jobs = []
    for r in rows:
        j = dict(r)
        if j.get("stats_json"):
            try:
                j["stats"] = json.loads(j["stats_json"])
            except json.JSONDecodeError:
                j["stats"] = None
        else:
            j["stats"] = None
        del j["stats_json"]
        jobs.append(j)
    return jobs


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _utcnow()
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", vals)


def add_job_log(job_id: str, message: str, level: str = "info") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO job_logs (job_id, level, message, created_at) VALUES (?, ?, ?, ?)",
            (job_id, level, message, _utcnow()),
        )


def get_job_logs(job_id: str, limit: int = 200) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT level, message, created_at FROM job_logs WHERE job_id = ? ORDER BY id DESC LIMIT ?",
            (job_id, limit),
        ).fetchall()
    return list(reversed([dict(r) for r in rows]))


def get_app_state(key: str) -> Any | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return row["value"]


def set_app_state(key: str, value: Any) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, json.dumps(value), _utcnow()),
        )


def get_all_app_state() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM app_state").fetchall()
    out: dict[str, Any] = {}
    for r in rows:
        try:
            out[r["key"]] = json.loads(r["value"])
        except json.JSONDecodeError:
            out[r["key"]] = r["value"]
    return out


def log_activity(kind: str, message: str, meta: dict[str, Any] | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (kind, message, meta, created_at) VALUES (?, ?, ?, ?)",
            (kind, message, json.dumps(meta) if meta else None, _utcnow()),
        )


def list_activity(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, kind, message, meta, created_at FROM activity_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        if d.get("meta"):
            try:
                d["meta"] = json.loads(d["meta"])
            except json.JSONDecodeError:
                pass
        items.append(d)
    return list(reversed(items))
