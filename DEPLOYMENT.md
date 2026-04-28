# 주차될까 배포 가이드

이 문서는 서울 공영주차장 실시간 데이터 기반 PWA MVP **주차될까**를 Render 백엔드 + Vercel 프론트엔드 구조로 배포하기 위한 절차를 정리한다.

> 현재 문서는 **배포 준비 문서**다. 실제 Render/Vercel 배포는 아직 수행하지 않았고, 별도 GitHub repo와 배포 계정 인증이 필요하다.

---

## 현재 배포 상태

- 로컬 통합 실행: 완료
- 백엔드 로컬 앱: `uvicorn app.main:app`로 실행 가능
- 프론트 로컬 앱: Vite dev server에서 `/api`를 `http://127.0.0.1:8000`으로 프록시
- 배포 파일 준비: 완료 (`backend/requirements.txt`, `render.yaml`, `frontend/vercel.json`)
- 실제 외부 배포: 미진행 — 현재 환경에는 별도 GitHub repo/Render/Vercel 인증이 없어 차단됨
- 실제 서울/Kakao API 키 기반 전체 동기화: CLI 구현 완료, 임시 DB에서 `fetched=124 saved=124`, 보정 후 `geocoded=15 failed=0`, 좌표 누락 `0`건 검증 완료
- Kakao 지도 SDK: `VITE_KAKAO_JAVASCRIPT_KEY` 기반 프론트 렌더링 코드 완료, 로컬 Kakao 도메인 등록 후 실제 지도/마커 렌더링 확인 완료
- 현재 로컬 기본 DB: `backend/parking.db`에 실제 서울 데이터 동기화/지오코딩 완료. 운영 배포 DB는 새 DB에서 seed 없이 생성 권장

현재 확인된 로컬 API 계약:

```http
GET /api/health
GET /api/geocode?query=강남역
GET /api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000
```

최근 로컬 smoke 결과:

- `/api/geocode?query=강남역` → HTTP 200, 강남역 좌표 반환
- 강남역 주변 `/api/parking-lots` → `count=4`
- 서울시청 주변 `/api/parking-lots` → `count=43`
- 브라우저 `강남역` 검색 → Kakao 지도 + 주차장 카드 4곳 + fallback 없음

---

## 필요한 환경변수

### 백엔드(Render) 환경변수

```bash
PORT=8000
PARKING_DB_PATH=/var/data/parking.db
PARKING_SEED_DEMO_DATA=0
SEOUL_OPEN_API_KEY=[REDACTED]
KAKAO_REST_API_KEY=[REDACTED]
FRONTEND_ORIGIN=https://<vercel-project>.vercel.app
APP_ENV=production
```

설명:

| 변수 | 용도 | 비고 |
| --- | --- | --- |
| `PORT` | Render가 주입하는 HTTP 포트 | 기본 `8000` |
| `PARKING_DB_PATH` | SQLite DB 파일 경로 | Render 영구 디스크 사용 시 `/var/data/parking.db` 권장 |
| `PARKING_SEED_DEMO_DATA` | 데모 seed 사용 여부 | 운영은 `0` 권장 |
| `SEOUL_OPEN_API_KEY` | 서울 열린데이터광장 `GetParkingInfo` 호출 키 | 서버 사이드 전용 |
| `KAKAO_REST_API_KEY` | Kakao Local 주소 검색 REST API 키 | 서버 사이드 전용, `Authorization: KakaoAK {api_key}` |
| `FRONTEND_ORIGIN` | CORS 허용 프론트 URL | `create_app(..., frontend_origin=...)` 또는 환경변수로 적용 |
| `APP_ENV` | 실행 환경 구분 | 예: `production` |

### 프론트엔드(Vercel) 환경변수

```bash
VITE_API_BASE_URL=https://<render-service>.onrender.com
VITE_KAKAO_JAVASCRIPT_KEY=[REDACTED]
```

설명:

| 변수 | 용도 | 비고 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 배포 프론트가 호출할 백엔드 base URL | 미설정 시 로컬 기본값 `/api`, 설정 시 `<origin>/api/...`로 호출 |
| `VITE_KAKAO_JAVASCRIPT_KEY` | Kakao Maps JavaScript SDK 키 | 브라우저 노출 가능 키지만 도메인 제한 필수 |

> 주의: `KAKAO_REST_API_KEY`는 프론트에 넣지 않는다. Kakao REST API 호출은 서버에서만 수행한다.

---

## API 키 발급처

### 서울 열린데이터광장

- 사이트: https://data.seoul.go.kr/
- 대상 API: `GetParkingInfo`
- 샘플 URL:

```http
http://openapi.seoul.go.kr:8088/sample/json/GetParkingInfo/1/5/
```

실제 키 사용 URL 형식:

```http
http://openapi.seoul.go.kr:8088/{SEOUL_OPEN_API_KEY}/json/GetParkingInfo/{start}/{end}/
```

### Kakao Developers

