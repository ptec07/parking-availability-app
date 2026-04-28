from __future__ import annotations

import argparse
import os
import sys
from typing import Mapping, Sequence, TextIO

from app.db import connect, create_schema
from app.kakao_local import HttpKakaoLocalApi, geocode_missing_parking_lot_coordinates
from app.sync import HttpSeoulParkingApi, sync_seoul_parking

DEFAULT_DB_PATH = "parking.db"
DEFAULT_PAGE_SIZE = 100


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    env = os.environ if env is None else env
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "sync-seoul-parking":
        return _sync_seoul_parking(args, env, stdout, stderr)
    if args.command == "geocode-missing-coordinates":
        return _geocode_missing_coordinates(args, env, stdout, stderr)

    parser.print_help(stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="주차될까 운영용 데이터 관리 CLI")
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync-seoul-parking", help="서울 열린데이터광장 주차정보를 SQLite DB에 동기화")
    sync_parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB 파일 경로")
    sync_parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help="서울 API page size")

    geocode_parser = subparsers.add_parser("geocode-missing-coordinates", help="좌표가 없는 주차장을 Kakao Local API로 지오코딩")
    geocode_parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB 파일 경로")

    return parser


def _sync_seoul_parking(args: argparse.Namespace, env: Mapping[str, str], stdout: TextIO, stderr: TextIO) -> int:
    api_key = _required_env(env, "SEOUL_OPEN_API_KEY", stderr)
    if api_key is None:
        return 2

    conn = connect(args.db)
    create_schema(conn)
    result = sync_seoul_parking(conn, HttpSeoulParkingApi(api_key), page_size=args.page_size)
    print(f"sync-seoul-parking fetched={result.fetched_count} saved={result.saved_count} db={args.db}", file=stdout)
    return 0


def _geocode_missing_coordinates(args: argparse.Namespace, env: Mapping[str, str], stdout: TextIO, stderr: TextIO) -> int:
    api_key = _required_env(env, "KAKAO_REST_API_KEY", stderr)
    if api_key is None:
        return 2

    conn = connect(args.db)
    create_schema(conn)
    result = geocode_missing_parking_lot_coordinates(conn, HttpKakaoLocalApi(api_key))
    print(
        "geocode-missing-coordinates "
        f"checked={result.checked_count} geocoded={result.geocoded_count} "
        f"skipped={result.skipped_count} failed={result.failed_count} db={args.db}",
        file=stdout,
    )
    return 0


def _required_env(env: Mapping[str, str], name: str, stderr: TextIO) -> str | None:
    value = env.get(name, "").strip()
    if value:
        return value
    print(f"Missing required environment variable: {name}", file=stderr)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
