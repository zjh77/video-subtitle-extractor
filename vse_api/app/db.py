from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from .config import DB_PATH, ensure_data_dirs

FILE_COLUMNS = {
    "id",
    "drama_name",
    "episode_label",
    "original_filename",
    "stored_filename",
    "stored_path",
    "size_bytes",
    "mime_type",
    "status",
    "created_at",
}

JOB_COLUMNS = {
    "id",
    "file_id",
    "drama_name",
    "episode_label",
    "status",
    "mode",
    "language",
    "generate_txt",
    "subtitle_ymin",
    "subtitle_ymax",
    "subtitle_xmin",
    "subtitle_xmax",
    "job_dir",
    "log_path",
    "result_srt_path",
    "result_txt_path",
    "progress",
    "stage",
    "error_message",
    "created_at",
    "started_at",
    "finished_at",
}


def _connect() -> sqlite3.Connection:
    ensure_data_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn() -> sqlite3.Connection:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        _ensure_table_schema(conn, "files", FILE_COLUMNS)
        _ensure_table_schema(conn, "jobs", JOB_COLUMNS)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                drama_name TEXT NOT NULL,
                episode_label TEXT,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mime_type TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                drama_name TEXT NOT NULL,
                episode_label TEXT,
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                language TEXT NOT NULL,
                generate_txt INTEGER NOT NULL DEFAULT 1,
                subtitle_ymin INTEGER,
                subtitle_ymax INTEGER,
                subtitle_xmin INTEGER,
                subtitle_xmax INTEGER,
                job_dir TEXT NOT NULL,
                log_path TEXT NOT NULL,
                result_srt_path TEXT,
                result_txt_path TEXT,
                progress REAL NOT NULL DEFAULT 0,
                stage TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id)
            )
            """
        )


def create_file(record: dict[str, Any]) -> None:
    _insert("files", record)


def update_file(file_id: str, **fields: Any) -> None:
    _update("files", "id", file_id, fields)


def get_file(file_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    return _file_row_to_dict(row) if row else None


def list_files(drama_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = "SELECT * FROM files"
    params: list[Any] = []
    if drama_name:
        query += " WHERE drama_name=?"
        params.append(drama_name)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_file_row_to_dict(row) for row in rows]


def delete_file(file_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))


def create_job(record: dict[str, Any]) -> None:
    _insert("jobs", record)


def update_job(job_id: str, **fields: Any) -> None:
    _update("jobs", "id", job_id, fields)


def get_job(job_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return _job_row_to_dict(row) if row else None


def list_jobs(drama_name: str | None = None, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = "SELECT * FROM jobs"
    clauses: list[str] = []
    params: list[Any] = []
    if drama_name:
        clauses.append("drama_name=?")
        params.append(drama_name)
    if status:
        clauses.append("status=?")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_job_row_to_dict(row) for row in rows]


def list_jobs_for_file(file_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE file_id=? ORDER BY created_at DESC",
            (file_id,),
        ).fetchall()
    return [_job_row_to_dict(row) for row in rows]


def delete_job(job_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def _insert(table: str, record: dict[str, Any]) -> None:
    keys = ", ".join(record.keys())
    placeholders = ", ".join("?" for _ in record)
    values = list(record.values())
    with get_conn() as conn:
        conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)


def _update(table: str, key_column: str, key_value: str, fields: dict[str, Any]) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key}=?" for key in fields.keys())
    values = list(fields.values()) + [key_value]
    with get_conn() as conn:
        conn.execute(f"UPDATE {table} SET {assignments} WHERE {key_column}=?", values)


def _ensure_table_schema(conn: sqlite3.Connection, table_name: str, required_columns: set[str]) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    if not exists:
        return
    current_columns = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if required_columns.issubset(current_columns):
        return
    backup_name = f"{table_name}_legacy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn.execute(f"ALTER TABLE {table_name} RENAME TO {backup_name}")


def _file_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _job_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["generate_txt"] = bool(item["generate_txt"])
    return item
