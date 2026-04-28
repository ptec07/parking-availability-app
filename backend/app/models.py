from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ParkingLotRecord:
    id: str
    name: str
    address: str
    lat: float | None
    lng: float | None
    total_spaces: int | None
    occupied_spaces: int | None
    updated_at: datetime | None
    raw_json: dict[str, Any]


def upsert_parking_lot(conn: sqlite3.Connection, record: ParkingLotRecord) -> None:
    conn.execute(
        """
        INSERT INTO parking_lots (
            id, name, address, lat, lng, total_spaces, occupied_spaces, updated_at, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            address = excluded.address,
            lat = excluded.lat,
            lng = excluded.lng,
            total_spaces = excluded.total_spaces,
            occupied_spaces = excluded.occupied_spaces,
            updated_at = excluded.updated_at,
            raw_json = excluded.raw_json
        """,
        _record_to_row(record),
    )
    conn.commit()


def get_parking_lot(conn: sqlite3.Connection, parking_lot_id: str) -> ParkingLotRecord | None:
    row = conn.execute("SELECT * FROM parking_lots WHERE id = ?", (parking_lot_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_parking_lots(conn: sqlite3.Connection) -> list[ParkingLotRecord]:
    rows = conn.execute("SELECT * FROM parking_lots ORDER BY name ASC, id ASC").fetchall()
    return [_row_to_record(row) for row in rows]


def update_parking_lot_coordinates(
    conn: sqlite3.Connection,
    parking_lot_id: str,
    lat: float,
    lng: float,
) -> None:
    conn.execute(
        "UPDATE parking_lots SET lat = ?, lng = ? WHERE id = ?",
        (lat, lng, parking_lot_id),
    )
    conn.commit()


def _record_to_row(record: ParkingLotRecord) -> tuple[Any, ...]:
    return (
        record.id,
        record.name,
        record.address,
        record.lat,
        record.lng,
        record.total_spaces,
        record.occupied_spaces,
        record.updated_at.isoformat() if record.updated_at else None,
        json.dumps(record.raw_json, ensure_ascii=False, sort_keys=True),
    )


def _row_to_record(row: sqlite3.Row) -> ParkingLotRecord:
    updated_at = datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
    return ParkingLotRecord(
        id=row["id"],
        name=row["name"],
        address=row["address"],
        lat=row["lat"],
        lng=row["lng"],
        total_spaces=row["total_spaces"],
        occupied_spaces=row["occupied_spaces"],
        updated_at=updated_at,
        raw_json=json.loads(row["raw_json"]),
    )
