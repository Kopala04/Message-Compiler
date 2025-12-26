from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_message_sqlite(db_path: Path, message_id: int) -> Any | None:
    mid = int(message_id)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
        if not row:
            return None
        return SimpleNamespace(**dict(row))


def mark_read_sqlite(db_path: Path, message_id: int) -> None:
    mid = int(message_id)
    with _connect(db_path) as conn:
        conn.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (mid,))
        conn.commit()

def update_provider_msg_id_sqlite(db_path: Path, message_id: int, provider_msg_id: str) -> None:
    mid = int(message_id)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE messages SET provider_msg_id = ? WHERE id = ?",
            (str(provider_msg_id), mid),
        )
        conn.commit()

def get_account_email_sqlite(db_path: Path, message_id: int) -> str | None:
    """Get the account email for a message by joining with accounts table."""
    mid = int(message_id)
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT a.email
            FROM messages m
            JOIN accounts a ON m.account_id = a.id
            WHERE m.id = ?
            """,
            (mid,),
        ).fetchone()
        if not row:
            return None
        return row["email"]


def save_body_sqlite(db_path: Path, message_id: int, body_text: str | None, body_html: str | None) -> None:
    mid = int(message_id)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE messages SET body_text = ?, body_html = ? WHERE id = ?",
            (body_text, body_html, mid),
        )
        conn.commit()
