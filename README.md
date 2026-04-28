# 주차될까

서울 공영주차장 실시간 데이터를 기반으로 목적지 주변의 주차 가능성을 보여주는 FastAPI + Vite/React MVP입니다.

- Backend: FastAPI, SQLite, pytest
- Frontend: Vite, React, TypeScript, Vitest
- Data: 서울 열린데이터광장 `GetParkingInfo`
- Map / Geocoding: Kakao Local REST API, Kakao Maps JavaScript SDK
- Deployment target: Render backend + Vercel frontend

## 주요 기능

- 서울 공영주차장 실시간 데이터 동기화
- Kakao Local API 기반 주차장 주소/목적지 지오코딩
- 목적지 검색: 예) `강남역`
- 반경 내 주차장 목록 및 Kakao 지도 표시
- 주차 가능성 점수화
  - 잔여면수
  - 데이터 최신성
  - 목적지와의 거리
- 지도 로딩 실패/키 누락 시 목록 기반 fallback UI

## 프로젝트 구조

```text
.
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── cli.py           # 운영용 sync/geocode CLI
│   │   ├── db.py            # SQLite 연결/schema
│   │   ├── kakao_local.py   # Kakao Local API client + fallback queries
│   │   ├── main.py          # FastAPI app and API routes
│   │   ├── models.py        # Parking lot persistence helpers
│   │   ├── scoring.py       # 주차 가능성 점수 로직
│   │   ├── seoul_parking.py # 서울 GetParkingInfo client/normalizer
│   │   └── sync.py          # 서울 데이터 동기화
│   ├── tests/
│   └── requirements.txt
├── frontend/                # Vite React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.tsx
│   │   └── api.ts
│   ├── vercel.json
│   └── package.json
├── render.yaml              # Render backend blueprint
├── DEPLOYMENT.md            # 배포 상세 가이드
└── IMPLEMENTATION_PLAN.md   # 구현 이력/검증 기록
```

## 필요한 API 키

루트에 `.env` 파일을 만들고 아래 값을 채웁니다. 실제 키는 commit하지 않습니다.

```bash
# Seoul Open API
SEOUL_OPEN_API_KEY=***

# Kakao APIs
KAKAO_REST_API_KEY=***
VITE_KAKAO_JAVASCRIPT_KEY=***

# Backend app
PORT=8000
PARKING_DB_PATH=./parking.db
PARKING_SEED_DEMO_DATA=0
FRONTEND_ORIGIN=http://127.0.0.1:5173
APP_ENV=development

# Frontend app
VITE_API_BASE_URL=/api
```

참고:

- `KAKAO_REST_API_KEY`는 backend/server-side 전용입니다.
- `VITE_KAKAO_JAVASCRIPT_KEY`는 browser에 노출되는 JavaScript 키이므로 Kakao Developers에서 Web 플랫폼 도메인을 제한해야 합니다.
- 로컬 개발 시 Kakao Developers에 다음 도메인을 등록합니다.
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`

## 로컬 실행

### 1. Backend 준비

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

이미 프로젝트 루트 `.env`에 API 키가 있다면 다음 순서로 실제 서울 데이터를 로컬 DB에 반영할 수 있습니다.

```bash
set -a
. ../.env
set +a

python -m app.cli sync-seoul-parking --db parking.db --page-size 200
python -m app.cli geocode-missing-coordinates --db parking.db
```

Backend 실행:

```bash
PARKING_DB_PATH=parking.db \
PARKING_SEED_DEMO_DATA=0 \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

헬스체크:

```bash
curl http://127.0.0.1:8000/api/health
```

### 2. Frontend 준비

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저에서 접속:

```text
http://127.0.0.1:5173/
```

목적지 입력창에 `강남역`처럼 장소명을 입력하면 backend `/api/geocode`를 거쳐 주변 주차장 결과 화면으로 이동합니다.

## API

### Health

```http
GET /api/health
```

예상 응답:

```json
{"status":"ok"}
```

### 목적지 지오코딩

```http
GET /api/geocode?query=강남역
```

예상 응답:

```json
{
  "query": "강남역",
  "lat": 37.49808633653005,
  "lng": 127.02800140627488,
  "address_name": "서울 강남구 역삼동 858"
}
```

### 주변 주차장 검색

```http
GET /api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000
```

예상 응답:

```json
{
  "items": [],
  "count": 0
}
```

실제 DB에 서울 데이터가 있으면 `items`에 주차장 카드에 필요한 이름, 주소, 좌표, 거리, 점수, 잔여면수 등이 포함됩니다.

## 테스트

Backend:

```bash
cd backend
PARKING_DB_PATH=parking.db python3 -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```

최근 검증 결과:

```text
backend: 42 passed
frontend: 6 files / 17 tests passed
frontend build: success
```

## 배포 개요

이 repo는 Render backend + Vercel frontend 배포를 기준으로 준비되어 있습니다.

### Render backend

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Blueprint: `render.yaml`

필수 환경변수:

```bash
PORT=8000
PARKING_DB_PATH=/var/data/parking.db
PARKING_SEED_DEMO_DATA=0
SEOUL_OPEN_API_KEY=***
KAKAO_REST_API_KEY=***
FRONTEND_ORIGIN=https://<vercel-project>.vercel.app
APP_ENV=production
```

운영 DB는 seed가 섞이지 않도록 새 DB에서 `sync-seoul-parking` 후 `geocode-missing-coordinates`를 실행하는 것을 권장합니다.

### Vercel frontend

- Project root: `frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- SPA fallback: `frontend/vercel.json`

필수 환경변수:

```bash
VITE_API_BASE_URL=https://<render-service>.onrender.com
VITE_KAKAO_JAVASCRIPT_KEY=***
```

배포 후 Kakao Developers의 JavaScript 키 Web 플랫폼 도메인에 실제 Vercel URL을 추가해야 지도 SDK가 차단되지 않습니다.

자세한 절차는 [`DEPLOYMENT.md`](./DEPLOYMENT.md)를 참고하세요.

## 보안 주의사항

- `.env`, SQLite DB 파일, build artifact는 `.gitignore`로 제외합니다.
- 실제 API 키는 문서/commit/log에 남기지 않습니다.
- Kakao REST API 키는 frontend에 넣지 않습니다.
- GitHub PAT, Render API key 등 배포 토큰은 작업 후 revoke/rotate를 권장합니다.

## 현재 상태

- GitHub repo: `ptec07/parking-availability-app`
- 로컬 실데이터 DB 동기화/지오코딩 검증 완료
- `강남역` 검색 browser smoke 검증 완료
- backend/frontend 전체 테스트 및 build 통과
- Render/Vercel 실제 배포는 계정 연결 및 환경변수 등록 후 진행 필요
