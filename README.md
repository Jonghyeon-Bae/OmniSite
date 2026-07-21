# OmniSite (옴니사이트): 다목적 스마트시티 입지선정 의사결정 지원 시스템 (SDSS)

OmniSite는 다기준 의사결정 분석기법(**AHP**)과 **XGBoost** 주민 갈등도(CSS) 예측 머신러닝, 그리고 **OpenAI pgvector** 기반의 사후 행정 공문서 RAG OCR 교차 검증을 융합한 지능형 공간 의사결정 지원 시스템(SDSS)입니다.

---

## 🛠️ 1. 기술 스택 (Technology Stack)

- **Frontend**: Next.js 16.2 (Turbopack), Vanilla CSS, Leaflet GIS Map
- **Backend**: FastAPI 0.110 (Python 3.11), SQLAlchemy, Uvicorn, Gunicorn
- **Database**: PostgreSQL 15 + PostGIS 3.3 (공간 데이터 인덱싱 R-Tree)
- **Machine Learning**: XGBoost Classifier, Scikit-Learn
- **Audit AI**: OpenAI GPT API, pgvector, PyPDF OCR Parser

---

## 📂 2. 디렉토리 구조 (Directory Structure)

```
1.0-prototype/
├── backend/                  # FastAPI 백엔드 모듈
│   ├── app/
│   │   ├── routers/          # AHP, Spatial, ML, Upload 라우터 API
│   │   ├── utils/            # 공간 연산 및 보안 필터링
│   │   └── main.py           # 백엔드 진입점
│   ├── requirements.txt      # 백엔드 의존성 패키지 명세
│   └── Dockerfile            # 백엔드 상용 빌드 파일
├── frontend/                 # Next.js 프론트엔드 모듈
│   ├── src/
│   │   └── app/              # 메인 대시보드 및 GIS 지도 화면
│   ├── package.json          # 프론트엔드 의존성 패키지 명세
│   └── Dockerfile            # 프론트엔드 상용 빌드 파일
├── Datasets/                 # 최초 공간 GIS 시드 데이터셋 (도메인 격리)
├── DB/                       # PostgreSQL 초기 초기화 스크립트
├── seed_db.py                # 공공 데이터셋 DB 마이그레이션 도구
├── docker-compose.yml        # 로컬 테스트/개발용 컴포즈 설정
├── docker-compose.production.yml # 상용 배포용 컴포즈 설정
├── deployment_plan.md        # 상용 AWS 서버 이관 상세 문서
└── README.md                 # 본 가이드라인 문서
```

---

## 🐳 3. [비개발자/실무자용] 도커 기반 원클릭 실행 및 콜드스타트 상세 가이드

개발 환경 구축이나 컴퓨터 셸(Shell) 명령어에 낯선 행정 실무자분들도 **복잡한 수동 프로그램 설치 없이 단 3개의 명령어만으로 시스템을 무결하게 기동**하실 수 있습니다. 각 명령어가 수행하는 역할과 예상되는 화면 결과를 자세히 확인하면서 진행해 주십시오.

