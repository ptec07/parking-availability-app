from __future__ import annotations

import sqlite3


def connect(database: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parking_lots (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            lat REAL,
            lng REAL,
            total_spaces INTEGER,
            occupied_spaces INTEGER,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
