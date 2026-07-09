# 주소복사 전용 버튼화 및 후보지 이격거리 다양성 가드 수립 계획 (v4.9.13)

본 계획은 배종현 조장님의 지시사항 및 승인에 따라 **1) 지번 주소 복사 전용 텍스트 버튼 UI 이식**, **2) 동일 거점 후보지 연속 노출 차단을 위한 상호 이격거리 다양성 가드(Spatial Diversity Filter)**를 이식하기 위한 기술 설계서입니다.

---

## User Review Required

> [!IMPORTANT]
> **1. 지번 주소 복사 텍스트 버튼 고도화 (UI/UX)**
> - 아이콘 대신 `[📋 주소 복사]` 라는 직관적인 한글 라벨의 텍스트 단추로 업그레이드하고, 지번 텍스트 영역에 `max-w` 및 `truncate` 가드를 심어 레이아웃 깨짐 현상을 원천 방지합니다.
>
> **2. 후보지 상호 간 이격거리 다양성 가드 (Spatial Diversity Filter) 탑재**
> - 최적지 랭킹 추천 수집 시, 상위 점수를 획득한 동일 거점이나 150m 이내 초근접 필지들이 Top 1~5 를 독점하여 입지 선정을 훼손시키던 공간 쏠림 현상을 방지합니다.
> - RAG 감리 데이터베이스에 적재된 `spatial_diversity_m` 값(흡연: 150m, 전기차: 300m 등)을 실시간 바인딩하여, **이격거리가 확보된 공간적 다양성 필터**를 PostGIS 추천 목록 추출 시 적용합니다.

---

## Proposed Changes

### 프론트엔드 컴포넌트 (Frontend)

---

#### [MODIFY] [OptimalResultPanel.jsx](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/components/OptimalResultPanel.jsx)
- **주소 복사 텍스트 단추 개편:**
    - `지번 / 소유 구분` 영역의 클립보드 복사 부를 직관적인 한글 텍스트 단추 형태인 `[📋 주소 복사]` 로 갱신 이식합니다.

---

### 백엔드 컴포넌트 (Backend)

---

#### [MODIFY] [spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py)
- **이격거리 다양성 가드(Spatial Diversity Filter) 이식:**
    - `/spatial/recommend` API 내 최종 정렬 후보군 수집 루프(라인 660 부근)에 이미 누적된 선택 부지들과의 거리가 `diversity_deg` (미터법 환산도) 이내에 있는 후보지는 스킵하는 공간 필터를 구현합니다.

---

## Verification Plan

### Automated Tests
- `ahp_spatial_test.py` 스크립트를 재구동하여 가중치 락킹 및 추천 연산 12개 시나리오 패스 확인.
- 동일 주차장 및 극초근접 필지가 Top 1~5 목록에 중복 노출되지 않고 공간적으로 고르게 이격 분산되는지 확인.
