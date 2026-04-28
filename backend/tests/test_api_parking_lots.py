from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import connect, create_schema
from app.main import create_app
from app.models import ParkingLotRecord, upsert_parking_lot


def seed_record(conn, **overrides):
    data = {
        "id": "171721",
        "name": "세종로 공영주차장(시)",
        "address": "종로구 세종로 80-1",
        "lat": 37.5735,
        "lng": 126.9751,
        "total_spaces": 1260,
        "occupied_spaces": 457,
        "updated_at": datetime.now(timezone.utc) - timedelta(minutes=3),
        "raw_json": {"PKLT_CD": "171721"},
    }
    data.update(overrides)
    upsert_parking_lot(conn, ParkingLotRecord(**data))


def make_client():
    conn = connect(":memory:")
    create_schema(conn)
    return TestClient(create_app(conn)), conn


def test_health_returns_ok():
    client, _conn = make_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parking_lots_filters_by_radius_and_returns_score():
    client, conn = make_client()
    seed_record(
        conn,
        id="near",
        name="가까운 주차장",
        lat=37.5665,
        lng=126.9780,
        total_spaces=100,
        occupied_spaces=20,
    )
    seed_record(conn, id="far", name="먼 주차장", lat=37.6500, lng=127.1000)

    response = client.get("/api/parking-lots?lat=37.5665&lng=126.9780&radius_m=500")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == ["near"]
    item = body["items"][0]
    assert item["available_spaces"] == 80
    assert item["score"] >= 75
    assert item["label"] == "가능성 높음"
    assert item["distance_m"] == 0


def test_parking_lots_sorts_by_distance():
    client, conn = make_client()
    seed_record(conn, id="second", name="조금 먼 주차장", lat=37.5675, lng=126.9780)
    seed_record(conn, id="first", name="가장 가까운 주차장", lat=37.5666, lng=126.9780)

    response = client.get("/api/parking-lots?lat=37.5665&lng=126.9780&radius_m=500")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["first", "second"]


def test_parking_lots_rejects_invalid_radius():
    client, _conn = make_client()

    response = client.get("/api/parking-lots?lat=37.5665&lng=126.9780&radius_m=0")

    assert response.status_code == 422
