from datetime import datetime, timezone, timedelta

from app.db import connect, create_schema
from app.models import get_parking_lot, list_parking_lots
from app.sync import InMemorySeoulParkingApi, sync_seoul_parking


SAMPLE_RESPONSE = {
    "GetParkingInfo": {
        "list_total_count": 2,
        "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
        "row": [
            {
                "PKLT_CD": "171721",
                "PKLT_NM": "세종로 공영주차장(시)",
                "ADDR": "종로구 세종로 80-1",
                "PRK_TYPE_NM": "노외 주차장",
                "OPER_SE_NM": "시간제 주차장",
                "TELNO": "02-2290-6566",
                "PRK_STTS_YN": "1",
                "PRK_STTS_NM": "현재~20분이내 연계데이터 존재(현재 주차대수 표현)",
                "TPKCT": 1260.0,
                "NOW_PRK_VHCL_CNT": 457.0,
                "NOW_PRK_VHCL_UPDT_TM": "2026-04-28 08:31:23",
                "PAY_YN_NM": "유료",
            },
            {
                "PKLT_CD": "171722",
                "PKLT_NM": "종묘주차장 공영주차장(시)",
                "ADDR": "종로구 훈정동 2-0",
                "PRK_TYPE_NM": "노외 주차장",
                "TPKCT": 1312.0,
                "NOW_PRK_VHCL_CNT": 690.0,
                "NOW_PRK_VHCL_UPDT_TM": "2026-04-28 08:31:23",
            },
        ],
    }
}


def make_conn():
    conn = connect(":memory:")
    create_schema(conn)
    return conn


def test_sync_seoul_parking_upserts_normalized_rows():
    conn = make_conn()
    api = InMemorySeoulParkingApi([SAMPLE_RESPONSE])

    result = sync_seoul_parking(conn, api, page_size=100)

    assert result.fetched_count == 2
    assert result.saved_count == 2
    records = list_parking_lots(conn)
    assert {record.id for record in records} == {"171721", "171722"}
    saved = get_parking_lot(conn, "171721")
    assert saved.total_spaces == 1260
    assert saved.occupied_spaces == 457
    assert saved.raw_json["PKLT_NM"] == "세종로 공영주차장(시)"


def test_sync_seoul_parking_fetches_multiple_pages_until_total_count_reached():
    conn = make_conn()
    first = {
        "GetParkingInfo": {
            "list_total_count": 2,
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [SAMPLE_RESPONSE["GetParkingInfo"]["row"][0]],
        }
    }
    second = {
        "GetParkingInfo": {
            "list_total_count": 2,
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [SAMPLE_RESPONSE["GetParkingInfo"]["row"][1]],
        }
    }
    api = InMemorySeoulParkingApi([first, second])

    result = sync_seoul_parking(conn, api, page_size=1)

    assert result.fetched_count == 2
    assert result.saved_count == 2
    assert api.calls == [(1, 1), (2, 2)]


def test_sync_seoul_parking_preserves_existing_coordinates_on_update():
    conn = make_conn()
    api = InMemorySeoulParkingApi([SAMPLE_RESPONSE])
    sync_seoul_parking(conn, api, page_size=100)
    saved = get_parking_lot(conn, "171721")
    from app.models import ParkingLotRecord, upsert_parking_lot
    upsert_parking_lot(conn, ParkingLotRecord(**{**saved.__dict__, "lat": 37.5735, "lng": 126.9751}))

    update_response = {
        "GetParkingInfo": {
            "list_total_count": 1,
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [{**SAMPLE_RESPONSE["GetParkingInfo"]["row"][0], "NOW_PRK_VHCL_CNT": 500.0}],
        }
    }
    sync_seoul_parking(conn, InMemorySeoulParkingApi([update_response]), page_size=100)

    updated = get_parking_lot(conn, "171721")
    assert updated.occupied_spaces == 500
    assert updated.lat == 37.5735
    assert updated.lng == 126.9751
