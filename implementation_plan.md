# 관리자 콘솔 ML 모델 레지스트리 성능 감사(Audit) 대시보드 개조 계획서

관리자 콘솔의 불필요하고 왜곡 위험이 있는 수동 ML 모델 핫업로드 및 단일 ML 재학습 탭을 전격 폐지하고, 서버 상에 활성화된 도메인별 ML 모델 목록을 조회하여 성능 지표(Accuracy, F1-Score, Feature Importance)를 감사(Audit)하는 전용 모니터링 대시보드로 정밀 전환합니다.

## User Review Required

> [!NOTE]
> 본 개조를 통해 관리자 콘솔(`AdminConsoleModal.jsx`)의 수동 `.pkl` 핫업로드 폼과 수동 재학습 트리거 버튼이 완전 삭제되며, 오직 실존 모델의 감사 및 조회를 담당하는 **"🤖 ML 모델 레지스트리 성능 감사"** 탭으로 전면 일원화됩니다.
> 실시간 모델 재학습은 파이프라인 Step 1(AI 감리 승인 시)의 자동 선순환 피드백 체계를 통해 구동됩니다.

## Proposed Changes

### Backend Component

#### [MODIFY] [model.py](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/최종1차/1.0-prototype/backend/app/routers/model.py)
- `GET /api/v1/model/registry` 엔드포인트 신설:
  - `backend/app/models/registry/` 디렉터리 내의 모든 `*_v1.pkl` 파일들을 탐색.
  - 각 모델 파일별 **도메인명(domain_tag), 파일 크기, 최종 수정시각(last_trained_at), 정확도(accuracy), F1-Score(f1_score), 피처 중요도 딕셔너리(feature_importances)**를 추출하여 동적 리스트로 반환.
  - 파이프라인 dumps 시 성능 메타데이터를 함께 저장하도록 `background_model_train` 수정.

### Frontend Component

#### [MODIFY] [AdminConsoleModal.jsx](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/최종1차/1.0-prototype/frontend/src/components/AdminConsoleModal.jsx)
- 기존 "ML 핫업로드" 및 "ML 재학습" 탭 텍스트 및 조작 버튼 제거/통합 ➔ **"🤖 ML 모델 레지스트리 감사 (Model Registry Audit)"** 탭으로 개편.
- 상단/좌측 도메인 선택 칩(예: `smoking_zone`, `city_feature` 등) UI 추가.
- 선택된 모델의 주요 지표 카드(정확도, F1-Score, 최종 재학습 시각) 및 **XGBoost 피처 기여도(Feature Importance) 막대 차트** 표출.

## Verification Plan

### Automated Tests
- `python -c "import app.routers.model"` 구문 정합성 및 백엔드 라우트 임포트 테스트.
- `npm run build` 가동하여 Next.js 프론트엔드 최적화 빌드 컴파일 무오류 통과 검증.

### Manual Verification
- 백엔드 `/api/v1/model/registry` 엔드포인트 호출 시 `models/registry/` 내의 `.pkl` 파일 목록 및 상세 성능 메타데이터 정상 리턴 확인.
- 어드민 콘솔 모달 진입 시 수동 업로드/재학습 버튼이 제거되고 도메인별 모델 선택 시 피처 중요도 그래프 및 통계 지표가 동적으로 갱신되는지 확인.
