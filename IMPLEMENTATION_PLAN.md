# 주차될까 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 서울 공영주차장 실시간 데이터를 사용해 목적지 주변 주차 가능성을 점수화하는 PWA MVP를 만든다.

**Architecture:** FastAPI 백엔드가 서울 열린데이터광장 `GetParkingInfo` 데이터를 수집·정규화하고, Kakao Local API로 주소를 좌표화해 캐시한다. React/Vite PWA 프론트엔드는 Kakao Maps 위에 주차장 핀과 카드 리스트를 표시한다. 예측은 v0에서 설명 가능한 규칙 기반 점수 함수로 구현한다.

**Tech Stack:** Python 3, FastAPI, pytest, httpx, SQLite, React, Vite, TypeScript, Vitest, Kakao Maps JavaScript SDK, Kakao Local REST API.

---

## Phase 0: 프로젝트 스캐폴드

### Task 1: 안전한 프로젝트 구조 생성

**Status:** 완료 — `backend/`, `frontend/`, `.env.example`, `.gitignore` 생성 및 기존 문서 보존 확인.

**Objective:** 기존 파일을 덮어쓰지 않고 앱 기본 디렉터리 구조를 만든다.

**Files:**
- Create: `backend/`
- Create: `frontend/`
- Create: `.env.example`
- Create: `.gitignore`

**Steps:**

1. 현재 폴더가 `/home/ptec07/.hermes/hermes-agent/workforce/parking-availability-app`인지 확인한다.
2. 기존 `PLAN.md`, `DECISIONS.md`, `DATA_SOURCES.md`, `PRD.md`, `IMPLEMENTATION_PLAN.md`는 보존한다.
3. `backend/`와 `frontend/`가 이미 있으면 중단하고 확인한다.
4. 새 폴더만 생성한다.

**Verification:**

```bash
find /home/ptec07/.hermes/hermes-agent/workforce/parking-availability-app -maxdepth 2 -type f | sort
```

Expected: 기획 문서와 `.env.example`, `.gitignore`만 보이며 기존 문서가 유지된다.

---

## Phase 1: 백엔드 핵심 도메인

### Task 2: 주차 가능성 점수 함수 테스트 작성

**Status:** 완료 — `tests/test_scoring.py`를 먼저 작성해 `ModuleNotFoundError: No module named 'app.scoring'` 실패를 확인했고, `app/scoring.py` 구현 후 `4 passed` 확인.

**Objective:** 규칙 기반 점수 함수의 기대 동작을 먼저 테스트한다.

**Files:**
- Create: `backend/tests/test_scoring.py`
- Create: `backend/app/scoring.py`

**Step 1: Write failing test**

```python
from datetime import datetime, timezone, timedelta

from app.scoring import score_parking_lot


def test_closed_parking_lot_scores_zero():
    result = score_parking_lot(
        total_spaces=100,
        occupied_spaces=20,
        updated_at=datetime.now(timezone.utc),
        arrival_time=datetime.now(timezone.utc),
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
```

**Step 2: Run test to verify failure**

```bash
cd backend
python3 -m pytest tests/test_scoring.py -q
```

Expected: FAIL because `app.scoring` does not exist or `score_parking_lot` is not implemented.

**Step 3: Write minimal implementation**

Implement:

- `ParkingScore` dataclass or Pydantic model
- `score_parking_lot(...)`
- label thresholds
- freshness score
- distance score

**Step 4: Run test to verify pass**

```bash
cd backend
python3 -m pytest tests/test_scoring.py -q
```

Expected: PASS.

---

### Task 3: 서울 GetParkingInfo 클라이언트 테스트 작성

**Status:** 완료 — `tests/test_seoul_client.py`를 먼저 작성해 `ModuleNotFoundError: No module named 'app.seoul_parking'` 실패를 확인했고, `app/seoul_parking.py` 구현 후 해당 테스트 `5 passed`, backend 전체 `9 passed` 확인.

**Objective:** 서울 API 응답을 앱 내부 모델로 정규화한다.

**Files:**
- Create: `backend/tests/test_seoul_client.py`
- Create: `backend/app/seoul_parking.py`

