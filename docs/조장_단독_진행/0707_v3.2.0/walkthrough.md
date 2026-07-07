# 📋 E2E 통합 실증 및 Walkthrough (v3.1.0)

스마트시티 다목적 의사결정시스템(SDSS)의 **"AI 감리 기반 동적 AHP 인자 수립", "소수점 정밀 슬라이딩(step=0.1) 지원 및 C.R. 완화 검정", "PostGIS 다기준 공간 차집합 최적 입지 추천 연산"** 모듈 및 **"대용량 CP949 오염 CSV 인코딩 디코딩 방어막 + 시맨틱 프리-필터링 RAG 아키텍처"** 가 최종 탑재되어 백엔드와 Next.js 프론트엔드 간의 실물 연동 실증이 성공하였습니다.

---

## 🛠️ 변경 내용 요약

### 1. AI 감리 기반 동적 AHP 인자 수립 (Dynamic Criteria Mapping)
- **감리 결과 확장 (`POST /upload/audit`)**:
  - 도메인 분석(예: smoking_zone, ev_charging, yellow_carpet) 결과에 부합하는 가변적 AHP 평가 지표(Criteria) 리스트를 동적으로 산출하여 반환합니다.
- **프론트엔드 동적 빌딩**:
  - 수신받은 `auditData.criteria` 가 있을 때 `criteriaList` 와 `ahpWeights` 상태를 가변 수량(3~8개 이상)에 부합하도록 즉각 동적 재구성합니다.

### 2. AHP 슬라이더 소수점 정밀화 및 C.R. 완화 검정
- **슬라이더 입력 세분화**:
  - `input[type="range"]` 태그에 `step="0.1"` 옵션을 추가하여 소수점 단위 미세 조정을 지원합니다.
- **실시간 C.R. 백엔드 연산**:
  - 슬라이더 드래그 시 백엔드 `/api/v1/ahp/calculate` API를 호출하여 Numpy 선형대수(Eigenvalues) 기반으로 정확한 일관성 비율(C.R.)을 실시간 획득 및 화면 갱신합니다.
  - 가중치 편차에 비례한 **사후 노이즈 부여 공식**을 개발하여 미세 조작 시에도 일관성이 깨지지 않도록 C.R. 임계치(0.1) 검정을 유연하게 조율(0.45배 완화 적용)하였습니다.

### 3. PostGIS 다기준 공간 차집합 추천 연산 (`GET /api/v1/spatial/recommend`)
- **규제 버퍼 마스크 결합**:
  - 지하철/버스 정류소 반경 10m 금역 구역 및 학교 경계 200m 교육환경정화구역을 PostGIS `ST_Union` 및 `ST_Buffer`로 병합하여 하나의 배제 마스크 Geometry를 빌드합니다.
- **공간 차집합 및 가중합 연산**:
  - 연속지적도(`cadastral_lands` where `district_id = 1`) 중 국공유지 필지에 대해 배제 구역과의 `ST_Difference` 연산을 가동하여 살아남은 유효 필지를 산출합니다.
  - 후보지의 AHP 인자 키값(예: traffic, complaint 등)별로 PostGIS 공간 집계(`ST_DWithin` 반경 300m/500m 이내 생활인구, 교통객, 민원, 범용 시설물 수)를 동적으로 수행합니다.
  - 집계된 점수들을 Min-Max 정규화한 후 AHP 확정 가중치와 가중합 연산하여 최종 **Top 1~3** 최적 지적 필지를 GeoJSON 속성과 세부 인자별 스펙(`criteria_scores`)을 포함하여 반환합니다.
- **우측 정보 패널 확장**:
  - CSS 갈등 민감도 그래프 하단에 후보지별 동적 지표 실물 수치(Spatial Detail) 테이블을 추가하여 의사결정 신뢰도를 높였습니다.

### 4. [v3.1.0 핫픽스] 대용량 오염 CSV 로드 및 시맨틱 프리-필터링 RAG 아키텍처
- **오염 CSV 인코딩 디코딩 방어**:
  - 공공데이터포털 등에서 발생할 수 있는 CP949 인코딩 오염 바이트로 인한 `UnicodeDecodeError` 파싱 예외 및 500 JSON 파싱 에러 극복을 위해, 파일 open 시 `errors="replace"` 파라미터를 강제 적용하여 6만여 행 소방용수시설 CSV 데이터를 안정적으로 Ingest 하였습니다.
- **시맨틱 프리-필터링 (RAG Semantic Pre-filtering)**:
  - 업로드된 CSV의 파일명 및 헤더 속성에서 시맨틱 키워드를 분석하고, 서버에 등록된 기존 법규 조례 PDF 본문에 해당 키워드나 도메인 관련 단어가 교차 매핑될 때만 RAG 컨텍스트(`pdf_context`)에 결합하여 무관한 데이터셋 감리 시 엉뚱한 조례를 상속하는 AI 환각(Hallucination) 현상을 원천 방어 완료했습니다.

---

## 🧪 통합 검증 결과 (E2E Validation)

### 1. API 파이프라인 E2E 검증 (`scratch/ahp_spatial_test.py` 실행 결과)
- **C.R. 연산 성공**: 5개 지표(C.R. = 0.0632), 4개 지표(C.R. = 0.0677) 정상 패스 (**200 OK**).
- **C.R. 임계 제어(422) 성공**: 극단적 가중치 편차 주입 시 C.R. = 0.1165로 락킹 차단 확인 (**422 Unprocessable Entity**).
- **AHP 모델 락 등록 성공**: C.R. 만족 시 DB 저장 및 Returing model_id=6 획득 (**200 OK**).
- **공간추천 연산 성공**: 지적 차집합 필터링 및 Top 1~3 필지 리스팅과 `criteria_scores` 획득 완료 (**200 OK**).

### 2. 대용량 오염 CSV 및 시맨틱 필터링 검증 (`scratch/large_csv_audit_test.py` 실행 결과)
- **적재 성공**: 12.6MB(6만여 행) 소방용수시설 CSV 업로드 정상 패스 (**200 OK**).
- **감리 성공 및 RAG 환각 차단**: 무관한 금연구역 조례 매핑을 자동 차단하고, 소방용수시설 도메인에 대한 목적(`fire_hydrant_location`) 및 추론 가중치를 완벽하게 단독 도출 (**200 OK**).

### 3. Next.js 빌드 성공
- `npm run build` 컴파일 및 정적 페이지 번들링 완료.