- 사이트: https://developers.kakao.com/
- 필요한 키:
  - REST API 키: `KAKAO_REST_API_KEY`
  - JavaScript 키: `VITE_KAKAO_JAVASCRIPT_KEY` 또는 `KAKAO_JAVASCRIPT_KEY`
- REST API 주소/키워드 검색 헤더:

```http
Authorization: KakaoAK {api_key}
```

사용 endpoint:

- 목적지/주소 검색: `https://dapi.kakao.com/v2/local/search/address.json`
- 주소 검색 실패 시 fallback: `https://dapi.kakao.com/v2/local/search/keyword.json`

보안 권장:

- JavaScript 키는 Vercel 배포 도메인과 로컬 개발 도메인만 허용한다.
- REST API 키는 Render 백엔드 환경변수에만 저장한다.
- 문서, 로그, 커밋에는 실제 키를 남기지 않는다. 예시는 항상 `[REDACTED]`로 둔다.

---

## 로컬 실행법

프로젝트 루트:

```bash
cd /home/ptec07/.hermes/hermes-agent/workforce/parking-availability-app
```

### 백엔드 실행

```bash
cd backend
PARKING_DB_PATH=./parking.db \
PARKING_SEED_DEMO_DATA=0 \
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

헬스체크:

```bash
curl http://127.0.0.1:8000/api/health
```

예상 결과:

```json
{"status":"ok"}
```

주차장 검색 smoke:

```bash
curl 'http://127.0.0.1:8000/api/geocode?query=강남역'
curl 'http://127.0.0.1:8000/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000'
```

새 운영/배포 DB는 seed 데이터가 섞이지 않도록 `PARKING_SEED_DEMO_DATA=0` 상태에서 아래 순서로 생성한다.

```bash
cd backend
SEOUL_OPEN_API_KEY=*** python -m app.cli sync-seoul-parking --db parking.db --page-size 200
KAKAO_REST_API_KEY=*** python -m app.cli geocode-missing-coordinates --db parking.db
```

### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저 확인:

```text
http://127.0.0.1:5173/
```

현재 Vite dev proxy:

```text
/frontend/apiProxyConfig.ts
/api -> http://127.0.0.1:8000
```

---

## Render 백엔드 배포

### 권장 구성

현재 백엔드는 stdlib `sqlite3` 기반이다. Render에서 운영하려면 다음 중 하나가 필요하다.

1. **영구 디스크 + SQLite**
   - MVP/데모에는 간단하다.
   - `PARKING_DB_PATH=/var/data/parking.db`처럼 Render disk mount 경로를 사용한다.
2. **PostgreSQL로 이전**
   - 운영 안정성은 더 좋다.
   - 현 코드에는 아직 PostgreSQL 지원이 없다.

### Render 서비스 설정 예시

현재 backend 폴더에는 Render Native Python 런타임용 `requirements.txt`가 있고, 프로젝트 루트에는 `render.yaml`이 있다. 실제 배포 시에는 아래 blueprint를 Render에서 연결하고, `FRONTEND_ORIGIN`, `SEOUL_OPEN_API_KEY`, `KAKAO_REST_API_KEY`를 Render 환경변수에 등록한다.

Render Native Python 런타임 예시:

```yaml
services:
  - type: web
    name: parking-availability-backend
    runtime: python
    plan: free
    rootDir: backend
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    healthCheckPath: /api/health
    autoDeploy: false
    envVars:
      - key: PORT
        value: 8000
      - key: PARKING_DB_PATH
        value: /var/data/parking.db
      - key: PARKING_SEED_DEMO_DATA
        value: 0
      - key: SEOUL_OPEN_API_KEY
        sync: false
      - key: KAKAO_REST_API_KEY
        sync: false
      - key: FRONTEND_ORIGIN
        sync: false
```

Docker 방식 예시:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### Render 배포 후 확인

```bash
curl https://<render-service>.onrender.com/api/health
```

예상 결과:

```json
{"status":"ok"}
```

검색 API:

```bash
curl 'https://<render-service>.onrender.com/api/geocode?query=강남역'
curl 'https://<render-service>.onrender.com/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000'
```

주의:

- `PARKING_SEED_DEMO_DATA=0`인 운영 환경에서 DB가 비어 있으면 `items: []`가 정상이다.
- 실제 데이터를 보려면 아래 운영용 CLI로 서울 API sync와 Kakao 지오코딩을 실행해야 한다.
- `/api/geocode`는 `KAKAO_REST_API_KEY`가 없으면 HTTP 503을 반환한다.

### 운영용 데이터 CLI

서울 공영주차장 실시간 데이터 동기화:

```bash
cd backend
SEOUL_OPEN_API_KEY=[REDACTED] \
python -m app.cli sync-seoul-parking --db /var/data/parking.db --page-size 100
```

좌표가 없는 주차장 Kakao Local 지오코딩:

```bash
cd backend
KAKAO_REST_API_KEY=[REDACTED] \
python -m app.cli geocode-missing-coordinates --db /var/data/parking.db
```

CLI는 실제 키 값을 출력하지 않고 처리 결과 count만 출력한다.

---

## Vercel 프론트엔드 배포

### 권장 설정

- Project root: `frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`

Vercel 환경변수:

```bash
VITE_API_BASE_URL=https://<render-service>.onrender.com
VITE_KAKAO_JAVASCRIPT_KEY=[REDACTED]
```

프론트는 `src/api.ts`의 `buildApiUrl()`에서 `VITE_API_BASE_URL`을 읽는다.

- 로컬 기본값: `/api`
- Vercel 운영값 예: `https://<render-service>.onrender.com`
- 실제 요청 예: `https://<render-service>.onrender.com/api/parking-lots?...`