### 3.1. 사전 준비 사항
1. **[Docker Desktop 설치 및 실행]**: [도커 데스크탑 다운로드](https://www.docker.com/products/docker-desktop/)에서 프로그램을 받아 기본 설정으로 설치한 뒤 실행하여 **우측 하단 고래 아이콘에 녹색 불(Running)**이 켜져 있는지 확인합니다.
2. **OpenAI API Key 입력**: 프로젝트 폴더 루트에 위치한 `.env` 파일을 메모장으로 열고, 사용하시는 OpenAI API Key를 기입하고 저장합니다.
   ```env
   OPENAI_API_KEY=sk-proj-your-api-key-here
   ```

---

### 3.2. E2E 콜드스타트 설치 순서 및 예상 결과 (timeline)

터미널(Cmd 또는 PowerShell)을 열고 프로젝트 폴더 경로에서 아래 명령어들을 순서대로 한 줄씩 복사하여 입력해 주십시오.

#### 1단계: 가상 환경 조립 및 데이터베이스 생성
- **명령어**:
  ```bash
  docker-compose up -d --build
  ```
- **어떤 과정인가요?**: 옴니사이트 기동에 필수적인 3개 컨테이너(웹 화면, AI 백엔드 서버, 공간 데이터베이스)를 가상 공간에 다운로드하고 조립하는 단계입니다. 최초 기동 시 데이터베이스에 테이블 스키마(구조)도 자동 생성됩니다.
- **예상되는 화면 로그**:
  ```text
  ✔ Network omnisite_default      Created
  ✔ Container omnisite_dev_db     Started
  ✔ Container omnisite_dev_be     Started
  ✔ Container omnisite_dev_fe     Started
  ```
- **성공 확인**: Docker Desktop 화면에서 3개 서비스가 모두 **초록색 아이콘(Running)**으로 켜져 있으면 성공입니다.

#### 2단계: 공공 지리 정보 공간 데이터셋 적재 (Seeding)
- **명령어**:
  ```bash
  docker-compose exec backend python seed_db.py
  ```
- **어떤 과정인가요?**: 텅 빈 데이터베이스에 [버스/지하철 정류소 위치, 유동인구 통계, 상습 무단투기 구역, 자치구 동 경계선] 등의 **용산구 실측 공공 데이터셋을 벌크로 밀어 넣는 필수 데이터 마이그레이션 단계**입니다.
- **예상되는 화면 로그 (콘솔 하단)**:
  ```text
  [1] Connecting to database...
  [1-1] Activating SQL extensions (postgis, vector)...
  [2] Truncating target tables...
  ...
  [9] Seeding population_stats & age_demographics & civil_complaints...
      Seeded 38 population stats.
  [+] Seeding completed successfully!
  ```
- **성공 확인**: 화면 맨 마지막 줄에 **`[+] Seeding completed successfully!`** 라는 영어 문구가 보이면 성공적으로 마이그레이션이 끝난 것입니다.

#### 3단계: 갈등 예측 인공지능(ML) 두뇌 학습 및 등록
- **명령어**:
  ```bash
  docker-compose exec backend python app/scripts/train_css_model.py
  ```
- **어떤 과정인가요?**: 2단계에서 적재한 공간 정보 데이터를 토대로, 특정 필지의 주민 갈등 민감도(CSS)를 기계 학습하여 채점하는 **XGBoost AI 예측 모델의 최초 훈련(Coldstart Training) 단계**입니다.
- **예상되는 화면 로그**:
  ```text
  === [PHASE 1: STARTING CSS ML MODEL TRAINING] ===
  Training set: (5253, 5), Test set: (1314, 5)
  Fitting final XGBoost pipeline model...
  ...
  Serializing and saving pipeline model to: app/models/registry/smoking_zone_v1.pkl
  SUCCESS: Model registration completed.
  ```
- **성공 확인**: 최종적으로 **`SUCCESS: Model registration completed.`** 문구가 출력되면 기계 학습이 정상 완료되고 플랫폼이 실사용 가능 상태가 됩니다.

---

### 3.3. 최초 시스템 로그인 및 보안 설정
- **웹 서비스 접속 주소**: 인터넷 브라우저 주소창에 [http://localhost:3000](http://localhost:3000) 을 입력해 접속합니다.
- **초기 관리자 자격 증명**:
  - **아이디**: `admin`
  - **비밀번호**: `admin1234`
- **보안 조치**: 최초 로그인에 성공하면 시스템이 자동으로 **`초기 비밀번호 강제 변경 창`**을 띄웁니다. 반드시 업무용 신규 패스워드를 설정하고 재로그인해 주십시오.

---

## 💻 4. [개발자 디버깅용] 로컬 직접 가동 가이드 (하이브리드 모드)

가상화(WSL2)에 따른 시스템 리소스 낭비를 막고 IDE 소스코드 디버깅을 기밀하게 집행하기 위해 데이터베이스만 Docker로 구동하고 프론트/백엔드는 로컬 셸에서 직접 기동하는 방식입니다.

### 4.1. DB 컨테이너 단독 백그라운드 구동
```bash
# 프로젝트 루트 디렉토리에서 실행
docker-compose up database -d
```

### 4.2. 백엔드(FastAPI) 개발 서버 실행 및 데이터 초기화
```bash
# 1. backend 디렉터리로 진입
cd backend

# 2. 파이썬 가상환경 생성 및 의존성 패키지 인스톨
python -m venv venv
venv\Scripts\activate      # Windows (Cmd 기준)
pip install -r requirements.txt

# 3. 최초 1회 공간 GIS 시드 데이터 마이그레이션 적재 (10초 소요)
python app/scripts/clean_and_organize_datasets.py
python app/scripts/create_decision_histories_table.py
python app/scripts/train_css_model.py

# 4. FastAPI 개발 핫리로드 서버 가동 (포트 8000 오픈)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4.3. 프론트엔드(Next.js) 개발 서버 실행
```bash
# 1. frontend 디렉터리로 진입
cd frontend

# 2. 노드 패키지 의존성 인스톨 및 핫리로드 개발 서버 실행 (포트 3000 오픈)
npm install
npm run dev
```
브라우저에서 `http://localhost:3000` 으로 접속하여 실시간 분석을 테스트하십시오.

---

## 🐳 5. 상용 배포 가이드 (AWS Lightsail 등)

실제 프로덕션 서버에 Docker 이미지 기반 정적 배포를 가동하는 절차입니다.

### 5.1. 상용 운영 환경변수 설정 (`.env`)
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 키값을 채워 넣습니다:
```env
OPENAI_API_KEY=your_real_openai_api_key
NEXT_PUBLIC_API_URL=http://your_aws_static_ip_here:8000
```
> [!WARNING]
> - `NEXT_PUBLIC_API_URL` 값에 localhost 대신 **클라우드 공인 고정 IP**를 정확히 기입하여 빌드해야 브라우저의 CORS 통신 차단 오류가 발생하지 않습니다.

### 5.2. 도커 컴포즈 프로덕션 가동
```bash
# 루트 디렉토리에서 상용 최적화 빌드 기동
docker-compose -f docker-compose.production.yml up --build -d
```

---

## 💡 6. 무편향성 고지 및 데이터셋 주의사항
- **MVP 데이터 편향**: 제공된 `Datasets/` 폴더 내의 기본 좌표 및 보호 구역 레이어는 스마트 흡연부스 MVP 검증을 위해 타겟 프로토타이핑되어 수록되어 있습니다.
- **다목적 SDSS 운용**: 본 OmniSite 엔진은 다목적 범용 아키텍처로 수립되어 있습니다. 공유킥보드, 전기차 충전소 등 타 인프라 입지선정을 진행할 시에는 데이터베이스의 `domain_regulation_rules` 테이블 내부 이격거리 규격과 실측 지표 레이어를 설치하려는 목적에 맞게 사전 튜닝 매핑하여 사용해 주십시오.
