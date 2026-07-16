# [v1.2-alpha] 단계별 위저드형 공간정보 벌크 적재 및 웹 어드민 ML 재학습 구현 계획서

본 계획서는 **OmniSite v1.2-alpha**의 기능 무결성을 완결하기 위해, (1) 통합 어드민 콘솔의 콜드스타트 초기 구동 인프라 구축 방식을 기존의 일괄 zip 업로드에서 **"4단계 순차적 멀티업로드 위저드(Step-by-Step Wizard Ingestion Engine)"**로 전면 전환하고, (2) 독립 터미널 실행에 의존하고 있던 XGBoost ML 모델의 생성을 웹 UI 상에서 버튼 하나로 기동할 수 있도록 백엔드 훈련 API 및 프론트엔드 UX를 연동하기 위한 설계서입니다.

---

## User Review Required

> [!IMPORTANT]
> 1. **단계별 위저드형 공간 데이터 인제스천 체계 도입:**
>    * 일관 zip 방식은 오류가 났을 때 원인 규명이 어렵고 유연성이 떨어집니다. 따라서 이를 **4단계 순차적 위저드 UI**로 변경합니다.
>    * 이전 단계를 성공해야만 다음 단계 업로드 드롭존이 활성화되는 프론트엔드 상태 제어(State Guard)를 통해 공간 DB 외래키(FK) 의존성 크래시를 원천 차단합니다.
> 2. **지리지표 멀티 업로드 및 "건너뛰기(Skip)" 정책 수립:**
>    * 3단계 지리지표 CSV 업로드 시 여러 파일을 드래그 앤 드롭으로 던지면 개별 분석 프로그레스바가 노출되고, 아직 데이터가 구축되지 않은 지표의 경우 **"건너뛰기(Skip)"**를 눌러 유연하게 다음 단계로 전향할 수 있게 설계합니다.
> 3. **웹 관리자 콘솔 전용 ML 모델 재학습(Retraining) API 개설 및 핫 스왑:**
>    * 백엔드에 `/api/v1/model/retrain` API를 개설하여, 사용자가 웹 브라우저 상에서 버튼 하나로 내장 데이터셋(`css_train_dataset.csv`)을 통한 XGBoost 모델 훈련을 트리거하고, 즉시 생성된 `.pkl` 모델 객체를 인메모리 싱글톤 레지스트리에 핫 스왑 로딩하도록 구현합니다.

---

## Proposed Changes

### 1. 백엔드(FastAPI) 단계별 개별 적재 엔드포인트 설계

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)
* **`POST /api/v1/upload/seed-spatial-step1` (뼈대 구축):**
  * 업로드 인자: 시군구 SHP 세트, 읍면동 SHP 세트, 법정동-행정동 연계 CSV (멀티파트 업로드).
  * 역할: 기존 `init_coldstart`에서 뼈대 적재 부문만 격리하여 `districts`, `dong_boundaries`에 대한 공간 DB 기초 프레임을 빌드합니다.
* **`POST /api/v1/upload/seed-spatial-step2` (지적도 구축):**
  * 업로드 인자: 연속지적도(LSMD) SHP 세트, 국유부동산 대장 CSV (선택).
  * 역할: 1단계에서 완성된 법정동 경계 데이터(`dong_boundaries`)를 기준으로 연속지적도 도형을 centroid 공간 연산(`ST_Contains`)하여 `cadastral_lands` 테이블에 완벽한 지적 마스터 데이터를 적재합니다.
* **`POST /api/v1/upload/seed-spatial-step3` (지리지표 멀티 적재):**
  * 업로드 인자: 개별 CSV 파일 및 타겟 테이블 정보 (예: `restricted_zones`, `transit_stations`, `transit_passengers`, `population_stats`).
  * 역할: 개별적으로 업로드되는 벌크 CSV 파일에 대해 인코딩 및 컬럼 정합성을 판독하고, 각각의 타겟 DB 테이블에 공간 포인트 변환 등을 수반하여 즉시 인서트 처리합니다.
* **`POST /api/v1/upload/seed-spatial-step4` (최종 완성 및 락 해제):**
  * 역할: 시딩 완료 트랜잭션을 확정하고, 초기 부팅 상태 마크를 해제하여 SDSS 의사결정 시뮬레이터 본체를 활성화합니다.

