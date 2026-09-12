import sqlite3

from config import SQLITE_DB_PATH


def initialize_database():
    """Create the legal document tables when they do not exist."""

    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS legal_documents (
                document_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                law_name TEXT NOT NULL,
                source TEXT,
                document_version TEXT
            );

            CREATE TABLE IF NOT EXISTS legal_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id INTEGER NOT NULL,
                law_name TEXT NOT NULL,
                section_name TEXT,
                page_number INTEGER,
                chunk_text TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES legal_documents(document_id)
            );
            """
        )


def add_document(file_name, law_name, source, document_version):
    """Insert a legal document and return its database identifier."""

    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO legal_documents
                (file_name, law_name, source, document_version)
            VALUES (?, ?, ?, ?)
            """,
            (file_name, law_name, source, document_version),
        )
        document_id = cursor.lastrowid
        cursor.close()

    return document_id


def add_chunk(
    document_id,
    chunk_id,
    law_name,
    section_name,
    page_number,
    chunk_text,
):
    """Insert or update one searchable legal text chunk."""

    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO legal_chunks
                (chunk_id, document_id, law_name, section_name, page_number, chunk_text)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id = excluded.document_id,
                law_name = excluded.law_name,
                section_name = excluded.section_name,
                page_number = excluded.page_number,
                chunk_text = excluded.chunk_text
            """,
            (
                chunk_id,
                document_id,
                law_name,
                section_name,
                page_number,
                chunk_text,
            ),
        )


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