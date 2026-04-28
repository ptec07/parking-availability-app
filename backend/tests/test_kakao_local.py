from datetime import datetime, timezone, timedelta

from app.db import connect, create_schema
from app.kakao_local import (
    GeocodeResult,
    InMemoryKakaoLocalApi,
    build_geocode_queries,
    geocode_missing_parking_lot_coordinates,
    parse_geocode_response,
)
from app.models import ParkingLotRecord, get_parking_lot, upsert_parking_lot


def make_record(**overrides):
    data = {
        "id": "171721",
        "name": "세종로 공영주차장(시)",
        "address": "종로구 세종로 80-1",
        "lat": None,
        "lng": None,
        "total_spaces": 1260,
        "occupied_spaces": 457,
        "updated_at": datetime(2026, 4, 28, 8, 31, 23, tzinfo=timezone(timedelta(hours=9))),
        "raw_json": {"PKLT_CD": "171721"},
    }
    data.update(overrides)
    return ParkingLotRecord(**data)


def make_conn():
    conn = connect(":memory:")
    create_schema(conn)
    return conn


def test_parse_geocode_response_uses_first_document_coordinates():
    payload = {
        "documents": [
            {
                "address_name": "서울 종로구 세종로 80-1",
                "x": "126.975102",
                "y": "37.573573",
            }
        ],
        "meta": {"total_count": 1},
    }

    result = parse_geocode_response(payload)

    assert result == GeocodeResult(lat=37.573573, lng=126.975102, address_name="서울 종로구 세종로 80-1")


def test_parse_geocode_response_returns_none_for_empty_documents():
    assert parse_geocode_response({"documents": []}) is None


def test_geocode_missing_coordinates_updates_only_records_without_coordinates():
    conn = make_conn()
    upsert_parking_lot(conn, make_record(id="needs", address="종로구 세종로 80-1"))
    upsert_parking_lot(
        conn,
        make_record(id="cached", address="종로구 훈정동 2-0", lat=37.571, lng=126.994),
    )
    api = InMemoryKakaoLocalApi(
        {
            "종로구 세종로 80-1": GeocodeResult(
                lat=37.573573,
                lng=126.975102,
                address_name="서울 종로구 세종로 80-1",
            )
        }
    )

    result = geocode_missing_parking_lot_coordinates(conn, api)

    assert result.checked_count == 2
    assert result.geocoded_count == 1
    assert result.skipped_count == 1
    assert api.queries == ["종로구 세종로 80-1"]
    assert get_parking_lot(conn, "needs").lat == 37.573573
    assert get_parking_lot(conn, "needs").lng == 126.975102
    assert get_parking_lot(conn, "cached").lat == 37.571
    assert get_parking_lot(conn, "cached").lng == 126.994


def test_geocode_missing_coordinates_leaves_record_null_when_api_has_no_result():
    conn = make_conn()
    upsert_parking_lot(conn, make_record(id="missing", address="주소 없음", name="없는 주차장(시)"))
    api = InMemoryKakaoLocalApi({"주소 없음": None, "없는 주차장": None, "서울 없는 주차장": None})

    result = geocode_missing_parking_lot_coordinates(conn, api)

    assert result.checked_count == 1
    assert result.geocoded_count == 0
    assert result.failed_count == 1
    assert get_parking_lot(conn, "missing").lat is None
    assert get_parking_lot(conn, "missing").lng is None


def test_build_geocode_queries_removes_seoul_parking_trailing_zero_and_adds_name_fallbacks():
    record = make_record(
        name="청계3(동호로) 공영주차장(시)",
        address="중구 방산동 4-47 0",
    )

    queries = build_geocode_queries(record)

    assert queries[:2] == ["중구 방산동 4-47 0", "중구 방산동 4-47"]
    assert "서울 중구 방산동 4-47" in queries
    assert "청계3 공영주차장" in queries
    assert "서울 청계3 공영주차장" in queries


def test_geocode_missing_coordinates_tries_cleaned_address_before_name_fallback():
    conn = make_conn()
    upsert_parking_lot(
        conn,
        make_record(
            id="trailing-zero",
            name="청계3(동호로) 공영주차장(시)",
            address="중구 방산동 4-47 0",
        ),
    )
    api = InMemoryKakaoLocalApi(
        {
            "중구 방산동 4-47 0": None,
            "중구 방산동 4-47": GeocodeResult(
                lat=37.568422,
                lng=127.000771,
                address_name="서울 중구 방산동 4-47",
            ),
        }
    )

    result = geocode_missing_parking_lot_coordinates(conn, api)

    assert result.geocoded_count == 1
    assert result.failed_count == 0
    assert api.queries == ["중구 방산동 4-47 0", "중구 방산동 4-47"]
    assert get_parking_lot(conn, "trailing-zero").lat == 37.568422
    assert get_parking_lot(conn, "trailing-zero").lng == 127.000771


def test_geocode_missing_coordinates_uses_parking_lot_name_when_address_candidates_fail():
    conn = make_conn()
    upsert_parking_lot(
        conn,
        make_record(
            id="name-fallback",
            name="당고개위 공영주차장(시)",
            address="노원구 상계동 111-568",
        ),
    )
    api = InMemoryKakaoLocalApi(
        {
            "노원구 상계동 111-568": None,
            "서울 노원구 상계동 111-568": None,
            "당고개위 공영주차장": GeocodeResult(
                lat=37.670714,
                lng=127.079839,
                address_name="서울 노원구 상계동 당고개위 공영주차장",
            ),
        }
    )

    result = geocode_missing_parking_lot_coordinates(conn, api)

    assert result.geocoded_count == 1
    assert result.failed_count == 0
    assert api.queries == [
        "노원구 상계동 111-568",
        "서울 노원구 상계동 111-568",
        "당고개위 공영주차장",
    ]
    assert get_parking_lot(conn, "name-fallback").lat == 37.670714
