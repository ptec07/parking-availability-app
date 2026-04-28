from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ParkingScore:
    score: int
    label: str
    reason: str


def score_parking_lot(
    total_spaces: int | float,
    occupied_spaces: int | float,
    updated_at: datetime,
    arrival_time: datetime,
    distance_m: int | float,
    is_open: bool,
) -> ParkingScore:
    """Return an explainable v0 parking availability score from 0 to 100."""
    if total_spaces <= 0:
        return ParkingScore(score=0, label="확인 필요", reason="전체 주차면수 데이터가 부족합니다.")

    if not is_open:
        return ParkingScore(score=0, label="어려움", reason="도착 예정 시각에는 운영하지 않습니다.")

    available_spaces = max(float(total_spaces) - float(occupied_spaces), 0.0)
    availability_ratio = min(available_spaces / float(total_spaces), 1.0)
    availability_score = availability_ratio * 60

    freshness_score = _freshness_score(updated_at, arrival_time)
    distance_score = _distance_score(float(distance_m))
    time_score = _time_score(arrival_time)

    score = round(max(0, min(100, availability_score + freshness_score + distance_score + time_score)))
    label = _label_for(score)
    reason = _reason_for(available_spaces, total_spaces, freshness_score, distance_score)
    return ParkingScore(score=score, label=label, reason=reason)


def _freshness_score(updated_at: datetime, arrival_time: datetime) -> float:
    age_minutes = abs((arrival_time - updated_at).total_seconds()) / 60
    if age_minutes <= 20:
        return 15
    if age_minutes <= 40:
        return 10
    if age_minutes <= 60:
        return 6
    if age_minutes <= 120:
        return 2
    return 0


def _distance_score(distance_m: float) -> float:
    if distance_m <= 300:
        return 10
    if distance_m <= 500:
        return 8
    if distance_m <= 800:
        return 5
    if distance_m <= 1000:
        return 3
    return 0


def _time_score(arrival_time: datetime) -> float:
    hour = arrival_time.hour
    if 7 <= hour <= 9 or 18 <= hour <= 20:
        return 8
    if 11 <= hour <= 14 or 16 <= hour <= 17:
        return 10
    return 15


def _label_for(score: int) -> str:
    if score >= 75:
        return "가능성 높음"
    if score >= 50:
        return "보통"
    if score >= 25:
        return "가능성 낮음"
    return "어려움"


def _reason_for(available_spaces: float, total_spaces: int | float, freshness_score: float, distance_score: float) -> str:
    parts = [f"잔여면수 약 {int(available_spaces)} / 전체 {int(total_spaces)}면"]
    if freshness_score >= 10:
        parts.append("데이터가 최신입니다")
    elif freshness_score <= 2:
        parts.append("데이터가 오래되어 신뢰도가 낮습니다")

    if distance_score >= 8:
        parts.append("목적지와 가깝습니다")
    elif distance_score <= 3:
        parts.append("목적지와 거리가 있습니다")

    return ", ".join(parts) + "."