#### [NEW] [model.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/model.py)
* **모델 재학습 및 성능 상태 조회 라우터 신규 구현:**
  * `POST /api/v1/model/retrain`: 훈련 요청 수신 시 `BackgroundTasks`를 통해 Uvicorn 스레드 차단 없이 XGBoost 모델 훈련 파이프라인(`train_css_model.py` 로직 내재화)을 비동기 구동합니다. 훈련이 성공적으로 완료되면 즉시 `backend/app/models/registry/smoking_zone_v1.pkl`로 모델을 물리 저장하고 `model_registry.load_models()`를 강제 기동하여 핫 리로드(Hot Swap)를 완결합니다.
  * `GET /api/v1/model/status`: 현재 로드되어 가용 중인 XGBoost 모델의 F1-Score 등 성능 검증 지표와 변수 중요도(Feature Importance) 정보를 프론트엔드로 전달합니다.

#### [MODIFY] [main.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/main.py)
* 신규 작성한 `model_router`를 가져와 `app.include_router(model_router)`를 통해 정식 등록 및 CORS 정책을 통합 바인딩합니다.

---

### 2. 프론트엔드(Next.js) 4단계 시각화 위저드(Wizard) UI 구현

#### [MODIFY] [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/spatial/page.js)
* **어드민 콘솔 초기 구동 설정 UI를 "단계별 위저드 모드"로 개편:**
  * **상태 관리 장착 (`step` 및 `uploadStatus`):**
    * `Step 1 (뼈대 구축)`: 시군구/읍면동 SHP 세트 + 법정동 연계 CSV 업로드 드롭존 노출. 업로드 성공 시에만 `Step 2` 활성화.
    * `Step 2 (토지 정보)`: 지적도 SHP 세트 + 국유지 CSV 업로드 드롭존 활성화. 성공 시 `Step 3` 활성화.
    * `Step 3 (지리지표 멀티 업로드)`: 4대 핵심 지수 CSV 멀티 업로드 드롭존 설계. 개별 파일들의 적재 진행 상태를 순차적 프로그레스바로 시각화. 완료 전이라도 **"건너뛰기(Skip)"** 버튼을 허용하여 런타임 유연성 보장.
    * `Step 4 (최종 락 해제)`: 초기 구동 완료 플래그 적용 및 ML 모델 훈련 세션 안내.
  * **"🤖 ML 모델 재학습" 탭 연동:**
    * 탭 진입 시 백엔드 `/api/v1/model/status`를 호출하여 학습 상태 및 피처 중요도 차트를 실시간 출력합니다.
    * **"⚡ ML 모델 최초 생성 및 재학습 기동"** 버튼을 배치하고, 클릭 시 `/api/v1/model/retrain` API를 트리거하여 비동기식 훈련 프로그레스 로딩 바를 화면에 활성화합니다. 훈련 성공 모달 표출 후 status를 automatic 갱신 리렌더링하도록 훅 구조를 결합합니다.

---

## Verification Plan

### Automated Tests
1. **단계별 Ingestion API 검증:**
   * Step 1 API를 호출해 `districts`와 `dong_boundaries`가 구축되는지 확인.
   * Step 2 API를 호출해 Step 1의 `dong_boundaries`와 기하적으로 contains 조인되어 `cadastral_lands`가 정상 인서트되는지 외래키 충돌 여부 확인.
   * Step 3 개별 API 호출 및 건너뛰기 수행 시, 건너뛴 지표들에 대한 null 데이터 예외가 ML/AHP 엔진에서 안전하게 예외처리되는지 검증.
2. **ML Retrain API 검증:**
   * `/api/v1/model/retrain` 호출 후 백그라운드 학습이 성공하여 `smoking_zone_v1.pkl` 파일 타임스탬프가 최신화되고 레지스트리에 핫스왑 로딩되는지 서버 콘솔 로그 검증.

### Manual Verification
1. 브라우저에서 통합 어드민 콘솔 모달의 `초기 구동 설정` 탭을 열어 1단계부터 4단계까지의 상태 가이드와 비동기 프로그레스바가 정합성 있게 변경/잠금해제되는지 테스트합니다.
2. 3단계 지리지표 적재 중 "건너뛰기"가 정상 작동하며, 최종 4단계에서 ML 모델 생성 버튼 기동 시 학습 완료 모달이 표출되는지 검증합니다.
