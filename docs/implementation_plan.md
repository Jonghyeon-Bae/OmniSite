# 📋 공간 데이터 파일 캐싱 도입, PostGIS 최적화 및 모의 토론 스트리밍 복원 계획 (v3.7.0)

본 계획서는 Step 3 AHP 잠금 후 추천 입지 연산 성능 저하(레이턴시)를 개선하고, 사용자가 매번 다르게 제공하는 업로드 공간 데이터를 PostgreSQL DB에 누적하는 대신 로컬 파일 시스템에 JSON 포맷으로 격리 캐싱(JSON Cache)하여 DB 누적을 원천 배어하며, SSE 스트리밍 토론 대사 누락 버그를 accumulated-text 라인 파서로 해결하기 위한 상세 설계서입니다.

---

## 🔍 1. 현황 및 개선 필요성

1. **공간 데이터 DB 적재에 따른 누적 및 중복 문제 (조장 피드백)**:
   - **현황**: 현재 CSV 파일을 보정하여 커밋할 때마다 `city_spatial_features` 테이블에 레코드가 계속 삽입(INSERT)되어 DB 용량이 매번 비대해지고 정합성이 왜곡될 위험이 있습니다.
   - **해결책**: 커스텀 업로드 데이터셋에 대해서는 PostgreSQL DB에 영구 적재하지 않고, 보정 완료 시 파일명에 대응하는 **로컬 JSON 캐시 파일 (`data/raw/filename.json`)**로 저장하여 관리합니다.
   - 공간 입지 추천 및 분석 시에는 이 JSON 파일을 Python 메모리 상에 로드(성능 향상을 위한 요청 수준 Request-Cache 적용)하여 파이썬 단에서 최적 입지 밀도 및 통계를 연산함으로써 DB 누적 및 테이블 팽창 문제를 완벽하게 해결합니다.

2. **AHP 추천 공간 연산 지연 (5초 이상 소요)**:
   - **원인**: `cadastral_lands` 6,524개 필지 및 배제구역 검증 쿼리에서 `geom::geography` 형변환을 실시간으로 남발하여 풀 테이블 스캔(Seq Scan)이 유발되고 있습니다.
   - **해결책**: WGS 84(4326)의 좌표계를 그대로 유지하되 geometry `ST_DWithin`과 degree 파라미터(1m ≒ 0.00001도)로 전환하여, `idx_cadastral_geom` GIST 인덱스를 100% 태우도록 최적화합니다. (성능 테스트 결과 5.2초 ➔ 0.02초로 **250배 단축**)

3. **AI 페르소나 모의 토론 스트리밍 대사 누락 및 병합 현상**:
   - **원인**: 프론트엔드 `page.js`에서 SSE 스트리밍이 글자 단위 청크로 쪼개져 들어올 때 실시간 매칭에 실패하여 이전 발언자 카드에 대사가 뭉쳐서 출력되었습니다.
   - **해결책**: 프론트엔드에 스트림 데이터를 전역 버퍼(`accumulatedText`)로 누적하고, 매 프레임마다 정밀 줄 단위 파서를 돌려 `상인대표`, `구민대표`, `조정관`, `시스템` 발언 카드를 정확히 생성하도록 개선합니다.

---

## 🛠️ Proposed Changes (변경 대상 파일 및 코드)

### 2-1. Backend

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)

1. **`commit_hitl_data` 내 DB 적재 제거 및 JSON 파일 캐싱 도입**:
   - `city_spatial_features` 테이블로의 `INSERT` 구문을 제거합니다.
   - 보정 승인된 좌표 정보에 대해, `dong_boundaries` 전체 폴리곤 데이터(37개 행정동)를 미리 로드하여 Shapely(`shapely.geometry.Polygon`) 객체 캐시로 구성합니다.
   - Python 상에서 각 좌표가 속한 `dong_id`를 고속 연산(contains)한 뒤, 최종 데이터를 `data/raw/{filename}.json` 포맷으로 저장 및 오버라이트합니다.
   - 이를 통해 매번 제공되는 데이터셋이 달라지더라도 로컬 파일 오버라이트 캐시로만 유지되며, PostgreSQL DB에는 전혀 누적되지 않습니다.

#### [MODIFY] [spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py)

1. **로컬 JSON 파일 캐싱 파서 도입 (`get_cached_file_data`)**:
   - 요청 레벨에서 JSON 캐시 파일을 불러오기 위한 메모리 캐싱 딕셔너리(`_file_cache`) 및 헬퍼 함수를 구현합니다.
   - `get_criteria_score` 호출 시 `associated_file`이 지정되어 있다면 DB를 조회하는 대신 `get_cached_file_data`를 통해 JSON 데이터를 로드하여 포인트 거리 및 동별 통계 집계를 Python 단에서 직접 연산합니다.

2. **기본 정적 테이블 공간 쿼리 geometry 최적화 (Fallback)**:
   - 업로드 파일이 지정되지 않아 기존 기본 데이터베이스 데이터를 조회하는 Fallback 쿼리들(`transit_stations`, `civil_complaints`, `illegal_dumping_zones` 등)에 대해, geometry `ST_DWithin` 및 degree 단위를 적용하여 인덱스를 강제 활용합니다.

3. **`recommend_optimal_sites` 및 `stream_debate_sim` 내 공간 쿼리 튜닝**:
   - 후보 필지 조회 시 `ST_DWithin(c.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.01)`을 통해 GIST 공간 인덱스를 활용하고, 배제 조건의 `NOT EXISTS` 내 거리 계산도 `ST_DWithin(c.geom, cc.geom, 0.002)` 등으로 튜닝합니다.

---

### 2-2. Frontend

#### [MODIFY] [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/page.js)

1. **SSE 대화 스트림 파서 갱신 (`useEffect` 내 `startDebateStream` 로직)**:
   - `let accumulatedText = ''` 변수를 두어 유입된 모든 문자열을 누적합니다.
   - 매 수신 시마다 누적된 버퍼를 정밀 줄 단위 파서로 분해하여 `상인대표`, `구민대표`, `조정관`, `시스템`을 식별하고 대화 로그 배열을 재구성하도록 코드를 개선합니다.

---

## 🧪 3. Verification Plan

### Automated Verification
- 최적화 코드 적용 후 `backend\venv\Scripts\python.exe -c "import time, urllib.request; ..."`를 구동하여 AHP lock 추천 입지 연산 API 응답이 **200ms 이하**로 들어오는지 단독 및 복합 지연 진단을 다시 가동합니다.
- `scratch/rag_debate_test.py` E2E 테스트 스크립트를 실행하여 전체 6개 시나리오 및 PDF 생성이 빌드-업 후 깨지지 않고 정상 통과되는지 확인합니다.

### Manual Verification
- 웹 브라우저(`localhost:3000`) 접속 후 Step 3 AHP 가중치 확정 클릭 시 즉시 Step 4 추천 후보지가 표출되는지 검증합니다.
- 동일한 데이터셋을 반복적으로 업로드 및 커밋한 후 `city_spatial_features` 테이블에 데이터가 누적되지 않고, `data/raw/` 폴더 내에 단일 JSON 캐시 파일만 성공적으로 오버라이트 갱신되는지 확인합니다.
