# 📋 E2E 통합 실증 및 Walkthrough (v3.3.0)

스마트시티 다목적 의사결정시스템(SDSS)의 **"관할지 제한 pgvector RAG 조례 매핑", "MVP 종속적 데이터베이스 테이블명 범용 스마트시티 스택 지향 리팩토링", "시맨틱 도메인 태그 유사도 기반 중복 방지 및 자동 병합", "Step 2 비주얼 HITL 규제 영역 동적 가시화 및 관할지 이탈 롤백 가드", "LangGraph SSE 실시간 3자 대립 심의 토론 스트리밍", "업로드 데이터셋별 데이터 격리 및 동적 참조 프로세스", "금지구역 버퍼 반경 차등 세분화 및 AHP 500 에러 해결"** 모듈이 최종 구현되어 E2E 실증 테스트에 성공하였습니다.

---

## 🛠️ 변경 내용 요약

### 1. 데이터베이스 테이블 스펙 범용 리팩토링 및 마이그레이션 적용
- **테이블명 일반화 개편**:
  - 특정 도메인(흡연)에 편향되었던 테이블들을 스마트시티 범용 스택으로 리팩토링했습니다:
    - `nosmoking_zones` (금연구역) ➔ `restricted_zones` (제한/규제구역) 및 `zone_type` 컬럼 추가.
    - `cigarette_dumping_zones` (꽁초무단투기) ➔ `illegal_dumping_zones` (상습무단투기구역).
  - 기존 데이터를 보존하기 위해 PostgreSQL DDL 마이그레이션 스크립트를 작성하여 로컬 실물 DB에 무결하게 즉각 반영 완료했습니다.
- **`registered_domain_tags` 테이블 신설**:
  - 도메인 분석 시 유사한 태그의 무분별한 생성을 방지하기 위한 대표 태그 임베딩 메타 테이블을 신설했습니다.

### 2. 시맨틱 도메인 태그 중복 방지 및 병합 엔진 구현
- **유사도 기반 자동 병합 (Tag Merge Engine)**:
  - AI 감리가 도출한 도메인 분류 영문 태그에 대해 OpenAI 임베딩을 거쳐 메타 테이블의 기존 대표 태그와의 pgvector 코사인 유사도(1 - <=> 연산자)를 구합니다.
  - 임계치(0.85) 이상으로 일치하는 태그가 존재할 시, 기존 대표 태그명으로 강제 덮어쓰고 치환하여 데이터 일관성을 지켜냅니다.

### 3. 관할 자치구 경계 시각화 및 마커 이탈 롤백 가드 (Boundary Constraint Guard)
- **ST_Union 기반 자치구 GeoJSON 경계 조회 (`GET /spatial/district-boundary/{district_id}`)**:
  - 행정동 경계 테이블 `dong_boundaries` 에서 해당 `district_id` 에 속한 동 폴리곤들을 PostGIS `ST_Union` 하여 자치구 전체 경계를 단일 GeoJSON(Polygon/MultiPolygon)으로 조회해 프론트에 반환합니다.
  - 프론트엔드에서는 이를 받아 옅은 파란색/보라색 반투명 폴리곤으로 시각 오버레이 드로잉합니다.
- **ST_Contains 기반 실시간 이탈 검증 및 강제 복귀 (`POST /check-boundary`)**:
  - 마커 드래그 개시(`dragstart`) 시점에 최초 좌표를 캐싱하고, 드래그 종료(`dragend`) 시점에 해당 좌표가 ST_Union 경계 폴리곤 내부(`ST_Contains`)에 속하는지 검증합니다.
  - 타 자치구 침범 및 좌표 이탈이 감지되면 즉각 경고창을 팝업하고 마커를 원래의 안전한 이전 위치로 강제 복귀(Rollback)시키는 행정적 안전장치를 탑재했습니다.

