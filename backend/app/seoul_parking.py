from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

SEOUL_API_BASE_URL = "http://openapi.seoul.go.kr:8088"
KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class SeoulParkingLot:
    id: str
    name: str
    address: str
    parking_type_name: str | None
    operation_type_name: str | None
    phone: str | None
    status_code: str | None
    status_name: str | None
    total_spaces: int | None
    occupied_spaces: int | None
    available_spaces: int | None
    updated_at: datetime | None
    paid_name: str | None
    weekday_open_time: str | None
    weekday_close_time: str | None
    weekend_open_time: str | None
    weekend_close_time: str | None
    holiday_open_time: str | None
    holiday_close_time: str | None
    basic_fee: int | None
    basic_minutes: int | None
    additional_fee: int | None
    additional_minutes: int | None
    daily_max_fee: int | None
    raw: dict[str, Any]


def build_api_url(api_key: str, start: int, end: int) -> str:
    if start < 1:
        raise ValueError("start must be >= 1")
    if end < start:
        raise ValueError("end must be >= start")
    return f"{SEOUL_API_BASE_URL}/{api_key}/json/GetParkingInfo/{start}/{end}/"


def normalize_parking_lot(row: dict[str, Any]) -> SeoulParkingLot:
    total_spaces = _to_int(row.get("TPKCT"))
    occupied_spaces = _to_int(row.get("NOW_PRK_VHCL_CNT"))
    available_spaces = _available_spaces(total_spaces, occupied_spaces)

    return SeoulParkingLot(
        id=str(row.get("PKLT_CD") or ""),
        name=str(row.get("PKLT_NM") or ""),
        address=str(row.get("ADDR") or ""),
        parking_type_name=_to_optional_str(row.get("PRK_TYPE_NM")),
        operation_type_name=_to_optional_str(row.get("OPER_SE_NM")),
        phone=_to_optional_str(row.get("TELNO")),
        status_code=_to_optional_str(row.get("PRK_STTS_YN")),
        status_name=_to_optional_str(row.get("PRK_STTS_NM")),
        total_spaces=total_spaces,
        occupied_spaces=occupied_spaces,
        available_spaces=available_spaces,
        updated_at=_parse_kst_datetime(row.get("NOW_PRK_VHCL_UPDT_TM")),
        paid_name=_to_optional_str(row.get("PAY_YN_NM")),
        weekday_open_time=_to_optional_str(row.get("WD_OPER_BGNG_TM")),
        weekday_close_time=_to_optional_str(row.get("WD_OPER_END_TM")),
        weekend_open_time=_to_optional_str(row.get("WE_OPER_BGNG_TM")),
        weekend_close_time=_to_optional_str(row.get("WE_OPER_END_TM")),
        holiday_open_time=_to_optional_str(row.get("LHLDY_OPER_BGNG_TM")),
        holiday_close_time=_to_optional_str(row.get("LHLDY_OPER_END_TM")),
        basic_fee=_to_int(row.get("BSC_PRK_CRG")),
        basic_minutes=_to_int(row.get("BSC_PRK_HR")),
        additional_fee=_to_int(row.get("ADD_PRK_CRG")),
        additional_minutes=_to_int(row.get("ADD_PRK_HR")),
        daily_max_fee=_to_int(row.get("DAY_MAX_CRG")),
        raw=dict(row),
    )


def _available_spaces(total_spaces: int | None, occupied_spaces: int | None) -> int | None:
    if total_spaces is None or occupied_spaces is None:
        return None
    return max(total_spaces - occupied_spaces, 0)


def _parse_kst_datetime(value: Any) -> datetime | None:
    text = _to_optional_str(value)
    if text is None:
        return None
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
