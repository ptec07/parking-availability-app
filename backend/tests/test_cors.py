from fastapi.testclient import TestClient

from app.db import connect, create_schema
from app.main import create_app


def test_create_app_allows_configured_frontend_origin_for_cors():
    conn = connect(":memory:")
    create_schema(conn)
    client = TestClient(create_app(conn, frontend_origin="https://parking.vercel.app"))

    response = client.options(
        "/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000",
        headers={
            "Origin": "https://parking.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://parking.vercel.app"
