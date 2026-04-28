# 데이터 소스 조사: 서울 주차가능성예측앱

**작성일:** 2026-04-28  
**상태:** 1차 확인 완료

## 1. 확인된 1차 API

### 서울 열린데이터광장 실시간 주차정보

샘플 호출이 정상 응답함을 확인했다.

```http
GET http://openapi.seoul.go.kr:8088/sample/json/GetParkingInfo/1/5/
```

확인 결과:

- 응답 상태: HTTP 200
- 결과 코드: `INFO-000`
- 총 샘플 건수: `124`
- 예시 주차장:
  - 세종로 공영주차장(시)
  - 종묘주차장 공영주차장(시)
  - 훈련원공원 공영주차장(시)

## 2. 주요 필드

샘플 응답에서 확인한 필드:

| 필드 | 의미 추정 | MVP 사용 여부 |
|---|---|---|
| `PKLT_CD` | 주차장 코드 | 사용 |
| `PKLT_NM` | 주차장명 | 사용 |
| `ADDR` | 주소 | 사용 |
| `PKLT_TYPE` | 주차장 유형 코드 | 보조 |
| `PRK_TYPE_NM` | 주차장 유형명 | 사용 |
| `OPER_SE_NM` | 운영 구분명 | 사용 |
| `TELNO` | 전화번호 | 사용 |
| `PRK_STTS_YN` | 주차 상태 연계 여부 | 사용 |
| `PRK_STTS_NM` | 주차 상태 설명 | 사용 |
| `TPKCT` | 전체 주차면수 | 사용 |
| `NOW_PRK_VHCL_CNT` | 현재 주차 차량 수 | 사용 |
| `NOW_PRK_VHCL_UPDT_TM` | 현재 주차대수 갱신 시각 | 사용 |
| `PAY_YN_NM` | 유료/무료 | 사용 |
| `WD_OPER_BGNG_TM` / `WD_OPER_END_TM` | 평일 운영시간 | 사용 |
| `WE_OPER_BGNG_TM` / `WE_OPER_END_TM` | 주말 운영시간 | 사용 |
| `LHLDY_OPER_BGNG_TM` / `LHLDY_OPER_END_TM` | 공휴일 운영시간 | 사용 |
| `BSC_PRK_CRG` / `BSC_PRK_HR` | 기본요금/기본시간 | 사용 |
| `ADD_PRK_CRG` / `ADD_PRK_HR` | 추가요금/추가시간 | 사용 |
| `DAY_MAX_CRG` | 일 최대 요금 | 사용 |
| `SHRN_PKLT_YN` | 공유주차장 여부 | 보조 |
| `SHRN_PKLT_MNG_URL` | 공유주차장 URL | 보조 |

## 3. 주의할 점

### 3.1 `NOW_PRK_VHCL_CNT`는 잔여면수가 아니라 현재 주차 차량 수로 보인다

샘플에서:

- 세종로 공영주차장: `TPKCT=1260`, `NOW_PRK_VHCL_CNT=457`
- 종묘주차장: `TPKCT=1312`, `NOW_PRK_VHCL_CNT=690`

따라서 MVP에서는 잔여면수를 다음처럼 계산한다.

```text
available_spaces = max(TPKCT - NOW_PRK_VHCL_CNT, 0)
availability_ratio = available_spaces / TPKCT
```

### 3.2 위치 좌표가 샘플 필드에는 없음

샘플 필드에는 위도/경도가 보이지 않았다. 따라서 MVP에서는 다음 중 하나가 필요하다.

1. `ADDR`를 Kakao Local API로 좌표 변환
2. 별도 서울 주차장 위치/정적 정보 API와 조인
3. 초기 데이터 적재 시 주소를 지오코딩하여 DB에 캐시

추천은 **초기 적재 시 Kakao Local API 지오코딩 후 DB 캐시**다.

### 3.3 인증키 필요

샘플 키는 테스트용이다. 실제 서비스에는 서울 열린데이터광장 인증키가 필요하다.

환경변수 후보:

```bash
SEOUL_OPEN_API_KEY=[REDACTED]
KAKAO_REST_API_KEY=[REDACTED]
VITE_KAKAO_JAVASCRIPT_KEY=[REDACTED]
```

## 4. 1차 데이터 파이프라인

1. 서울 `GetParkingInfo`에서 주차장 실시간 정보 수집
2. `PKLT_CD` 기준 upsert
3. 주소가 있고 좌표가 없으면 Kakao Local API로 지오코딩
4. 좌표를 DB에 캐시
5. 사용자 목적지 좌표 기준 반경 검색
6. 현재 점유율과 데이터 신선도로 가능성 점수 계산

## 5. 다음 확인 필요

- 실제 인증키로 `GetParkingInfo` 전체 페이지 호출 제한 확인
- 갱신 주기 확인
- 좌표 포함 정적 주차장 API가 별도 존재하는지 확인
- Kakao Local API 호출량/요금 확인