**Test cases:**

- `NOW_PRK_VHCL_CNT`를 현재 주차 차량 수로 해석한다.
- `available_spaces = TPKCT - NOW_PRK_VHCL_CNT`로 계산한다.
- `PKLT_CD`, `PKLT_NM`, `ADDR`, `NOW_PRK_VHCL_UPDT_TM`를 보존한다.
- 갱신 시각 문자열을 timezone-aware datetime으로 변환한다.

**Verification:**

```bash
cd backend
python3 -m pytest tests/test_seoul_client.py -q
```

Expected first: FAIL, after implementation: PASS.

---

### Task 4: 좌표 캐시 모델 작성

**Status:** 완료 — `tests/test_models.py`를 먼저 작성해 `ModuleNotFoundError: No module named 'app.db'` 실패를 확인했고, `app/db.py`와 `app/models.py` 구현 후 해당 테스트 `4 passed`, backend 전체 `13 passed` 확인.

**Objective:** Kakao 지오코딩 결과를 DB에 저장해 반복 호출을 줄인다.

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/test_models.py`

**Data model:**

```text
parking_lots
- id TEXT PRIMARY KEY
- name TEXT
- address TEXT
- lat REAL NULL
- lng REAL NULL
- total_spaces INTEGER
- occupied_spaces INTEGER
- updated_at TEXT
- raw_json TEXT
```

**Verification:**

- SQLite in-memory DB에서 테이블 생성 테스트
- upsert 테스트

---

### Task 5: 반경 검색 API 작성

**Status:** 완료 — `tests/test_api_parking_lots.py`를 먼저 작성해 import 실패를 확인했고, `app/main.py` 구현 후 SQLite thread 오류를 `check_same_thread=False`로 수정했다. 해당 테스트 `4 passed`, backend 전체 `17 passed` 확인.

**Objective:** 목적지 좌표 주변 주차장을 거리순으로 반환한다.

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api_parking_lots.py`

**Endpoint:**

```http
GET /api/parking-lots?lat=37.5665&lng=126.9780&radius_m=500
```

**Verification:**

```bash
cd backend
python3 -m pytest tests/test_api_parking_lots.py -q
```

Expected: seeded test DB 기준으로 반경 내 주차장만 반환.

---

## Phase 2: 데이터 동기화

### Task 6: 서울 주차 데이터 sync 명령 작성

**Status:** 완료 — `tests/test_sync.py`를 먼저 작성해 `ModuleNotFoundError: No module named 'app.sync'` 실패를 확인했고, `app/sync.py` 구현 후 해당 테스트 `3 passed`, backend 전체 `20 passed` 확인. 실제 CLI 명령은 아직 미구현이며 sync 함수/HTTP 클라이언트 기반만 완료.

**Objective:** 서울 API에서 주차장 상태를 가져와 DB에 저장한다.

**Files:**
- Create: `backend/app/sync.py`
- Create: `backend/tests/test_sync.py`

**Behavior:**

- `SEOUL_OPEN_API_KEY`가 있으면 실제 키 사용
- 없으면 개발 모드에서 `sample` 키 사용 가능
- API 페이지네이션 처리
- `PKLT_CD` 기준 upsert

**Verification:**

- Mock HTTP 응답으로 sync 테스트
- 실제 API 통합 테스트는 별도 마커 `integration`으로 분리

---

### Task 7: Kakao Local geocoding 클라이언트 작성

**Status:** 완료 — `tests/test_kakao_local.py`를 먼저 작성해 `ModuleNotFoundError: No module named 'app.kakao_local'` 실패를 확인했고, `app/kakao_local.py`와 좌표 업데이트 헬퍼 구현 후 해당 테스트 `4 passed`, backend 전체 `24 passed` 확인.

**Objective:** 주소를 좌표로 바꾸고 캐시한다.

**Files:**
- Create: `backend/app/kakao_local.py`
- Create: `backend/tests/test_kakao_local.py`

**Behavior:**

- `KAKAO_REST_API_KEY` 환경변수 사용
- API 실패 시 앱 전체 실패가 아니라 해당 주차장 좌표만 `NULL`
- 이미 좌표가 있으면 재호출하지 않음

