from datetime import datetime, timezone

from app.seoul_parking import SeoulParkingLot, build_api_url, normalize_parking_lot


SAMPLE_ROW = {
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
    "WD_OPER_BGNG_TM": "0000",
    "WD_OPER_END_TM": "2400",
    "WE_OPER_BGNG_TM": "0000",
    "WE_OPER_END_TM": "2400",
    "LHLDY_OPER_BGNG_TM": "0000",
    "LHLDY_OPER_END_TM": "2400",
    "BSC_PRK_CRG": 430,
    "BSC_PRK_HR": 5,
    "ADD_PRK_CRG": 430,
    "ADD_PRK_HR": 5,
    "DAY_MAX_CRG": 0,
}


def test_normalize_parking_lot_preserves_identity_and_address():
    lot = normalize_parking_lot(SAMPLE_ROW)

    assert isinstance(lot, SeoulParkingLot)
    assert lot.id == "171721"
    assert lot.name == "세종로 공영주차장(시)"
    assert lot.address == "종로구 세종로 80-1"
    assert lot.parking_type_name == "노외 주차장"


def test_normalize_parking_lot_interprets_now_count_as_occupied_spaces():
    lot = normalize_parking_lot(SAMPLE_ROW)

    assert lot.total_spaces == 1260
    assert lot.occupied_spaces == 457
    assert lot.available_spaces == 803


def test_normalize_parking_lot_parses_update_time_as_kst_timezone_aware_datetime():
    lot = normalize_parking_lot(SAMPLE_ROW)

    assert lot.updated_at.hour == 8
    assert lot.updated_at.minute == 31
    assert lot.updated_at.second == 23
    assert lot.updated_at.utcoffset().total_seconds() == 9 * 60 * 60


def test_normalize_parking_lot_handles_missing_counts_as_none():
    row = dict(SAMPLE_ROW)
    row["TPKCT"] = ""
    row["NOW_PRK_VHCL_CNT"] = None

    lot = normalize_parking_lot(row)

    assert lot.total_spaces is None
    assert lot.occupied_spaces is None
    assert lot.available_spaces is None


def test_build_api_url_uses_key_format_and_range():
    url = build_api_url("sample", start=1, end=5)

    assert url == "http://openapi.seoul.go.kr:8088/sample/json/GetParkingInfo/1/5/"
