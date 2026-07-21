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
├── docker-compose.yml        # 로컬 테스트/개발용 컴포즈 설정
├── docker-compose.production.yml # 상용 배포용 컴포즈 설정
├── deployment_plan.md        # 상용 AWS 서버 이관 상세 문서
├── start_omnisite_local.bat  # 윈도우용 초간단 원클릭 실행 스크립트
└── README.md                 # 본 가이드라인 문서
```

---

## ⚡ 3. [초보자 및 행정실무용] 5분 초간단 실행 가이드 (더블클릭 기동)

컴퓨터 명령어나 개발 터미널에 친숙하지 않은 행정 실무자분들을 위해 **더블클릭 한 번으로 전체 시스템을 기동할 수 있는 자동 실행 프로그램**을 제공합니다.

### 3.1. 사전 필수 도구 다운로드 및 설치 (최초 1회만 수행)
아래의 3대 필수 도구를 링크에서 다운로드하여 기본 설정으로 컴퓨터에 설치해 주십시오.
1. **[Docker Desktop 설치](https://www.docker.com/products/docker-desktop/)**: 데이터베이스 기동을 위한 가상화 엔진입니다. (설치 후 실행하여 녹색 불이 켜진 상태를 확인해 주세요)
2. **[Python 3.11 설치](https://www.python.org/downloads/release/python-3119/)**: 백엔드 인공지능 분석용 엔진입니다. (설치 창 하단의 **[Add Python to PATH]** 체크박스를 반드시 체크한 후 설치해 주세요)
3. **[Node.js 20 설치](https://nodejs.org/)**: 웹 화면 렌더링용 플랫폼입니다. (LTS 버전을 권장합니다)

### 3.2. 더블클릭 기동 도구 실행
1. [Docker Desktop] 아이콘을 더블클릭하여 먼저 실행 상태로 둡니다.
2. 프로젝트 루트 폴더에 위치한 **`start_omnisite_local.bat`** (톱니바퀴 모양 아이콘) 파일을 마우스 더블클릭으로 실행합니다.
3. 시스템이 자동으로 데이터베이스를 구성하고, 파이썬 패키지를 인스톨한 뒤, 최초 1회 **공공 공간정보 데이터셋 벌크 적재(Cold Start)**를 알아서 집행합니다.
4. 약 30초~1분 대기하시면 크롬 브라우저가 알아서 켜지며 **`http://localhost:3000`** 대시보드 화면으로 즉시 연결됩니다!

---

## 💻 4. [개발자용] 로컬 직접 가동 가이드 (하이브리드 모드)

도커 가상화(WSL2)에 따른 시스템 리소스 낭비를 막고 IDE 디버깅을 기밀하게 집행하기 위해 데이터베이스만 Docker로 구동하고 프론트/백엔드는 로컬 셸에서 직접 기동하는 방식을 권장합니다.

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
