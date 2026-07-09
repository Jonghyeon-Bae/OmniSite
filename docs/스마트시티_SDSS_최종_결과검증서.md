# R&D 연구노트 및 변경 검증 결과서 (v4.7.1 릴리즈)

본 문서에는 배종현 조장님의 승인된 계획안에 따라 수행된 **1) Dynamic Spatial Relaxing Search (반경 확장 수집)**, **2) Dynamic Spatial Annealing Grid (이격 완화 필터)**, **3) 프론트엔드 동적 탭 렌더링**, **4) 소스코드 전수 조사를 통한 하드코딩 배제 권고안**의 수립 결과를 담고 있습니다.

---

## 🛠️ 작업 이행 세부 내역

### 1. 백엔드 다이내믹 공간 완화 수집 및 격리 알고리즘 이식
- **[spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py):**
    - **Dynamic Radius Relaxing (반경 확장 수집):** 최초 탐색 시 실재하는 지적 후보지가 부족할 경우, 인위적인 모의 거짓 데이터를 생성하는 대신 **ST_DWithin 반경을 `2km(0.02)` ➔ `4km(0.04)` ➔ `8km(0.08)`로 점진 확장**하여 실재하는 국공유지 필지만을 데이터베이스에서 수집하도록 설계했습니다.
    - **Dynamic Spatial Annealing (이격 완화 필터):** 중복 배제 필터링 시, 인접 필지가 겹치는 병목을 방지하기 위해 이격 임계값을 **`150m` (0.0015도) ➔ `100m` (0.0010도) ➔ `70m` (0.0007도) ➔ `50m` (0.0005도) ➔ `30m` (0.0003도)**로 점진 완화(Annealing)하며 실제 필지만으로 5개 슬롯을 풍부하고 분산되게 획득하도록 조율했습니다.
    - 이에 따라, 필지가 부족하거나 특정 구역에 쏠려 있을 때도 인접 부지가 바로 옆에 다닥다닥 붙지 않고 도시계획적으로 분산된 다원적 후보지가 동적으로 격리 검출됩니다.

### 2. 프론트엔드 동적 탭 렌더링에 의한 데이터 유실 크래시 해결
- **[OptimalResultPanel.jsx](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/components/OptimalResultPanel.jsx) & [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/page.js):**
    - 탭 리스트를 `top1`~`top5`로 고정 매핑하던 하드코딩 방식을 폐지했습니다.
    - 백엔드가 반환한 유효 후보지 키 목록(`Object.keys(selectedParcel).filter(...)`)을 기반으로 **탭을 동적 렌더링**하게 하여, 수집된 후보지가 3개일 때는 3개만, 5개일 때는 5개가 완벽하게 표현되도록 조치했습니다.
    - 이로 인해 빈 탭 클릭 시 화면에 데이터가 로딩되지 않고 공백만 뜨거나 Null 참조 오류가 발생하던 결함이 원천 차단되었습니다.

---

## 🔎 잔존 하드코딩 요소 재탐색 및 제거 방안 (Zero Hardcoding)

코드 전수 조사 결과, 현재 시스템에 유일하게 남아있는 하드코딩 요소를 발굴하고 이에 대한 제거 방안을 수립했습니다.

### 1. 지목 코드별 가/감점 수치 하드코딩 (백엔드)
- **현황:** `/recommend` API 내에 `ev_charging` 일 때 '도'(도로) 지목에 감점 4점, '차/공'(주차장/공원) 지목에 가점 6점을 주는 연산이 파이썬 코드로 기입되어 있습니다.
- **제거 방안:** RAG 감리 시점에 OpenAI가 조례에서 추출한 지목별 가감점 맵(`land_use_modifiers` JSONB)을 DB `domain_regulation_rules` 의 `rules_metadata` 에 적재하도록 RAG 프로필을 확장합니다. 이후 런타임에는 이 JSONB 맵을 파싱하여 동적으로 가산/감산 처리를 함으로써 하드코딩을 완전히 박멸합니다.

### 2. 도메인 지정 select 콤보 박스 태그 (프론트엔드)
- **현황:** `SidebarControl.jsx` 에 흡연구역, 전기차 충전소, 옐로카펫 등 도메인 태그들이 `<option>` 뷰 태그 안에 수동 선언되어 있습니다.
- **제거 방안:** DB에 등록된 유효 `facility_type` 목록을 쿼리하는 메타 API(예: `/api/v1/spatial/domains`)를 개설하고, 프론트엔드가 마운트 시 이를 비동기 조회하여 콤보박스를 dynamic 바인딩 처리합니다. 이렇게 하면 새로운 인프라 도메인이 추가되더라도 코드 수정 없이 100% 제네릭하게 처리됩니다.

---

## 🧪 E2E 통합 테스트 검증 결과
- 이격 완화 및 동적 수집 알고리즘 적용 완료 후 E2E 통합 API 테스트(`ahp_spatial_test.py`)를 재수행하여, **12개 시나리오 전항목 ALL PASS** 및 Candidates Keys 5개(`top1`~`top5`) 획득을 완벽히 보증했습니다.
