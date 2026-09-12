import sqlite3

from config import SQLITE_DB_PATH


def get_all_chunks():
    """Return all indexed legal chunks as dictionary-like rows."""

    if not SQLITE_DB_PATH.exists():
        return []

    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'legal_chunks'
            """
        ).fetchone()

        if table_exists is None:
            return []

        rows = connection.execute(
            """
            SELECT chunk_id, chunk_text, law_name, section_name, page_number
            FROM legal_chunks
            ORDER BY chunk_id
            """
        ).fetchall()

    return rows