---

## Phase 3: 프론트엔드 MVP

### Task 8: Vite React 앱 생성

**Status:** 완료 — `frontend/` 경로가 없음을 확인한 뒤 Vite React TypeScript/Vitest 기본 구조를 생성했다. `App.test.tsx`를 먼저 작성해 `Failed to resolve import "./App"` 실패를 확인했고, 최소 `App.tsx`/`main.tsx`/스타일 구현 후 frontend 테스트 `1 passed`, `npm run build` 성공, backend 전체 `24 passed` 확인. 빌드 중 `@types/node` 누락으로 1차 실패했고 devDependency 추가로 해결했다.

**Objective:** PWA의 기본 프론트엔드 구조를 만든다.

**Files:**
- Create under: `frontend/`

**Command:**

```bash
cd /home/ptec07/.hermes/hermes-agent/workforce/parking-availability-app
npm create vite@latest frontend -- --template react-ts
```

**Safety:** `frontend/`가 이미 있으면 실행하지 않는다.

**Verification:**

```bash
cd frontend
npm install
npm run build
```

---

### Task 9: 주차장 카드 컴포넌트 테스트 작성

**Status:** 완료 — `ParkingLotCard.test.tsx`를 먼저 작성해 `Failed to resolve import "./ParkingLotCard"` 실패를 확인했고, `ParkingLotCard.tsx`와 카드 스타일 구현 후 해당 테스트 `3 passed`, frontend 전체 `4 passed`, `npm run build` 성공, backend 전체 `24 passed` 확인.

**Objective:** 점수/라벨/잔여면수 표시를 프론트에서 검증한다.

**Files:**
- Create: `frontend/src/components/ParkingLotCard.tsx`
- Create: `frontend/src/components/ParkingLotCard.test.tsx`

**Test cases:**

- 가능성 높음 카드가 초록 상태로 표시된다.
- 갱신 시각과 잔여면수가 표시된다.
- 데이터 부족일 때 회색 상태로 표시된다.

---

### Task 10: 지도/리스트 화면 작성

**Status:** 완료 — `SearchResultsPage.test.tsx`를 먼저 작성해 `Failed to resolve import "./SearchResultsPage"` 실패를 확인했고, `/api/parking-lots` 호출·지도 미리보기·카드 리스트·가능성/거리순 정렬·빈 상태·오류 상태를 구현했다. `App` CTA로 서울시청 데모 검색 결과 화면을 연결했고, frontend 전체 `9 passed`, `npm run build` 성공, backend 전체 `24 passed` 확인.

**Objective:** API 결과를 지도 핀과 리스트로 동시에 보여준다.

**Files:**
- Create: `frontend/src/pages/SearchResultsPage.tsx`
- Modify: `frontend/src/App.tsx`

**Behavior:**

- 목적지 좌표를 기준으로 `/api/parking-lots` 호출
- 지도 핀 표시
- 하단 리스트 카드 표시
- 정렬: 가능성 높은 순 / 가까운 순

---

## Phase 4: 통합 검증

### Task 11: 로컬 통합 실행

**Status:** 완료 — `tests/test_runtime_app.py`와 `src/test/vite-config.test.ts`를 먼저 작성해 `create_default_app` import 실패와 Vite proxy 미설정 실패를 확인했다. `uvicorn app.main:app`용 기본 FastAPI app factory, SQLite schema 초기화, 데모 주차장 seed, Vite `/api` proxy를 구현했다. 데모 CTA는 서울시청 3km 반경으로 연결해 세종로/종묘/훈련원공원 데모 데이터가 보이도록 조정했다. backend 전체 `26 passed`, frontend 전체 `10 passed`, `npm run build` 성공, 실제 backend/frontend 로컬 서버 smoke 및 브라우저 QA까지 확인했다.

**Objective:** 백엔드와 프론트엔드를 동시에 띄워 MVP 흐름을 검증한다.

**Commands:**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

**Manual QA:**

- 서울시청 좌표 기준 검색
- 세종로/종묘/훈련원공원 주차장이 보이는지 확인
- 가능성 점수가 표시되는지 확인
- 데이터 갱신 시각이 보이는지 확인

