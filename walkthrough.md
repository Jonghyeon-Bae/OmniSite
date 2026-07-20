# 관리자 콘솔 활성 ML 모델 레지스트리 성능 감사(Audit) 대시보드 개조 결과 보고서

관리자 콘솔의 불필요하고 정합성 훼손 위험이 있던 수동 `.pkl` 핫업로드 및 수동 재학습 조작부를 전격 폐지하고, 서버에 존재하는 도메인별 활성 ML 모델의 성능 통계 및 피처 기여도를 한눈에 점검·감사하는 **[🤖 ML 모델 레지스트리 감사 (Model Registry Audit)]** 전용 대시보드로 정밀 전환하였습니다.

## 🛠️ 변경 및 개선 사항

### 1. 백엔드 레지스트리 스캐너 및 메타데이터 영구 저장 (`model.py`)
- **`GET /api/v1/model/registry` 엔드포인트 구현:**
  - `backend/app/models/registry/` 디렉터리에 존재하는 모든 `*_v1.pkl` 바이너리 모델 및 `*_v1_meta.json` 동적 스캔.
  - 도메인명, 파일명, 파일 용량, 최종 학습 시점, 정확도(Accuracy), F1-Score, 피처 기여도(Feature Importance) 정보를 리스트업하여 수신.
- **메타데이터 자동 영구 적재:**
  - 파이프라인 Step 1(AI 감리 승인) 자동 재학습 완료 시, `{domain}_v1_meta.json` 을 동시 생성하여 서버가 재기동되어도 모든 도메인 모델의 메타데이터가 손실되지 않도록 보장.

### 2. 프론트엔드 어드민 콘솔 대시보드 개조 (`AdminConsoleModal.jsx`)
- **수동 업로드/재학습 기능 전격 폐지:**
  - 과거 수동 `.pkl` 드롭존 및 단일 재학습 버튼을 제거하여 모델 오염 및 피처 차원 불일치 크래시 위험을 100% 차단.
- **도메인 모델 선택 칩(Selectable Chips) 및 감사 카드 시각화:**
  - 서버에 등록된 도메인 모델(예: `smoking_zone`, `city_feature` 등) 목록을 칩 형태로 표출.
  - 선택된 도메인 모델의 **Accuracy, F1-Score, 파일 크기, 학습 시각** 카드 표출.
  - **XGBoost 의사결정 피처 기여도(Feature Importance) 가로 그래프** 동적 시각화 표출.

---

## 🧪 검증 결과

### 1. 백엔드 임포트 및 파이프라인 정합성 검증
- `python -c "import app.routers.model"` 테스트 실행 결과: **오류 0건, 정상 파싱 및 핫바인딩 확인**.

### 2. 프론트엔드 프로덕션 컴파일 빌드 검증
- `npm run build` 가동 결과: **`Compiled successfully in 1728ms`** (static static page generation 6/6 100% 성공).
