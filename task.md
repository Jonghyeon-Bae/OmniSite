# OmniSite 6단계 공간계획 피드백 루프 개조 작업 체크리스트

- [x] **1단계: 백엔드 XGBoost 동적 피처 파이프라인 개조 (`model.py`)**
  - [x] `background_model_train` 이 `domain` 매개변수를 수용해 `f"{domain}_v1.pkl"` 로 분기 저장되도록 수정
  - [x] `restricted_zones` 내 모든 고유 `zone_type` 을 자동 스캔하여 SQL 최단 거리 피처 생성부를 동적으로 빌딩하는 모듈 이식
  - [x] `/train` API 엔드포인트 수정 및 동적 도메인 바인딩

- [x] **2단계: 메인 페이지 `pipelineStep` 6단계 확장 및 연동 (`page.js`)**
  - [x] `pipelineStep` 최대 범위를 6으로 확장
  - [x] Step 1 감리 완료 시, 데이터 커밋 후 비동기 `/model/train` 을 호출하며 자동으로 Step 2(ML 검증)로 전이하도록 개조
  - [x] 기존 컴포넌트 렌더링에 매핑된 `pipelineStep` 상태 분기를 각각 한 단계씩 슬라이딩 매핑 (`2 ➔ 3`, `3 ➔ 4`, `4 ➔ 5`, `5 ➔ 6`)

- [x] **3단계: 사이드바 제어 패널 `pipelineStep === 2` UI 추가 (`SidebarControl.jsx`)**
  - [x] `pipelineStep === 2` 인 구간에 XGBoost 훈련 로딩 및 실제 통계 리포트 (Accuracy, F1-Score) 시각화 카드 구현
  - [x] Feature Importance 막대 그래프 시각화 차트 이식
  - [x] 다음 단계 진행을 위한 가중치 모델 승인 (`setPipelineStep(3)`) 버튼 및 기존 모델 유지 진행 버튼 탑재

- [x] **4단계: 기존 패널 및 모달 슬라이딩 조건 동조 (`OptimalResultPanel.jsx`, `DebateSimulatorModal.jsx`)**
  - [x] `OptimalResultPanel.jsx` 의 Step 2 HITL 위치 보정 렌더링 조건을 `3` 으로 변경
  - [x] `OptimalResultPanel.jsx` 의 Step 4 추천 입지 선정 렌더링 조건을 `5` 로 변경
  - [x] `DebateSimulatorModal.jsx` 의 토론 시뮬레이터 락킹 단계를 `6` 으로 변경

- [x] **5단계: 빌드 컴파일 검증 및 통합 시나리오 테스트**
  - [x] `npm run build` 가동하여 Next.js 프로덕션 빌드 무오류 통과 검증
  - [x] 데이터 업로드 ➔ 감리 승인 ➔ 자동 재학습 ➔ 정확도 검증/승인 ➔ HITL 보정 ➔ AHP ➔ 결과 ➔ 토론 시나리오 정상 동작 검증
