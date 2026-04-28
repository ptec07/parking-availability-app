from __future__ import annotations

import math
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.db import connect, create_schema
from app.kakao_local import HttpKakaoLocalApi, KakaoLocalApi
from app.models import ParkingLotRecord, list_parking_lots, upsert_parking_lot
from app.scoring import score_parking_lot


def create_app(
    conn: sqlite3.Connection,
    frontend_origin: str | None = None,
    kakao_local_api: KakaoLocalApi | None = None,
) -> FastAPI:
    app = FastAPI(title="주차될까 API")
    _configure_cors(app, frontend_origin)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/parking-lots")
    def parking_lots(
        lat: float,
        lng: float,
        radius_m: int = Query(default=500, gt=0, le=5000),
        arrival_time: datetime | None = None,
    ) -> dict[str, object]:
        arrival = arrival_time or datetime.now(timezone.utc)
        items: list[dict[str, object]] = []
        for record in list_parking_lots(conn):
            if record.lat is None or record.lng is None:
                continue
            distance_m = round(_haversine_m(lat, lng, record.lat, record.lng))
            if distance_m > radius_m:
                continue
            items.append(_serialize_record(record, distance_m, arrival))
        items.sort(key=lambda item: (item["distance_m"], item["name"]))
        return {"items": items, "count": len(items)}

    @app.get("/api/geocode")
    def geocode_destination(query: str = Query(min_length=1)) -> dict[str, object]:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise HTTPException(status_code=422, detail="Query is required")
        api = kakao_local_api or _create_kakao_local_api_from_env()
        result = api.geocode_address(normalized_query)
        if result is None:
            raise HTTPException(status_code=404, detail="Destination not found")
        return {
            "query": normalized_query,
            "label": normalized_query,
            "lat": result.lat,
            "lng": result.lng,
            "address_name": result.address_name,
        }

    return app


def create_default_app(database: str | None = None, seed_demo_data: bool | None = None) -> FastAPI:
    """Create the uvicorn-ready local app with schema initialization.

    Tests can still use create_app(conn) for isolated in-memory DBs. This factory is
    for local integration runs such as `uvicorn app.main:app`.
    """
    database_path = database or os.environ.get("PARKING_DB_PATH", "parking.db")
    should_seed_demo_data = _should_seed_demo_data(seed_demo_data)
    conn = connect(database_path)
    create_schema(conn)
    if should_seed_demo_data:
        seed_demo_parking_lots(conn)
    return create_app(conn, frontend_origin=os.environ.get("FRONTEND_ORIGIN"))


def _create_kakao_local_api_from_env() -> HttpKakaoLocalApi:
    api_key = os.environ.get("KAKAO_REST_API_KEY", "")
    if not api_key.strip():
        raise HTTPException(status_code=503, detail="Kakao REST API key is not configured")
    return HttpKakaoLocalApi(api_key)


def _configure_cors(app: FastAPI, frontend_origin: str | None) -> None:
    origins = [frontend_origin] if frontend_origin else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):(4\d{3}|5\d{3})",
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )


def _should_seed_demo_data(seed_demo_data: bool | None) -> bool:
    if seed_demo_data is not None:
        return seed_demo_data
    value = os.environ.get("PARKING_SEED_DEMO_DATA", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def seed_demo_parking_lots(conn: sqlite3.Connection) -> None:
    existing_count = conn.execute("SELECT COUNT(*) FROM parking_lots").fetchone()[0]
    if existing_count:
        return

    now = datetime.now(timezone.utc) - timedelta(minutes=3)
    demo_records = [
        ParkingLotRecord(
            id="171721",
            name="세종로 공영주차장(시)",
            address="종로구 세종로 80-1",
            lat=37.5735,
            lng=126.9751,
            total_spaces=1260,
            occupied_spaces=457,
            updated_at=now,
            raw_json={"source": "demo", "PKLT_CD": "171721"},
        ),
        ParkingLotRecord(
            id="171722",
            name="종묘 공영주차장",
            address="종로구 종로 157",
            lat=37.5706,
            lng=126.9947,
            total_spaces=1317,
            occupied_spaces=815,
            updated_at=now,
            raw_json={"source": "demo", "PKLT_CD": "171722"},
        ),
        ParkingLotRecord(
            id="171723",
            name="훈련원공원 공영주차장",
            address="중구 을지로 227",
            lat=37.5675,
            lng=127.0039,
            total_spaces=873,
            occupied_spaces=620,
            updated_at=now,
            raw_json={"source": "demo", "PKLT_CD": "171723"},
        ),
    ]
    for record in demo_records:
        upsert_parking_lot(conn, record)


app = create_default_app()


def _serialize_record(record: ParkingLotRecord, distance_m: int, arrival_time: datetime) -> dict[str, object]:
    total_spaces = record.total_spaces
    occupied_spaces = record.occupied_spaces
    available_spaces = None
    score = None
    label = "확인 필요"
    reason = "주차면수 데이터가 부족합니다."

    if total_spaces is not None and occupied_spaces is not None and record.updated_at is not None:
        available_spaces = max(total_spaces - occupied_spaces, 0)
        parking_score = score_parking_lot(
            total_spaces=total_spaces,
            occupied_spaces=occupied_spaces,
            updated_at=record.updated_at,
            arrival_time=arrival_time,
            distance_m=distance_m,
            is_open=True,
        )
        score = parking_score.score
        label = parking_score.label
        reason = parking_score.reason

    return {
        "id": record.id,
        "name": record.name,
        "address": record.address,
        "lat": record.lat,
        "lng": record.lng,
        "distance_m": distance_m,
        "total_spaces": total_spaces,
        "occupied_spaces": occupied_spaces,
        "available_spaces": available_spaces,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "score": score,
        "label": label,
        "reason": reason,
    }


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_m * c
