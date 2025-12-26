from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from typing import Any
from pathlib import Path


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_messages_sqlite(db_path: Path, limit: int = 50) -> list[Any]:
    """
    UI-safe message list (no SQLAlchemy).
    Returns objects with dot-access (msg.subject, msg.date_utc, etc.).
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM messages
            ORDER BY
                CASE WHEN date_utc IS NULL THEN 1 ELSE 0 END,
                date_utc DESC,
                created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    return [SimpleNamespace(**dict(r)) for r in rows]
