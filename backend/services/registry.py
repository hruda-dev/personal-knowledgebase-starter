"""SQLite stores a compact source catalog. Qdrant stores the actual chunks."""
import sqlite3
from contextlib import contextmanager
from backend.config import DATABASE_PATH


@contextmanager
def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS documents (
               id TEXT PRIMARY KEY,
               filename TEXT NOT NULL,
               chunk_count INTEGER NOT NULL,
               created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    conn.commit()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def add_document(document_id: str, filename: str, chunk_count: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, chunk_count) VALUES (?, ?, ?)",
            (document_id, filename, chunk_count),
        )


def list_documents() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, filename, chunk_count, created_at FROM documents ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def has_document(document_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone()
    return row is not None


def remove_document(document_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
