# R&D 연구노트 및 변경 검증 결과서 (v4.9.13 릴리즈)

본 문서에는 배종현 조장님의 지시사항 및 승인에 따라 고도화된 **1) 지번 주소 복사 전용 한글 텍스트 버튼 개편**, **2) 후보지 간 쏠림 현상 방지를 위한 DB 연동 상호 이격거리 다양성 가드(Spatial Diversity Filter)**의 변경 내역과 검증 결과를 기록합니다.

---

## 🛠️ 작업 이행 세부 내역

### 1. 지번 주소 복사 전용 텍스트 버튼 개편 ([OptimalResultPanel.jsx](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/components/OptimalResultPanel.jsx))
- **조치:** 기존의 작은 클립보드 아이콘 대신 한글 라벨의 **`[📋 주소 복사]`** 텍스트 단추를 배치했습니다.
- 지번 명칭 출력부 옆에 정교하게 정렬 배치하고 `max-w-[160px] truncate` 가드를 입혀 긴 지번이 들어오더라도 단추가 깨지지 않고 안전하게 출력되도록 UI 완성도를 제고했습니다.

### 2. 후보지 상호 간 이격거리 다양성 가드 도입 ([spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py))
- **조치:** 추천 입지 연산 시, 특정 고득점 필지나 동일 건물 및 인접 50m~150m 구간에 후보지들이 연속해서 3~4개씩 중복 쏠려 추출되던 공간적 왜곡 현상을 완전히 차단했습니다.
- RAG 감리가 감리 완료 시점에 DB `domain_regulation_rules` 의 `rules_metadata` 로 적재한 도메인별 표준 이격거리(`spatial_diversity_m`, 흡연: 150m, 전기차: 300m 등)를 실시간 바인딩하여 1차적으로 엄격한 공간 분산 필터를 수행하고, 후보지가 모자랄 시 `0.5배`씩 완화해 보충하는 **3단 이격 방어 가드레일**을 구축했습니다.
- 이를 통해 입지 후보지가 지도 전역에 고르게 분산 표출되도록 최적화 성능을 확보했습니다.

---

## 🧪 E2E 통합 테스트 검증 결과
- **테스트 커맨드:** `backend\venv\Scripts\python scratch/ahp_spatial_test.py`
- **결과:** **12개 시나리오 전항목 ALL PASS**를 다시 획득하여 무결성을 확보했습니다.
