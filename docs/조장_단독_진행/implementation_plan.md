# 📋 pgvector RAG 기반 조례 프리-필터링, DB 리팩토링 및 LangGraph SSE 모의 토론 구축 계획서 (v3.2.0)

본 계획서는 스마트시티 다목적 의사결정시스템(SDSS)의 **"관할지 제한 pgvector RAG 조례 매핑", "MVP 종속적 데이터베이스 테이블명 범용 스마트시티 스택 지향 리팩토링", "시맨틱 도메인 태그 유사도 기반 중복 방지", "Step 2 비주얼 HITL 규제 영역 동적 가시화", "LangGraph SSE 실시간 3자 대립 심의 토론 스트리밍"** 모듈을 설계하고 구축하기 위한 4단계 고도화 구현 계획서입니다.

---

## 1. 🔍 기술적 개편 및 해결 방안

### 1.1. 관할지 기반 pgvector RAG Pre-filtering
- **원리**: 
  - 조례 PDF가 업로드될 때 텍스트를 청크 단위(예: 1000자, overlap 200자)로 쪼개어 OpenAI `text-embedding-3-small` API로 1536차원 벡터를 생성하고 `district_regulations` 테이블에 물리 적재합니다.
  - 사용자가 업로드한 CSV 데이터셋의 키워드로 쿼리 벡터를 생성하여 RAG 검색을 실행하되, 타 자치구 조례 유입으로 인한 오판을 차단하기 위해 **`WHERE district_id = :district_id` 자치구 필터를 선제 결합(Pre-filtering)**하여 검색 범위를 엄밀하게 통제합니다.

### 1.2. 시맨틱 도메인 태그 중복 방지 및 강제 병합
- **원리**:
  - `registered_domain_tags` 테이블을 신설하여 기존 대표 태그 명칭과 임베딩 벡터를 관리합니다.
  - AI 감리가 매번 다르게 생성하는 임시 도메인 태그 설명의 임베딩 벡터와 메타 테이블 간의 **코사인 유사도(1 - <=> 연산자)**를 연산합니다.
  - 유사도 임계치(0.85) 이상인 기존 태그가 발견될 경우, 신규 생성하지 않고 기존 태그로 강제 병합(Merge)하여 분석 파이프라인의 오작동을 차단합니다.

### 1.3. 데이터베이스 테이블명 범용 리팩토링 및 마이그레이션
- **원리**:
  - 특정 도메인(흡연)에 종속적으로 설계된 테이블명을 일반화된 스마트시티 테이블 스키마로 개편합니다:
    - `nosmoking_zones` (금연구역) ➔ **`restricted_zones` (제한/규제구역)**: `zone_type` 칼럼 추가.
    - `cigarette_dumping_zones` (꽁초무단투기) ➔ **`illegal_dumping_zones` (상습무단투기구역)**.
  - 백엔드 DB 초기화 DDL, Python CRUD 및 공간 연산 쿼리 내 모든 명칭을 동시 리팩토링하고 기존 적재 데이터를 안전하게 마이그레이션합니다.

### 1.4. Step 2 비주얼 HITL 규제 버퍼 동적 가시화
- **원리**:
  - AI 감리가 감리 결과 응답으로 정형 규제 제한 스펙(`spatial_restrictions`, 예: `subway_station: 10m`)을 전송하면, Step 2의 Leaflet 지도 상에 해당 규제 대상 시설물들을 쿼리하여 **붉은색 경고 반경 원(L.circle)으로 즉각 동적 드로잉**합니다.
  - 사용자가 마커를 드래그하는 핸들러 루프에서 붉은 영역 진입 여부를 감지해 ⚠️ 경고 마커로 토글하여 보정 작업의 타당성을 즉시 실현합니다.

### 1.5. LangGraph SSE 3자 대립 토론 스트리밍
- **원리**:
  - 사용자가 락(Lock)을 완료한 추천 필지에 대해 모의 토론을 요청하면, GPT-4o-mini를 연동하여 찬성(상인), 반대(주민), 조정(공무원) 에이전트 간의 3자 토론을 순차 진행합니다.
  - 토론 결과를 일괄 반환하지 않고, `text/event-stream` 프로토콜을 사용해 한 단어/대사씩 클라이언트에 실시간 스트리밍(SSE)하여 사용자 화면의 터미널 대화창에 타이핑되듯 표출합니다.

### 1.6. Step 1 공간 데이터 필수 컬럼 선제적 차단 밸리데이션 (Pre-Validation Guard)
- **원리**:
  - 업로드된 CSV 파일에 공간 위치 정보(위도 및 경도 관련 헤더 후보군)가 아예 존재하지 않는 결측 파일인 경우, 감리(`/upload/audit`) 단에서 프로세스를 진행하지 않고 **400 Bad Request 에러**(`"위도(lat) 및 경도(lng) 필수 위치 컬럼이 존재하지 않아 분석할 수 없습니다."`)를 발생시켜 선제적으로 차단합니다.
  - 이를 통해 부적합한 데이터셋이 시스템 내부(Step 2 보정 등)로 진입하는 것을 완벽하게 예방합니다.