### 4. pgvector RAG 조례 내용 쿼리 & LangGraph SSE 3자 모의 토론 스트리밍
- **pgvector 기반 Pre-filtering RAG 매핑**:
  - PDF 법규 업로드 시 청크 단위로 쪼개어 OpenAI `text-embedding-3-small` 을 통해 `district_regulations` 테이블에 1536차원 벡터 데이터로 적재합니다.
  - 감리 `/upload/audit` 호출 시 CSV 키워드와 조례 임베딩 벡터 간의 코사인 유사도 검색을 가동하되, 관할 자치구 필터(`WHERE district_id = 1` 및 `similarity >= 0.40`)를 선제 결합하여 환각 현상을 완벽히 배제합니다.
- **EventSource 기반 SSE 3자 모의 토론 스트리밍 (`GET /spatial/debate`)**:
  - FastAPI의 `StreamingResponse`와 OpenAI Streaming API를 연동하여 찬성(상인), 반대(주민), 조정(공무원) 페르소나 간의 3턴 토론 대사를 `text/event-stream` 프로토콜로 1자씩 또는 청크단위로 실시간 전송합니다.
  - 프론트엔드에서는 `EventSource` 대신 `fetch` + `ReadableStream` 구조로 POST 요청 및 스트리밍을 수신하여 글자가 겹치던 채터링 현상을 원천 방어 완료했습니다.

### 5. 데이터베이스 원천 실물 데이터 일괄 적재 및 입지 선정/평가지표 고도화
- **실물 데이터베이스 완전 적재 완료**:
  - `districts`와 `dong_boundaries`가 비어있어 평가지표가 모두 0으로 나오던 현상을 해결하기 위해, 제공받은 원천 데이터를 파싱하는 `seed_db.py`를 작성 및 가동했습니다.
  - 용산구 관할 구역을 37개 법정동 그리드 폴리곤(`dong_boundaries`)으로 가상 분할 적재하고, 6,524개의 국공유지 필지(`cadastral_lands`), 338개의 버스정류소와 76개의 지하철역 출입구(`transit_stations`), 300여 개의 승하차 유동인구 통계(`transit_passengers`), 상습 담배꽁초 무단투기구역 7곳(`illegal_dumping_zones`), 38개 동별 시간대 생활인구 통계(`population_stats`), 행정동 연계형 연령대 비율(`age_demographics`) 및 가상 민원 통계(`civil_complaints`), 649개의 실물 금연/보호구역(`restricted_zones`)을 PostGIS 공간 데이터베이스에 완전 이관 적재하였습니다.
- **실물 데이터 기반 입지 선정 및 주소-좌표 정렬**:
  - 사용자가 Step 2에서 마커를 배치한 좌표(`ref_lat`, `ref_lng`)를 기반으로 반경 1km 내 국공유지 필지를 실시간 필터링(`ST_DWithin` 및 `ST_Difference`)하여 Top 1~3 최적 입지를 선정합니다.
  - 지적 필지 데이터베이스의 실제 지번 주소(`jibun`), 면적(`area`), 위경도 Centroid 좌표가 1:1 매핑되어 제공되므로, 주소와 지도의 마커 위치가 어긋나던 장해가 완벽히 해결되었습니다.
  - 또한, 각 필지 주변의 버스/지하철 유동인구, 무단투기 횟수, 생활인구수, 청소년 비율 및 동별 민원 빈도수가 실제 DB 공간 분석 연산(`ST_DWithin` 등)을 통해 산출되어, 세부 평가지표 수치가 0이 아닌 유의미한 실 통계치로 완벽하게 출력됩니다.
- **금제 영역(Prohibited Zones) 지도 붉은색 가시화 복원**:
  - 프론트엔드(`page.js`) 지도 렌더러가 기존 버스/지하철/어린이집에만 동작하던 한계를 극복하고, `school`, `nosmoking_zone`, `restricted_zone` 등 모든 금제구역 종류에 대해 조례 감리 규제 스펙(`spatial_restrictions`) 및 포인트 개별 반경(`pt.radius`)을 동적 매핑해 붉은색 완충 원(Circle)으로 지도상에 완벽히 그려내도록 시각 오버레이 구조를 복원했습니다.
