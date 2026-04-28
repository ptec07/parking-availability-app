from app.db import connect, create_schema
from app.kakao_local import GeocodeResult, InMemoryKakaoLocalApi
from app.main import create_app
from fastapi.testclient import TestClient


def make_client(api):
    conn = connect(":memory:")
    create_schema(conn)
    return TestClient(create_app(conn, kakao_local_api=api))


def test_geocode_endpoint_returns_destination_coordinates_for_query():
    api = InMemoryKakaoLocalApi(
        {
            "강남역": GeocodeResult(
                lat=37.497952,
                lng=127.027619,
                address_name="서울 강남구 강남대로 지하 396",
            )
        }
    )
    client = make_client(api)

    response = client.get("/api/geocode", params={"query": "강남역"})

    assert response.status_code == 200
    assert response.json() == {
        "query": "강남역",
        "label": "강남역",
        "lat": 37.497952,
        "lng": 127.027619,
        "address_name": "서울 강남구 강남대로 지하 396",
    }
    assert api.queries == ["강남역"]


def test_geocode_endpoint_returns_404_when_kakao_has_no_match():
    client = make_client(InMemoryKakaoLocalApi({"없는장소": None}))

    response = client.get("/api/geocode", params={"query": "없는장소"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Destination not found"


def test_geocode_endpoint_rejects_blank_query_before_calling_kakao():
    api = InMemoryKakaoLocalApi({})
    client = make_client(api)

    response = client.get("/api/geocode", params={"query": "   "})

    assert response.status_code == 422
    assert api.queries == []
