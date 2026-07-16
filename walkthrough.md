# 6단계 공간계획 피드백 루프 아키텍처 개조 완료 보고서

OmniSite 메인 시나리오 파이프라인의 원래 5단계 순서(AI 감리 ➔ 사용자 위치 지정 HITL ➔ AHP ➔ 결과 ➔ 토론)의 설계를 완벽히 보존한 채, **XGBoost 님비 예측 모델의 실시간 재학습 검증 단계(Step 2)**를 우아하게 결합하여 **총 6단계 선순환 아키텍처**로 개조 완료하였습니다.

---

## 🛠️ 변경 및 완공된 사항

### 1) 백엔드 XGBoost 동적 공간 피처 연동 및 도메인 분기 (`model.py`)
- **자동 피처 스캔 및 SQL 제너레이터 구축:** 사용자가 업로드하고 감리를 통과한 신규 규제 도메인(`zone_type`)을 PostGIS 상에서 자동으로 런타임 스캔하여, `dist_to_[zone_type]` 거리를 자동으로 계산 및 가중 학습 피처로 동적 반영하는 SQL Generator 모듈을 빌딩 완료했습니다.
- **도메인 쿼리 바인딩 및 분기 저장:** `/retrain` API 기동 시 `domain` 파라미터를 받아 `f"{domain}_v1.pkl"` 형태로 독립된 XGBoost 모델 파일을 핫스왑 직결 적재하도록 변경하였습니다.
- **사용자망 권한 완화:** 메인 시뮬레이션 중 실무관 세션(User)에서도 훈련 상태를 동기적으로 조회할 수 있도록 `/retrain` 및 `/status` 엔드포인트의 JWT 가드 의존성을 `get_current_user` 로 완화했습니다.

### 2) 메인 파이프라인 6단계 슬라이딩 동조 (`page.js`)
- `pipelineStep` 의 상태 범위를 6단계로 확장하고 아래와 같이 컴포넌트 렌더링 분기를 일괄 상향 슬라이딩 이식하였습니다.
- **Step 1:** AI 감리 및 데이터 업로드 ➔ 승인(Approve) 시 백엔드 비동기 `/retrain` API를 자동 호출하고 `Step 2` 로 전이.
- **Step 2 (NEW):** ML 재학습 검증 및 정확도/F1-Score 보고 승인.
- **Step 3 (기존 Step 2):** 사용자 위치 지정 HITL (`OptimalResultPanel.jsx` L35)
- **Step 4 (기존 Step 3):** AHP 가중치 설정 및 Lock (`SidebarControl.jsx` L135)
- **Step 5 (기존 Step 4):** 추천 입지 선정 결과 Top 5 (`OptimalResultPanel.jsx` L136)
- **Step 6 (기존 Step 5):** 페르소나그룹 AI 토론 (`OptimalResultPanel.jsx` L274)

### 3) 사이드바 Step 2 프리미엄 ML 검증 패널 구현 (`SidebarControl.jsx`)
- `pipelineStep === 2` 분기에 나타날 로딩 및 통계 보고 패널을 HSL 테일러드 컬러 가이드에 맞춰 미려하게 완공했습니다.
- 훈련 기동 중일 때는 엠버 컬러 스피너 애니메이션이 가동되며, 훈련 완료 시 **Accuracy/F1-Score 및 Feature Importance 차트**가 실시간 갱신 플롯됩니다.
- 하단에 **`[✓ 신규 예측 가중치 승인 및 진행]`** 버튼과 **`[이전 가중치 모델 유지 후 진행]`** 버튼을 탑재하여 완벽한 HITL 피드백 루프를 수립했습니다.

---

## 🧪 검증 결과 및 산출물

1. **Next.js 프로덕션 컴파일 빌드 테스트**
   - 변경된 Javascript 컴포넌트들의 컴파일 정합성을 검증하기 위해 `npm run build`를 수행하여 **오류 없이 100% 컴파일 완공**을 확인하였습니다.
2. **Uvicorn API 서버 기동 상태 유지**
   - 백엔드 재기동 시 태스크 안전 가드로 `app.main` 인스턴스를 Port 8000에서 정상 리스타트하여 비동기 모델 백그라운드 스레드가 백그라운드 태스크(Task ID: 1286)로 무오류 활성 동작 중임을 검증하였습니다.