---

## Phase 5: 배포 준비

### Task 12: Render/Vercel 배포 문서 작성

**Status:** 완료 — `tests/test_deployment_documentation.py`를 먼저 작성해 `DEPLOYMENT.md` 없음으로 인한 `FileNotFoundError` 실패를 확인했고, Render 백엔드/Vercel 프론트엔드 기준 배포 문서 `DEPLOYMENT.md`를 작성했다. 문서에는 필요한 환경변수, 서울/Kakao API 키 발급처, 로컬 실행법, Render/Vercel 설정, 배포 후 헬스체크, 보안 주의사항, 남은 배포 준비 작업을 포함했다. 문서 테스트 `3 passed`, backend 전체 `29 passed`, frontend 전체 `10 passed`, `npm run build` 성공 확인.

**Objective:** 백엔드 Render, 프론트 Vercel 기준의 배포 절차를 문서화한다.

**Files:**
- Create: `DEPLOYMENT.md`
- Create: `backend/tests/test_deployment_documentation.py`

**Include:**

- 필요한 환경변수
- API 키 발급처
- 로컬 실행법
- 배포 후 헬스체크

---

### Task 13: 실제 배포 준비 파일과 운영 연결 설정 추가

**Status:** 완료 — `tests/test_deployment_files.py`, `tests/test_cors.py`, `frontend/src/api.test.ts`를 먼저 작성해 `requirements.txt`, `render.yaml`, `frontend/vercel.json`, `app.main.create_app(..., frontend_origin=...)`, `src/api.ts` 부재 실패를 확인했다. 이후 Render Native Python 배포용 `backend/requirements.txt`와 루트 `render.yaml`, Vercel SPA fallback용 `frontend/vercel.json`, FastAPI CORS 설정, 프론트 `VITE_API_BASE_URL` 기반 API URL helper를 구현했다. targeted backend 배포/CORS 테스트 `4 passed`, targeted frontend API/App/Page 테스트 `9 passed`, backend 전체 `33 passed`, frontend 전체 `13 passed`, `npm run build` 성공 확인.

**Objective:** 문서만 있던 배포 준비를 실제 설정 파일과 운영 연결 코드로 구체화한다.

**Files:**
- Create: `backend/tests/test_deployment_files.py`
- Create: `backend/tests/test_cors.py`
- Create: `frontend/src/api.test.ts`
- Create: `backend/requirements.txt`
- Create: `render.yaml`
- Create: `frontend/vercel.json`
- Create: `frontend/src/api.ts`
- Update: `backend/app/main.py`
- Update: `frontend/src/pages/SearchResultsPage.tsx`
- Update: `.env.example`
- Update: `DEPLOYMENT.md`

**Include:**

- Render Native Python blueprint
- Vercel SPA fallback 설정
- `FRONTEND_ORIGIN` CORS 허용
- `VITE_API_BASE_URL` 기반 프론트 API URL 생성

---

### Task 14: 운영용 서울 sync / Kakao geocode CLI 추가

**Status:** 완료 — `tests/test_cli.py`를 먼저 작성해 `from app import cli` import 실패를 확인했고, `app/cli.py`를 추가해 `python -m app.cli sync-seoul-parking` 및 `python -m app.cli geocode-missing-coordinates` 명령을 구현했다. CLI는 `SEOUL_OPEN_API_KEY`, `KAKAO_REST_API_KEY`를 환경변수에서 읽고 실제 키를 출력하지 않으며, SQLite schema 생성 후 서울 주차 데이터 동기화와 좌표 누락 주차장 지오코딩을 실행한다. targeted CLI 테스트 `3 passed`, backend 전체 `36 passed`, frontend 전체 `13 passed`, `npm run build` 성공 확인.

**Objective:** 함수로만 있던 sync/geocode 흐름을 운영·배포 환경에서 실행 가능한 CLI로 만든다.

**Files:**
- Create: `backend/tests/test_cli.py`
- Create: `backend/app/cli.py`
- Update: `DEPLOYMENT.md`
- Update: `IMPLEMENTATION_PLAN.md`

