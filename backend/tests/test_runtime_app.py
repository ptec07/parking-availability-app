from fastapi.testclient import TestClient

from app.main import create_default_app


def test_default_app_creates_schema_and_seeds_demo_parking_lots(tmp_path):
    database_path = tmp_path / "parking.db"
    app = create_default_app(database=str(database_path), seed_demo_data=True)
    client = TestClient(app)

    health = client.get("/api/health")
    response = client.get("/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000")

    assert health.status_code == 200
    assert database_path.exists()
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["items"])
    assert {item["name"] for item in body["items"]} >= {"세종로 공영주차장(시)", "종묘 공영주차장", "훈련원공원 공영주차장"}


def test_default_app_can_start_without_demo_seed(tmp_path):
    database_path = tmp_path / "parking-empty.db"
    app = create_default_app(database=str(database_path), seed_demo_data=False)
    client = TestClient(app)

    response = client.get("/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000")

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0}
