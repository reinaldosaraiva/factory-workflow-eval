from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def get_db_path() -> str:
    return os.getenv("NOTES_DB_PATH", "app/data/notes.db")


def _ensure_parent_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def _migration_sql() -> str:
    migration_file = Path(__file__).parent / "migrations" / "001_create_notes.sql"
    return migration_file.read_text(encoding="utf-8")


def initialize_database(db_path: str | None = None) -> None:
    target_db = db_path or get_db_path()
    _ensure_parent_dir(target_db)
    with sqlite3.connect(target_db) as conn:
        conn.executescript(_migration_sql())
        conn.commit()


def create_note(title: str, content: str | None, created_at: str, db_path: str | None = None) -> dict[str, Any]:
    target_db = db_path or get_db_path()
    initialize_database(target_db)
    with sqlite3.connect(target_db) as conn:
        cursor = conn.execute(
            "INSERT INTO notes (title, content, created_at) VALUES (?, ?, ?)",
            (title, content, created_at),
        )
        conn.commit()
        note_id = int(cursor.lastrowid)
    return {
        "id": note_id,
        "title": title,
        "content": content,
        "created_at": created_at,
    }


def list_notes(db_path: str | None = None) -> list[dict[str, Any]]:
    target_db = db_path or get_db_path()
    initialize_database(target_db)
    with sqlite3.connect(target_db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, title, content, created_at FROM notes ORDER BY id ASC").fetchall()
    return [dict(row) for row in rows]


def clear_notes_store(db_path: str | None = None) -> None:
    target_db = db_path or get_db_path()
    initialize_database(target_db)
    with sqlite3.connect(target_db) as conn:
        conn.execute("DELETE FROM notes")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='notes'")
        conn.commit()