**Include:**

- `sync-seoul-parking --db ... --page-size ...`
- `geocode-missing-coordinates --db ...`
- 필수 환경변수 누락 시 명확한 오류 코드
- 실제 API 키 출력 금지

---

### Task 15: Kakao Maps JavaScript SDK 지도 렌더링

**Status:** 완료 — `KakaoParkingMap.test.tsx`를 먼저 작성해 `Failed to resolve import "./KakaoParkingMap"` 실패를 확인했고, `KakaoParkingMap.tsx`를 추가해 Kakao Maps JavaScript SDK 로드, 목적지/주차장 마커 생성, 키 누락 시 안전한 지도 미리보기 fallback을 구현했다. `SearchResultsPage`는 API 응답의 `lat/lng`를 지도 컴포넌트에 전달하고 `VITE_KAKAO_JAVASCRIPT_KEY`를 사용한다. 루트 `.env`의 `VITE_KAKAO_JAVASCRIPT_KEY`를 frontend Vite 실행에서도 읽도록 `envDir: '..'` 설정도 추가했다. targeted frontend 지도/App/Page 테스트 `8 passed`, 최종 frontend 전체 `16 passed`, `npm run build` 성공, backend 전체 `36 passed` 확인.

**Objective:** 기존 지도 미리보기를 실제 Kakao 지도 SDK 기반 렌더링으로 교체하되, 테스트 환경과 키 누락 환경에서는 안전하게 fallback한다.

**Files:**
- Create: `frontend/src/components/KakaoParkingMap.tsx`
- Create: `frontend/src/components/KakaoParkingMap.test.tsx`
- Update: `frontend/src/pages/SearchResultsPage.tsx`
- Update: `frontend/src/pages/SearchResultsPage.test.tsx`
- Update: `frontend/src/styles.css`
- Update: `frontend/vite.config.ts`
- Create: `frontend/envConfig.ts`
- Update: `frontend/src/test/vite-config.test.ts`
- Update: `frontend/tsconfig.node.json`
- Update: `IMPLEMENTATION_PLAN.md`

**Include:**

- `VITE_KAKAO_JAVASCRIPT_KEY` 기반 SDK script 로드
- `autoload=false` 후 `kakao.maps.load(...)` 사용
- 목적지 마커 1개와 주차장 마커 N개 생성
- 키 누락/SDK 오류 시 지도 미리보기 fallback
- 테스트에서는 실제 Kakao 네트워크 호출 없이 SDK 객체 mock

---

### Task 16: 지오코딩 실패 15건 보정 및 실데이터 DB 반영

**Status:** 완료 — 기존 임시 DB에서 좌표가 없던 15건을 추출해 원인을 분석했다. 일부 주소는 서울 API 주소 끝에 불필요한 `0`이 붙어 있었고, 일부는 Kakao 주소 검색보다 키워드 검색이 더 적합했다. `tests/test_kakao_local.py`를 먼저 확장해 `build_geocode_queries` import 실패를 확인한 뒤, 주소 끝 `0` 제거, `서울 + 주소`, 괄호 설명 제거 주차장명, `서울 + 주차장명` 후보와 Kakao keyword fallback을 구현했다. 재실행 결과 임시 DB `checked=124 geocoded=15 skipped=109 failed=0`, 좌표 누락 `0`건을 확인했다. 기본 로컬 DB `backend/parking.db`도 실제 서울 데이터로 동기화/지오코딩했고, API smoke에서 서울시청 3km 반경 `count=43`을 확인했다.

**Files:**
- Update: `backend/app/kakao_local.py`
- Update: `backend/tests/test_kakao_local.py`
- Create/Update ignored local data: `backend/parking.db`

**Verification:**

```bash
cd backend
python3 -m pytest tests/test_kakao_local.py -q
python -m app.cli geocode-missing-coordinates --db /tmp/parking-availability-seoul-key-check.db
python -m app.cli sync-seoul-parking --db parking.db --page-size 200
python -m app.cli geocode-missing-coordinates --db parking.db
```

---

### Task 17: 목적지 검색 UI 및 `/api/geocode` 추가