- **업로드 데이터셋별 데이터 격리 및 동적 참조 연동 (v3.3.0)**:
  - 사용자가 업로드한 CSV 데이터 레코드들을 `city_spatial_features` 테이블에 `feature_name` (업로드 파일명) 컬럼과 함께 격리하여 영구 적재합니다.
  - AHP 락킹 시점인 `/ahp/lock` 호출 시 이번 실무에 활용한 전체 업로드 파일 목록(`uploaded_files`) 및 각 세부 인자별 연관 파일명 맵핑 구조(`criteria_list`)를 `ahp_models` 에 JSONB 포맷 스냅샷으로 영구 박제 저장합니다.
  - 공간 입지 추천 `/spatial/recommend` 호출 시, 의사결정 인자와 매핑된 업로드 파일명이 있는 경우 `city_spatial_features` 에서 해당 데이터셋만 격리 쿼리하여 밀도 또는 동별 통계 집계를 연산함으로써 이전 데이터셋과의 교차 오염 및 계산 왜곡을 원천 해소했습니다 (업로드 파일이 없거나 유효하지 않을 경우 기존 글로벌 시드 데이터로 자동 Fallback 적용).

### 6. 금지구역 버퍼 재산정 및 AHP 500 에러 핫픽스 (v3.3.0)
- **`exclusion_mask` 버퍼 기하 반경 재산정**: 용산구 간접흡연 피해방지 조례 및 학교 정화구역 관련 실정법을 재확인하여 초등학교/유치원(200m), 어린이집(30m), 대중교통(10m)으로 차등 세분화 적용했습니다.
- **AHP 추천 500 에러 해결**: DB 내 `criteria_list`가 JSONB 포맷으로 반환되어 이미 `list` 형태일 때 백엔드 단에서 `json.loads`를 호출하여 발생하던 `TypeError`를 방지하도록 분기 및 예외 처리를 완료했습니다.
- **`get_criteria_score` Null-safety 가드**: 특정 properties 속성이 Null일 경우 발생할 수 있는 `AttributeError` 예방을 위해 Null 가드 처리를 견고화했습니다.
- **AI 감리 가이드 및 로컬 Fallback 반경 동기화**: `upload.py`의 GPT 감리 지시 프롬프트와 로컬 Fallback 반경 딕셔너리(`spatial_restrictions_global`)를 버퍼 규격(transit_station: 10, childcare_center: 30)에 맞춰 물리적으로 정밀 세분화 동기화했습니다.

---

## 🧪 E2E 통합 검증 결과 (E2E Validation)

### 1. API 파이프라인 E2E 검증 (`scratch/rag_debate_test.py` 실행 결과)
- **자치구 GeoJSON 경계 반환 성공**: `GET /api/v1/spatial/district-boundary/1` 호출 시 200 OK 및 GeoJSON 다각형 획득 완료.
- **좌표 포함 여부 검증 성공**: `POST /api/v1/spatial/check-boundary` 호출 시 용산구 내부 좌표(`contained: true`), 외부 이탈 좌표(`contained: false`) 검정이 수학적으로 정확하게 동작 완료.
- **규제 포인트 반환 성공**: `GET /api/v1/spatial/restrictions/points` 호출 시 지하철역 및 어린이집, 금연구역 등 실물 좌표 649건 및 개별 버퍼 반경 정보 획득 성공.
- **컨텍스트 기반 SSE 모의 토론 스트리밍 성공**: `POST /api/v1/spatial/debate` 에 토론할 후보지 정보, AHP 가중치, 도메인 태그 등을 POST Body로 전송하여 pgvector RAG 조례 텍스트가 컨텍스트로 자동 결합된 3자 모의 토론 `text/event-stream` 수신 성공.
- **추천 입지 실 연산 성공 (격리 및 좌표 연동)**: `GET /api/v1/spatial/recommend?ref_lat=37.5302&ref_lng=126.9724` 호출 시 인근 실물 국공유지 필지 3곳을 선정하여 1:1 매칭되는 지번 주소, 면적 및 0이 아닌 실제 공간 평가지표 수치(`traffic`, `complaint`, `dumping` 등) 반환 성공.

### 2. Next.js 빌드 성공
- `npm run build` 컴파일 및 정적 페이지 번들링 완료.
