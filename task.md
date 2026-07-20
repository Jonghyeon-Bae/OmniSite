# ML 모델 레지스트리 성능 감사(Audit) 대시보드 전환 체크리스트

- [x] **1단계: 백엔드 모델 레지스트리 메타데이터 스캐너 및 API 구현 (`model.py`)**
  - [x] `background_model_train` 완료 시 `f"{domain}_v1_meta.json"` 에 accuracy, f1_score, feature_importances, trained_at 함께 저장하도록 강화
  - [x] `GET /api/v1/model/registry` 엔드포인트 구현: `registry_path` 내 모든 모델 메타데이터 스캔 및 동적 리스트 반환
  - [x] `GET /api/v1/model/registry/{domain}` 선택된 도메인 모델 메타데이터 단건 반환

- [x] **2단계: 어드민 콘솔 수동 핫업로드/재학습 제거 및 감사 대시보드 개조 (`AdminConsoleModal.jsx`)**
  - [x] 수동 `.pkl` 파일 핫업로드 드롭존 및 수동 재학습 트리거 버튼 전격 폐지
  - [x] "🤖 ML 모델 레지스트리 감사 (Model Registry Audit)" 탭으로 화면 개편
  - [x] 서버 등록 도메인 모델 리스트업 칩/드롭다운 UI 주입
  - [x] 선택된 모델의 accuracy, f1_score, trained_at 및 피처 중요도(Feature Importance) 가로 그래프 차트 렌더링

- [x] **3단계: 검증 및 동기화**
  - [x] 백엔드 파이프라인 정합성 검증 (`python -c "import app.routers.model"`)
  - [x] `npm run build` 가동하여 Next.js 프로덕션 빌드 무오류 통과 검증
  - [x] 연구노트 및 바탕화면 Workspace 파일 이관 동기화
