from datetime import datetime, timezone, timedelta

from app.db import connect, create_schema
from app.models import ParkingLotRecord, get_parking_lot, list_parking_lots, upsert_parking_lot


def make_record(**overrides):
    data = {
        "id": "171721",
        "name": "세종로 공영주차장(시)",
        "address": "종로구 세종로 80-1",
        "lat": 37.5735,
        "lng": 126.9751,
        "total_spaces": 1260,
        "occupied_spaces": 457,
        "updated_at": datetime(2026, 4, 28, 8, 31, 23, tzinfo=timezone(timedelta(hours=9))),
        "raw_json": {"PKLT_CD": "171721", "TPKCT": 1260.0},
    }
    data.update(overrides)
    return ParkingLotRecord(**data)


def test_create_schema_creates_parking_lots_table():
    conn = connect(":memory:")

    create_schema(conn)

    table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='parking_lots'"
    ).fetchone()
    assert table["name"] == "parking_lots"


def test_upsert_and_get_parking_lot_round_trips_record():
    conn = connect(":memory:")
    create_schema(conn)
    record = make_record()

    upsert_parking_lot(conn, record)
    saved = get_parking_lot(conn, "171721")

    assert saved == record


def test_upsert_parking_lot_updates_existing_record():
    conn = connect(":memory:")
    create_schema(conn)
    upsert_parking_lot(conn, make_record(occupied_spaces=457))

    upsert_parking_lot(conn, make_record(occupied_spaces=500, raw_json={"PKLT_CD": "171721", "NOW_PRK_VHCL_CNT": 500}))
    saved = get_parking_lot(conn, "171721")

    assert saved.occupied_spaces == 500
    assert saved.raw_json["NOW_PRK_VHCL_CNT"] == 500


def test_list_parking_lots_returns_all_records_sorted_by_name():
    conn = connect(":memory:")
    create_schema(conn)
    upsert_parking_lot(conn, make_record(id="b", name="훈련원공원 공영주차장"))
    upsert_parking_lot(conn, make_record(id="a", name="세종로 공영주차장"))

    records = list_parking_lots(conn)

    assert [record.id for record in records] == ["a", "b"]
