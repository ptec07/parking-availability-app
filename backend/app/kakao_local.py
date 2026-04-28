from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from app.models import list_parking_lots, update_parking_lot_coordinates

KAKAO_LOCAL_ADDRESS_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/address.json"
KAKAO_LOCAL_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


@dataclass(frozen=True)
class GeocodeResult:
    lat: float
    lng: float
    address_name: str


@dataclass(frozen=True)
class GeocodeSyncResult:
    checked_count: int
    geocoded_count: int
    skipped_count: int
    failed_count: int


class KakaoLocalApi(Protocol):
    def geocode_address(self, query: str) -> GeocodeResult | None:
        ...


class HttpKakaoLocalApi:
    def __init__(self, api_key: str, timeout: int = 10) -> None:
        if not api_key.strip():
            raise ValueError("Kakao REST API key is required")
        self.api_key = api_key.strip()
        self.timeout = timeout

    def geocode_address(self, query: str) -> GeocodeResult | None:
        address_result = self._request_geocode(KAKAO_LOCAL_ADDRESS_SEARCH_URL, query)
        if address_result is not None:
            return address_result
        return self._request_geocode(KAKAO_LOCAL_KEYWORD_SEARCH_URL, query)

    def _request_geocode(self, endpoint: str, query: str) -> GeocodeResult | None:
        params = urllib.parse.urlencode({"query": query})
        url = f"{endpoint}?{params}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"KakaoAK {self.api_key}",
                "User-Agent": "parking-availability-app/0.1",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return parse_geocode_response(payload)


class InMemoryKakaoLocalApi:
    def __init__(self, results_by_query: dict[str, GeocodeResult | None]) -> None:
        self.results_by_query = dict(results_by_query)
        self.queries: list[str] = []

    def geocode_address(self, query: str) -> GeocodeResult | None:
        self.queries.append(query)
        return self.results_by_query.get(query)


def build_geocode_queries(record) -> list[str]:
    queries: list[str] = []

    def add(query: str) -> None:
        normalized = " ".join(query.split())
        if normalized and normalized not in queries:
            queries.append(normalized)

    add(record.address)
    cleaned_address = re.sub(r"\s+0$", "", record.address).strip()
    add(cleaned_address)
    add(f"서울 {cleaned_address}")

    cleaned_name = re.sub(r"\([^)]*\)", "", record.name)
    cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip()
    add(cleaned_name)
    add(f"서울 {cleaned_name}")

    return queries


def parse_geocode_response(payload: dict[str, Any]) -> GeocodeResult | None:
    documents = payload.get("documents") or []
    if not documents:
        return None

    first = documents[0]
    try:
        lng = float(first["x"])
        lat = float(first["y"])
    except (KeyError, TypeError, ValueError):
        return None

    address_name = str(first.get("address_name") or first.get("road_address", {}).get("address_name") or "")
    return GeocodeResult(lat=lat, lng=lng, address_name=address_name)


def geocode_missing_parking_lot_coordinates(conn, api: KakaoLocalApi) -> GeocodeSyncResult:
    checked_count = 0
    geocoded_count = 0
    skipped_count = 0
    failed_count = 0

    for record in list_parking_lots(conn):
        checked_count += 1
        if record.lat is not None and record.lng is not None:
            skipped_count += 1
            continue
        if not record.address.strip():
            failed_count += 1
            continue

        result = None
        for query in build_geocode_queries(record):
            result = api.geocode_address(query)
            if result is not None:
                break
        if result is None:
            failed_count += 1
            continue

        update_parking_lot_coordinates(conn, record.id, result.lat, result.lng)
        geocoded_count += 1

    return GeocodeSyncResult(
        checked_count=checked_count,
        geocoded_count=geocoded_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
    )
