from datetime import datetime, timedelta, timezone

from app.scoring import score_parking_lot


def test_closed_parking_lot_scores_zero():
    now = datetime.now(timezone.utc)

    result = score_parking_lot(
        total_spaces=100,
        occupied_spaces=20,
        updated_at=now,
        arrival_time=now,
        distance_m=100,
        is_open=False,
    )

    assert result.score == 0
    assert result.label == "어려움"


def test_available_fresh_nearby_parking_lot_scores_high():
    now = datetime.now(timezone.utc)

    result = score_parking_lot(
        total_spaces=100,
        occupied_spaces=20,
        updated_at=now - timedelta(minutes=3),
        arrival_time=now + timedelta(minutes=20),
        distance_m=250,
        is_open=True,
    )

    assert result.score >= 75
    assert result.label == "가능성 높음"
    assert "잔여면수" in result.reason


def test_stale_data_reduces_confidence():
    now = datetime.now(timezone.utc)

    fresh = score_parking_lot(100, 50, now - timedelta(minutes=3), now, 300, True)
    stale = score_parking_lot(100, 50, now - timedelta(hours=2), now, 300, True)

    assert stale.score < fresh.score


def test_zero_total_spaces_returns_data_insufficient():
    now = datetime.now(timezone.utc)

    result = score_parking_lot(0, 0, now, now, 100, True)

    assert result.score == 0
    assert result.label == "확인 필요"
