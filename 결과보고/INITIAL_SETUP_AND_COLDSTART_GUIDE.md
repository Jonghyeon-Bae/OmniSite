# 🚀 스마트시티 SDSS 옴니사이트(OmniSite) 최초 실행 및 콜드스타트 복구 가이드

본 문서는 **스마트시티 입지선정 의사결정 지원 시스템 (OmniSite)**을 신규 환경(개발 PC, AWS EC2, 시뮬레이션 서버)에 최초 설치하거나, DB 초기화/콜드스타트 테스트 후 기존 실측 데이터셋 상태로 100% 복구하기 위한 표준 운용 명세서(SOP)입니다.

---

## 📋 1. 사전 요구사항 (Prerequisites)

* **PostgreSQL + PostGIS**: 15.0 이상 (PostGIS 확장 필수)
* **Python**: 3.10+ (가상환경 `venv` 사용)
* **Node.js**: v18.0+ / npm v9.0+
* **권장 DB 스키마**: `postgres` (사용자: `Admin`, 비밀번호: `admin1234`, 포트: `5432`)

---

## 🛠️ 2. Step-by-Step 최초 설치 및 데이터 시딩 (Initial Setup)

### Step 1: 백엔드 환경 구축 및 패키지 설치
```bash
cd backend
python -m venv venv
# Windows PowerShell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: 최초 데이터 시딩 & DB 복구 (`seed_db.py`)
> **💡 주의**: `seed_db.py`는 실측 부지 데이터 6,524건(`05.용산구_부지면적_좌표(흡연부스 후보).csv`)과 타입별 금연구역/어린이집/학교 제한구역 268건(`06. 06-07 금연구역 통합본.csv`)을 PostGIS DB에 100% 무오류 시딩합니다.

```bash
# 프로젝트 최상위 루트 디렉토리에서 실행
python seed_db.py
```
* **수행 내용**:
  1. `cadastral_lands` PNU 파싱 중복 방지 가드(`11170...`) 자동 적용으로 6,524건 필지 수록.
  2. 제한구역 268건 타입별 규제 반경(`school`: 200m, `childcare_center`: 50m, `nosmoking_zone`: 10m) 차집합 시딩.
  3. 기본 관리자 계정 (`admin` / `admin1234`) 자동 생성.

### Step 3: 백엔드 uvicorn 서버 가동 (Port 8000)
```bash
cd backend
.\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: 프론트엔드 설치 및 가동 (Port 3000)
```bash
cd frontend
npm install
npm run dev
```

---

## 🔄 3. 콜드스타트 테스트 후 1-Click 원복 파이프라인 (Cold-start Recovery)

콜드스타트 위저드 테스트나 데이터 변경 후 이전의 원형 상태로 100% 복구하려면 아래 2개의 명령어를 순서대로 실행합니다.

```bash
# 1. DB 실측 원본 데이터셋 100% 재시딩 (6,524 필지 + 268 제한구역 + Admin 계정)
python seed_db.py

# 2. XGBoost 머신러닝 모델 자가 학습 재기동 (Accuracy 80.2% 달성)
python -c "import requests; print(requests.post('http://127.0.0.1:8000/api/v1/model/retrain').json())"
```

---

## 🧪 4. 전체 E2E 파이프라인 무결성 검증 (Regression Verification)

설치 또는 복구 완료 후 전체 시스템(AHP, 입지추천, PDF RAG Audit, ML 학습)이 100% 정상 작동하는지 검증합니다.

```bash
python backend/app/scripts/test_e2e_full_pipeline.py
```

* **정상 결과 확인 기준**:
  - `[E2E STEP 0 ~ 8] 100% SUCCESS`
  - XGBoost ML Accuracy: **0.8021 (80.2%) 이상**
  - Next.js 빌드: `npm run build` 결과 **0 Error, 0 Warning**

---

## 🚨 5. 주요 트러블슈팅 및 예방 수칙 (Troubleshooting)

1. **`InFailedSqlTransaction` 에러 발생 시**:
   - PostGIS 쿼리 내 지오메트리 SRID 불일치 또는 존재하지 않는 컬럼 참조 시 발생합니다.
   - `spatial.py` 내 `ST_SetSRID(c.geom, 4326)` 표기를 확인하십시오.
2. **Leaflet GIS 비동기 싱글톤 수칙 준수 (Freeze Rule)**:
   - `src/app/page.js` 및 `src/app/spatial/page.js` 파일의 맵 초기화 및 마커 스로틀링 로직은 기능 무결성이 검증된 상태이므로 향후 어떠한 개발 단계에서도 **절대로 수정해서는 안 됩니다.**

---

**작성일**: 2026-07-23  
**시스템 버전**: `v1.3.0-stable-Rev131`  
**관리자**: 스마트시티 SDSS 옴니사이트(OmniSite) 개발팀