**Status:** 완료 — `backend/tests/test_api_geocode.py`와 `frontend/src/App.test.tsx`를 먼저 작성/수정해 `/api/geocode` 미구현 및 목적지 입력창 부재 실패를 확인했다. 이후 FastAPI에 `GET /api/geocode?query=...`를 추가하고 Kakao REST API로 목적지 좌표를 변환하도록 구현했다. 프론트 홈 화면에는 목적지 입력 폼을 추가해 사용자가 `강남역` 같은 장소명을 입력하면 geocode → 주변 주차장 API → Kakao 지도/카드 결과 화면으로 이동한다. 브라우저 smoke에서 `강남역 주변 주차장`, Kakao 지도, 주차장 4곳, fallback 없음, `window.kakao === true`를 확인했다.

**Files:**
- Create: `backend/tests/test_api_geocode.py`
- Update: `backend/app/main.py`
- Update: `frontend/src/App.tsx`
- Update: `frontend/src/App.test.tsx`
- Update: `frontend/src/styles.css`

**Verification:**

```bash
cd backend
PARKING_DB_PATH=parking.db python3 -m pytest tests/test_api_geocode.py -q
PARKING_DB_PATH=parking.db python3 -m pytest tests -q
cd frontend
npm test -- --run
npm run build
```

Final observed results:

```text
backend: 42 passed
frontend: 6 test files / 17 tests passed
frontend build: success
browser smoke: 강남역 검색 결과 4곳 + Kakao 지도 정상
```

---

### Task 18: Production 배포 및 Vercel Serverless API fallback

**Status:** 완료 — GitHub 별도 repo(`https://github.com/ptec07/parking-availability-app`)를 생성/push하고 Vercel production에 배포했다. Render backend는 private repo fetch 문제로 우선 보류하고, production MVP 검색을 살리기 위해 Vercel same-origin Serverless API fallback을 구현했다. TypeScript API handler는 production에서 `FUNCTION_INVOCATION_FAILED`가 발생해 CommonJS function(`frontend/api/*.js`)으로 전환했다. `backend/parking.db`의 실데이터를 `parking_lots.json`으로 export하여 `/api/parking-lots`가 SQLite 없이 반경 검색/점수화를 수행한다. 최종 production smoke에서 `강남역` geocode HTTP 200, parking-lots `count=4`, 브라우저 결과 화면/Kakao 지도/주차장 카드 4곳/console error 없음 확인.

**Files:**
- Create: `frontend/src/serverlessParkingCore.test.ts`
- Create: `frontend/src/serverlessParkingCore.ts`
- Create: `frontend/src/data/parking_lots.json`
- Create: `frontend/api/_core.js`
- Create: `frontend/api/geocode.js`
- Create: `frontend/api/parking-lots.js`
- Create: `frontend/api/parking_lots.json`
- Update: `frontend/package.json`
- Update: `frontend/package-lock.json`
- Update: `DEPLOYMENT.md`

**Verification:**

```bash
cd frontend
npm test -- --run
npm run build
VITE_API_BASE_URL=/api npx vercel build --prod
npx vercel deploy --prebuilt --prod --yes
```

Final observed results:

```text
production URL: https://parking-availability-app.vercel.app
/api/geocode?query=강남역: 200, lat=37.49808633653005, lng=127.02800140627488
/api/parking-lots?...강남역 좌표...: 200, count=4
browser smoke: 강남역 주변 주차장 + Kakao 지도 + 카드 4곳 정상
```

---

## Open Questions

1. 서울 열린데이터광장 인증키를 발급받을 것인가? — 해결: 로컬 `.env`에 저장했고 실제 sync/geocode 및 기본 DB 반영 완료.
2. Kakao JavaScript Key / REST API Key를 사용할 수 있는가? — 해결: 로컬 `.env`에 저장했고 REST 목적지 검색, 주차장 지오코딩, JavaScript SDK 지도 렌더링 모두 확인 완료.
3. MVP를 실제 배포까지 바로 진행할 것인가? — 배포 준비는 완료됐지만 현재 환경에는 별도 GitHub repo/Render/Vercel 인증이 없어 실제 배포는 차단됨.
