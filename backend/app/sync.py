from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Protocol, Any

from app.models import ParkingLotRecord, get_parking_lot, upsert_parking_lot
from app.seoul_parking import build_api_url, normalize_parking_lot


class SeoulParkingApi(Protocol):
    def fetch(self, start: int, end: int) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class SyncResult:
    fetched_count: int
    saved_count: int


class HttpSeoulParkingApi:
    def __init__(self, api_key: str, timeout: int = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def fetch(self, start: int, end: int) -> dict[str, Any]:
        url = build_api_url(self.api_key, start, end)
        request = urllib.request.Request(url, headers={"User-Agent": "parking-availability-app/0.1"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


class InMemorySeoulParkingApi:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[int, int]] = []

    def fetch(self, start: int, end: int) -> dict[str, Any]:
        self.calls.append((start, end))
        if not self._responses:
            raise RuntimeError("No in-memory Seoul parking API response left")
        return self._responses.pop(0)


def sync_seoul_parking(conn, api: SeoulParkingApi, page_size: int = 100) -> SyncResult:
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    start = 1
    fetched_count = 0
    saved_count = 0
    total_count: int | None = None

    while total_count is None or fetched_count < total_count:
        end = start + page_size - 1
        payload = api.fetch(start, end)
        body = payload.get("GetParkingInfo", {})
        _raise_if_api_error(body)
        total_count = int(body.get("list_total_count") or 0)
        rows = body.get("row") or []
        if not rows:
            break

        for row in rows:
            normalized = normalize_parking_lot(row)
            existing = get_parking_lot(conn, normalized.id)
            record = ParkingLotRecord(
                id=normalized.id,
                name=normalized.name,
                address=normalized.address,
                lat=existing.lat if existing else None,
                lng=existing.lng if existing else None,
                total_spaces=normalized.total_spaces,
                occupied_spaces=normalized.occupied_spaces,
                updated_at=normalized.updated_at,
                raw_json=normalized.raw,
            )
            upsert_parking_lot(conn, record)
            saved_count += 1

        fetched_count += len(rows)
        start = end + 1

    return SyncResult(fetched_count=fetched_count, saved_count=saved_count)


def _raise_if_api_error(body: dict[str, Any]) -> None:
    result = body.get("RESULT") or {}
    code = result.get("CODE")
    if code and code != "INFO-000":
        message = result.get("MESSAGE") or "서울 주차 API 오류"
        raise RuntimeError(f"Seoul parking API error {code}: {message}")
