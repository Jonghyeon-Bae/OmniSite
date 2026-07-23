# 🛡️ OmniSite (옴니사이트) 콜드스타트 & 신규 환경 초기 가동 SOP (v1.3.0-stable)

본 문서는 신규 서버(AWS EC2, Docker Container, 온프레미스 PC 등) 설치 시나 기존 데이터베이스 완전 붕괴/초기화 상황에서도 **100% 재현 가능한 1-Click 콜드스타트 복구 및 최초 가동 절차**를 기술한 표준운용절차(SOP) 명세서입니다.

---

## 📌 1. 사전 환경 요건 (Prerequisites)

| 구성 요소 | 서버/환경 권장 사양 | 필수 확정 버전 / 확장 모듈 |
| :--- | :--- | :--- |
| **OS** | Windows 10/11 또는 Ubuntu 22.04 LTS | - |
| **DBMS** | PostgreSQL 15.x 이상 | **PostGIS**, **pgvector** (필수) |
| **Python** | Python 3.10 ~ 3.11 | `backend/venv` 가상환경 연동 |
| **Node.js** | Node.js v18.x ~ v20.x | npm 9.x 이상 |

---

## 📂 2. 대문자 `Datasets/` 콜드스타트 4단계 디렉터리 표준 구조

프로젝트 최상위 루트의 **`Datasets/`** 디렉터리는 콜드스타트 4단계 위저드 업로드 체계와 1:1 완벽하게 매칭됩니다:

```text
1.0-prototype/
└── Datasets/
    ├── 1_boundaries/             # [Step 1] 행정/법정동 경계 & 연계 매핑
    │   ├── 용산구_법정동_행정동_연계매핑.csv
    │   └── 읍면동.zip (emd.shp)
    ├── 2_cadastral/              # [Step 2] 부지 필지 지적도 & 국유부동산 정보
    │   ├── 05.용산구_부지면적_좌표(흡연부스 후보).csv (6,524 필지)
    │   └── 11. 국유부동산정보.csv (6,978 국유지)
    ├── 3_restrictions/           # [Step 3] 금연구역/이격거리 법정 금지구역
    │   └── 06. 06-07 금연구역 통합본.csv (268개 제한구역)
    └── 4_indicators/             # [Step 4] 도시 입지 복합 지표 데이터셋
        ├── 10. 소상공인시장진흥공단_상가.csv (6,509개 상가)
        ├── 서울시 버스정류소 위치정보_YONGSAN.csv
        ├── 02. 지하철역 위치.csv
        ├── BUS_STATION_BOARDING_MONTH_202605_YONGSAN.csv
        ├── CARD_SUBWAY_MONTH_202605_YONGSAN.csv
        ├── 07. 담배꽁초_상습_무단투기.csv
        └── LOCAL_PEOPLE_DONG_202605_YONGSAN_PEAK.csv
```

---

## 🚀 3. 콜드스타트 1-Click 파이프라인 가동 절차 (3-Step Execution)

신규 DB 생성 후 아래 3개 명령어를 순차적으로 실행하면 백엔드, DB, ML 모델이 100% 자동 구축됩니다.

### Step 1: 데이터베이스 스키마 생성 및 정제 데이터 시딩
```bash
# 프로젝트 최상위 루트에서 가상환경 파이썬으로 실행
backend\venv\Scripts\python seed_db.py
```
* **수행 내용**:
  1. PostGIS 및 pgvector 확장 모듈 자동 활성화.
  2. 11개 대상 테이블 Truncate 및 스키마 초기화.
  3. `Datasets/` 상대 경로에서 6,524개 필지, 6,509개 상가, 268개 제한구역, 414개 교통 노드, 38개 동 인구/민원 데이터 100% 무오류 자동 시딩.
  4. 기본 관리자 계정(`admin` / `admin1234`) 자동 생성.

### Step 2: XGBoost 적격부지 추천 ML 모델 자가 학습
```bash
backend\venv\Scripts\python backend\app\scripts\train_css_model.py
```
* **수행 내용**:
  1. DB `cadastral_lands` 및 공간 지표 결합 특성 행렬 생성.
  2. XGBoost 바이너리 분류 모델 훈련 및 `backend/app/models/xgboost_site_model.pkl` 저장.

### Step 3: E2E 통합 무결성 레그레션 테스트
```bash
backend\venv\Scripts\python backend\app\scripts\test_e2e_full_pipeline.py
```
* **수행 내용**:
  1. 관리자 로그인/인증 토큰 발급 (STEP 0)
  2. AHP 고정 및 이력 생성 (STEP 1~3)
  3. PDF RAG 자동 심의 및 pgvector 아카이빙 (STEP 4~5)
  4. Data Poisoning Guard 방어 및 롤백 검증 (STEP 6~7)
  5. XGBoost 온라인 재학습 트리가동 (STEP 8)
  6. **Outcome: `100% SUCCESS` 통과 확인**

---

## 🖥️ 4. 서비스 가동 가이드 (Running Application)

### Backend (FastAPI - Port 8000)
```bash
cd backend
venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend (Next.js Turbopack - Port 3000)
```bash
cd frontend
npm run dev
```

---

## 🔒 5. 개발 수칙 및 코드 동결 규정 (Strict Freeze & Prior Approval Rules)

1. **검증 완료 로직 완전 동결 (Strict Code Freeze)**:
   - **시딩 파이프라인 (`seed_db.py`)**: `Datasets/` 대문자 4단계 폴더 연동, 6,524 필지, 6,509 상가, 268 제한구역 시딩 파이프라인.
   - **Leaflet GIS 맵 엔진 (`page.js` & `spatial/page.js`)**: 비동기 싱글톤 로드, Ref 캐시 해제 `.enable()`, 마커 드래그 스로틀링 필터링 로직.
   - **위치 검증 엔진 (`spatial.py` & `spatial/page.js`)**: 법정 금연구역 버퍼 및 사용자 지정 임시금지구역(`user_exclusion_zones`) 마커 침범 감지 경고창(`alert`) 및 자동 위치 롤백 (`isWarning = false`) 로직.
   - **AI 모의 심의 토론 파이프라인 (`DebateSimulatorModal.jsx`)**: 심의 완료 시 DB 이력 상태 `'토론 완료'` 명시 로직.
2. **조장(USER) 사전 명시적 승인 필수 (Prior Explicit Approval Required)**:
   - 상기 동결 대상 로직의 변경이 필요한 기술적 논의가 발생할 경우, **반드시 조장(USER)에게 사유를 보고하고 사전 명시적 승인을 받은 이후에만 코드 수정 작업을 수행**합니다. 승인 없는 무단 코드 수정(mutating)은 엄격히 금지됩니다.
3. **동시성 문서 동기화**:
   - 아키텍처 및 파이프라인 수정 시 반드시 본 SOP 문서와 종합 연구노트, `.agents/AGENTS.md`를 동시 개정합니다.

---
**최종 검증일자**: 2026-07-23  
**시스템 상태**: `v1.3.0-stable-Rev140` 100% 콜드스타트 복구 & 사전승인 동결 규정 반영 완료
