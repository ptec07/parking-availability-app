from datetime import datetime, timedelta, timezone
from io import StringIO

from app.db import connect, create_schema
from app.models import ParkingLotRecord, get_parking_lot, upsert_parking_lot
from app.sync import InMemorySeoulParkingApi

SAMPLE_RESPONSE = {
    "GetParkingInfo": {
        "list_total_count": 1,
        "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
        "row": [
            {
                "PKLT_CD": "171721",
                "PKLT_NM": "세종로 공영주차장(시)",
                "ADDR": "종로구 세종로 80-1",
                "TPKCT": 1260.0,
                "NOW_PRK_VHCL_CNT": 457.0,
                "NOW_PRK_VHCL_UPDT_TM": "2026-04-28 08:31:23",
            }
        ],
    }
}


def test_sync_seoul_parking_cli_uses_env_key_and_writes_database(tmp_path, monkeypatch):
    from app import cli

    db_path = tmp_path / "parking.db"
    created_api_keys = []

    def fake_api_factory(api_key):
        created_api_keys.append(api_key)
        return InMemorySeoulParkingApi([SAMPLE_RESPONSE])

    monkeypatch.setattr(cli, "HttpSeoulParkingApi", fake_api_factory)
    stdout = StringIO()

    exit_code = cli.main(
        ["sync-seoul-parking", "--db", str(db_path), "--page-size", "100"],
        env={"SEOUL_OPEN_API_KEY": "test-seoul-key"},
        stdout=stdout,
    )

    assert exit_code == 0
    assert created_api_keys == ["test-seoul-key"]
    assert "fetched=1" in stdout.getvalue()
    assert "saved=1" in stdout.getvalue()

    conn = connect(str(db_path))
    saved = get_parking_lot(conn, "171721")
    assert saved is not None
    assert saved.name == "세종로 공영주차장(시)"
    assert saved.total_spaces == 1260
    assert saved.occupied_spaces == 457


def test_geocode_missing_coordinates_cli_uses_env_key_and_updates_database(tmp_path, monkeypatch):
    from app import cli
    from app.kakao_local import GeocodeResult, InMemoryKakaoLocalApi

    db_path = tmp_path / "parking.db"
    conn = connect(str(db_path))
    create_schema(conn)
    upsert_parking_lot(
        conn,
        ParkingLotRecord(
            id="171721",
            name="세종로 공영주차장(시)",
            address="종로구 세종로 80-1",
            lat=None,
            lng=None,
            total_spaces=1260,
            occupied_spaces=457,
            updated_at=datetime(2026, 4, 28, 8, 31, 23, tzinfo=timezone(timedelta(hours=9))),
            raw_json={"PKLT_CD": "171721"},
        ),
    )
    conn.close()
    created_api_keys = []

    def fake_api_factory(api_key):
        created_api_keys.append(api_key)
        return InMemoryKakaoLocalApi(
            {"종로구 세종로 80-1": GeocodeResult(lat=37.573573, lng=126.975102, address_name="서울 종로구 세종로 80-1")}
        )

    monkeypatch.setattr(cli, "HttpKakaoLocalApi", fake_api_factory)
    stdout = StringIO()

    exit_code = cli.main(
        ["geocode-missing-coordinates", "--db", str(db_path)],
        env={"KAKAO_REST_API_KEY": "test-kakao-key"},
        stdout=stdout,
    )

    assert exit_code == 0
    assert created_api_keys == ["test-kakao-key"]
    assert "geocoded=1" in stdout.getvalue()
    assert "failed=0" in stdout.getvalue()

    conn = connect(str(db_path))
    saved = get_parking_lot(conn, "171721")
    assert saved.lat == 37.573573
    assert saved.lng == 126.975102


def test_cli_returns_error_without_required_secret(tmp_path):
    from app import cli

    stderr = StringIO()

    exit_code = cli.main(["sync-seoul-parking", "--db", str(tmp_path / "parking.db")], env={}, stderr=stderr)

    assert exit_code == 2
    assert "SEOUL_OPEN_API_KEY" in stderr.getvalue()
    assert "test-seoul-key" not in stderr.getvalue()