백엔드는 `FRONTEND_ORIGIN=https://<vercel-project>.vercel.app`으로 Vercel origin을 CORS 허용한다.

배포 후에는 Kakao Developers의 JavaScript 키 Web 플랫폼 도메인에 실제 Vercel origin을 추가해야 한다.

### Vercel SPA fallback

`frontend/vercel.json`을 두어 Vite build 산출물 `dist`를 서빙하고 모든 SPA 경로를 `index.html`로 되돌린다.

```json
{
  "version": 2,
  "cleanUrls": true,
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

---

## 배포 후 헬스체크

### 백엔드

```bash
BACKEND_URL=https://<render-service>.onrender.com
curl -i "$BACKEND_URL/api/health"
curl -i "$BACKEND_URL/api/geocode?query=강남역"
curl -i "$BACKEND_URL/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000"
```

성공 기준:

- `/api/health` HTTP 200
- 응답 본문: `{"status":"ok"}`
- `/api/geocode?query=강남역` HTTP 200 및 `lat`, `lng` 포함
- `/api/parking-lots` HTTP 200
- 응답에 `items` 배열과 `count` 숫자 포함

### 프론트엔드

```bash
FRONTEND_URL=https://<vercel-project>.vercel.app
curl -i "$FRONTEND_URL/"
```

브라우저 QA:

1. `/` 접속
2. 목적지 입력창에 `강남역` 입력 후 검색
3. `강남역 주변 주차장` 제목 확인
4. Kakao 지도와 카드 목록 또는 빈 상태가 보이는지 확인
5. 브라우저 콘솔에 CORS/API/Kakao domain mismatch 오류가 없는지 확인

---

## 보안 주의사항

- 실제 API 키는 `.env`, Render env, Vercel env에만 저장한다.
- `.env.example`과 문서에는 `[REDACTED]` 또는 placeholder만 둔다.
- `KAKAO_REST_API_KEY`는 절대 프론트 빌드 환경변수로 넣지 않는다.
- `VITE_KAKAO_JAVASCRIPT_KEY`는 브라우저에 노출되는 키이므로 Kakao Developers에서 도메인 제한을 설정한다.
- 운영에서는 `PARKING_SEED_DEMO_DATA=0`을 권장한다.
- 현재 SQLite 파일은 단일 인스턴스 기준이다. 여러 인스턴스/스케일아웃에는 적합하지 않다.

---

## 남은 배포 준비 작업

이번 단계에서 의존성 파일, Render blueprint, Vercel SPA 설정, 프론트 API base URL helper, 백엔드 CORS 기반, 목적지 geocode API, Kakao 지도 렌더링은 추가했다. 실제 외부 배포 전에 아래 작업이 남아 있다.

1. 별도 GitHub repo 준비 및 첫 push
   - 현재 프로젝트는 상위 Hermes repo 기준 untracked 상태이며 remote가 `NousResearch/hermes-agent.git`라 그대로 push 금지
2. Render/Vercel 인증 준비
   - 현재 확인 결과 `vercel` CLI 없음, `RENDER_API_KEY`/`VERCEL_TOKEN`/`GITHUB_TOKEN`/`GH_TOKEN` 없음, `gh auth status` 미인증
3. Render 서비스 생성 및 영구 디스크 연결
   - `render.yaml` 기준으로 서비스 생성 후 `/var/data` 디스크 mount 확인
4. Vercel 프로젝트 생성 및 환경변수 등록
   - `VITE_API_BASE_URL=https://<render-service>.onrender.com`
5. 서울/Kakao 데이터 sync 주기 실행 설정
   - Render cron job 또는 외부 스케줄러에서 `python -m app.cli sync-seoul-parking` 후 `geocode-missing-coordinates` 실행
6. 실제 서울/Kakao API 키를 Render/Vercel 환경변수로 등록
7. Vercel 배포 URL을 Kakao Developers JavaScript Web 도메인에 추가
8. 배포 후 `/api/health`, `/api/geocode`, `/api/parking-lots`, 프론트 브라우저 QA 확인

---

## 현재 검증 명령

최신 전체 회귀 검증:

```bash
cd backend
PARKING_DB_PATH=parking.db python3 -m pytest tests -q

cd ../frontend
npm test -- --run
npm run build
```

최근 확인 결과:

```text
backend: 42 passed
frontend: 6 files / 17 tests passed
frontend build: success
```