### 1.7. 관할 자치구 경계 가시화 및 마커 이탈 롤백 가드 (Boundary Constraint Guard)
- **원리**:
  - Step 2 보정 단계 진입 시 로그인 사용자의 관할 자치구(`districts`) 경계 기하 데이터(MultiPolygon)를 GeoJSON 형식으로 조회하여 지도 상에 옅은 파란색/보라색 반투명 폴리곤으로 시각적 렌더링합니다.
  - 마커 드래그 시 좌표 오동작 및 타 자치구 침범 휴먼 에러를 물리적으로 차단하기 위해, 드래그 시작(`dragstart`) 시 최초 좌표를 백업하고 드래그 종료(`dragend`) 시점에 PostGIS `ST_Contains` 함수 기반으로 관할 경계 내 포함 여부를 검증합니다.
  - 관할 구역 이탈이 감지되면 즉각 경고 경보를 팝업하고 마커를 원래의 안전한 이전 좌표로 강제 복귀(Rollback)시키는 가드를 가동합니다.

---

## 2. Proposed Changes

### 💾 데이터베이스 및 DDL (`DB/init/`, `backend/app/`)

#### [NEW] [registered_domain_tags 테이블 신설]
- `registered_domain_tags` 테이블을 DDL 스키마에 선언하고 코어 태그 목록(`smoking_zone`, `ev_charging`, `yellow_carpet`)을 임베딩과 함께 프리-시딩합니다.

#### [MODIFY] [01_schema.sql](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/DB/init/01_schema.sql)
- `nosmoking_zones` ➔ `restricted_zones` 변경 및 `zone_type` 칼럼 주입.
- `cigarette_dumping_zones` ➔ `illegal_dumping_zones` 변경.

---

### 💻 백엔드 컴포넌트 (`backend/app/routers/`)

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)
- `upload_regulation_files` API에 PDF 청킹 및 OpenAI text-embedding-3-small 임베딩을 통한 `district_regulations` 벡터 테이블 적재 로직 완성.
- `audit_upload_files` API 내부의 RAG 컨텍스트 생성을 수동 키워드 스캔에서 **pgvector 코사인 유사도 쿼리(pre-filtering: district_id 및 유사도 0.40 이상)**로 전면 교체.
- 감리 완료 시 도출된 도메인 설명과 `registered_domain_tags` 간의 pgvector 코사인 유사도 병합 로직 탑재.
- 감리 완료 결과 스펙에 규제 메타데이터(`spatial_restrictions`) 추가 반환.

#### [MODIFY] [spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py)
- 리팩토링된 `restricted_zones` 및 `illegal_dumping_zones` 테이블명을 참조하도록 공간 연산 및 가중합 쿼리 갱신.
- **[NEW]** `GET /api/v1/spatial/restrictions/points` API 신설: Step 2 규제 버퍼 가시화를 위한 시설물 좌표 반환.
- **[NEW]** `GET /api/v1/spatial/debate` SSE 스트리밍 API 신설: OpenAI Streaming API를 연동하여 찬성/반대/조정 3자 토론 내용을 `text/event-stream` 프로토콜로 전송.
- **[NEW]** `GET /api/v1/spatial/district-boundary/{district_id}` API 신설: 관할 자치구 경계 GeoJSON 반환.
- **[NEW]** `POST /api/v1/spatial/check-boundary` API 신설: 특정 위경도의 자치구 경계 내 포함 여부 검증 (PostGIS ST_Contains 활용).

---

### 🎨 프론트엔드 컴포넌트 (`frontend/src/app/`)

#### [MODIFY] [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/page.js)
- Step 2 진입 시, 감리 응답으로 수신받은 `spatial_restrictions` 에 따라 백엔드로부터 시설물 좌표를 조회해 붉은색 규제 버퍼 원(L.circle) 동적 가시화 구현.
- 관할 자치구 경계 GeoJSON 데이터를 조회하여 지도 상에 옅은 파란색/보라색 반투명 폴리곤으로 시각적 렌더링.
- 마커 드래그 시 `dragstart`에서 최초 좌표를 백업하고, `dragend` 시 백엔드 `/check-boundary` 검증을 거쳐 이탈 시 롤백 및 에러 얼럿 처리 적용.
- 핀 드래그 스냅 핸들러에 규제 서클 교차 판정 기능을 추가하여 경고 토글 연동.
- Step 5의 `runSimulation` 실행 시 하드코딩된 mock 스크립트 대신 `EventSource`를 생성하여 백엔드 `/api/v1/spatial/debate` SSE 채널을 구독하고 실시간 스트리밍 대화를 터미널 로그에 순차 밀어 넣는 로직으로 개편.

---

## 3. Verification Plan

### Automated Tests
- `scratch/rag_debate_test.py` 스크립트를 작성하여:
  1. `POST /upload/regulation` 을 통해 PDF가 청킹/임베딩되어 pgvector DB에 정상 적재되는지 검증.
  2. `POST /upload/audit` 실행 시 자치구 pre-filtering이 동작하여 정확한 조례만 인입되는지 검증.
  3. `GET /spatial/debate` SSE 스트리밍 호출 시 청크 텍스트가 정상 스트리밍(**200 OK**) 수신되는지 비동기 테스트 실행.

### Manual Verification
- 브라우저 상에서 Step 1 감리 후 Step 2로 넘어갔을 때 금지 구역 붉은 원들이 지도에 잘 나타나는지 확인.
- 결측 마커를 붉은 원 안으로 끌고 들어갔을 때 마커가 ⚠️ 경고 이미지로 실시간 토글되는지 확인.
- 모의 심의 토론을 시작했을 때 에이전트의 대화가 한 자씩 부드럽게 타자기가 쳐지듯 실시간 스트리밍 전계되는지 UX 관측.
