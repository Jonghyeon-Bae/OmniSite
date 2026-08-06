# 🏛️ OmniSite SDSS v1.5.0 초기 설치 및 데이터셋 필수요소 통합 명세서 (Initial Setup & Datasets Specification)

본 문서는 **OmniSite SDSS v1.5.0-ZeroBias** 플랫폼을 처음 설치(Cold-Start)하거나 복구할 때 필요한 **소프트웨어 환경, 1_boundaries/2_cadastral/3_infrastructure 내 ESRI Shapefile (.shp/.dbf/.shx/.prj) 공간 레이어 세트를 포함한 Datasets/ 전체 실측 데이터셋 명세, 환경변수(.env) 키 규격, 1-Click 시딩 도구, 및 계정 승인 정책**을 총괄 정리한 필수 요구사항 명세서입니다.

---

## 📜 목차 (Table of Contents)
1. **필수 1. 소프트웨어 및 가상화 인프라 요구사항**
2. **필수 2. 데이터셋 (`Datasets/`) 디렉터리 및 ESRI Shapefile 공간 정보 레이어 포함 전체 실측 파일 명세**
3. **필수 3. 환경변수 (`.env`) 설정 및 키 규격**
4. **필수 4. 1-Click DB 자동 시딩 (`seed_db.py`) 및 ML 모델 학습 (`train_css_model.py`)**
5. **필수 5. 초기 시스템 계정 및 승인 권한 정책**
6. **초기화 체크리스트 (Initialization Checklist)**

---

## 1. 필수 1. 소프트웨어 및 가상화 인프라 요구사항

| 구분 | 소프트웨어 / 기술 | 최소 요구 버전 | 필수 역할 |
| :--- | :--- | :--- | :--- |
| **가상화** | **Docker Engine & Docker Compose** | Docker Engine 24.0+ & Compose v2 | 웹, 백엔드, DB 3대 서비스 컨테이너 격리 및 1-Click 실행 |
| **백엔드** | **Python** | **v3.11.0 이상** | FastAPI REST API, PostGIS 쿼리, PySHP, XGBoost ML, PyJWT, ReportLab PDF |
| **프론트엔드** | **Node.js** | **v18.17.0+ (v20 LTS 권장)** | Next.js 16.2 Turbopack App Router 및 Leaflet GIS 지도 |
| **데이터베이스**| **PostgreSQL & PostGIS** | **PostgreSQL 15+ & PostGIS 3.3+** | 6,524 필지 다각형/점 GIST R-Tree 공간 인덱싱 공간 연산 |

---

## 2. 필수 2. 데이터셋 (`Datasets/`) ESRI Shapefile 공간 정보 레이어 포함 전수 명세

시드 마이그레이션 도구(`seed_db.py`)가 데이터베이스 구축 시 파싱하는 `Datasets/` 하위 5대 영역 전체 공공 공간 데이터셋 파일 구조입니다.

> ⚠️ **ESRI Shapefile (.shp) 필수 구성 요소 주의사항**:
> 공간 정보 Shapefile을 파싱할 때 `.shp` 파일만 존재하면 Python `pyshp (shapefile.Reader)` 파싱 도중 `Missing shapefile component (.shx, .dbf)` 예외가 발생합니다. 반드시 **`.shp`(도형), `.dbf`(속성 DB), `.shx`(인덱스), `.prj`(좌표계)** 4종 필수 파일 세트가 동일 디렉터리에 상주해야 합니다.

```
Datasets/
├── 1_boundaries/                                # [1대 영역: 행정/법정동 공간 경계 레이어]
│   ├── 용산구_법정동_행정동_연계매핑.csv           # 법정동-행정동 코드 1:1 공간 매핑 테이블
│   ├── 시군구.zip / 읍면동.zip                   # 전국 지자체 행정구역 원본 압축 아카이브
│   └── extracted/                              # [법정동/행정동 경계 SHP 4종 세트]
│       ├── emd.shp                             # 1) 읍면동/행정동 다각형 공간 도형 파일
│       ├── emd.dbf                             # 2) 행정동 명칭 및 동코드 속성 DB
│       ├── emd.shx                             # 3) 공간 도형 인덱스 (pyshp 필수)
│       └── emd.prj                             # 4) EPSG:5179 좌표계 정의 파일
│
├── 2_cadastral/                                 # [2대 영역: 지적 필지 및 소유구분 레이어]
│   ├── 05.용산구_부지면적_좌표(흡연부스 후보).csv     # 6,524개 용산구 지적 필지 데이터셋
│   ├── 11. 국유부동산정보.csv                      # 국유지/공유지/사유지 소유 구분 매핑
│   ├── LSMD_CONT_LDREG_서울_용산구.zip           # 연속지적도 공간 원본 압축 아카이브
│   └── extracted/                              # [용산구 연속지적도 SHP 5종 세트]
│       ├── LSMD_CONT_LDREG_11170_202606.shp   # 1) 필지 다각형 공간 도형 파일
│       ├── LSMD_CONT_LDREG_11170_202606.dbf   # 2) PNU 번호, 지목, 면적 속성 DB
│       ├── LSMD_CONT_LDREG_11170_202606.shx   # 3) 공간 도형 인덱스 (pyshp 필수)
│       ├── LSMD_CONT_LDREG_11170_202606.prj   # 4) 좌표계 정의 파일
│       └── LSMD_CONT_LDREG_11170_202606.cpg   # 5) CP949 텍스트 인코딩 정의
│
├── 3_infrastructure/                            # [3대 영역: 공공 인프라 공간 레이어]
│   ├── 교량/                                    # [교량 공간 SHP 4종 세트]
│   │   ├── N3A_A0070000.shp                    # 1) 교량 다각형 공간 도형 파일
│   │   ├── N3A_A0070000.dbf                    # 2) 교량명 및 구조 속성 DB
│   │   ├── N3A_A0070000.shx                    # 3) 공간 도형 인덱스
│   │   └── N3A_A0070000.prj                    # 4) 좌표계 정의
│   └── 터널/                                    # [터널 공간 SHP 4종 세트]
│       ├── N3A_A0110020.shp                    # 1) 터널 다각형 공간 도형 파일
│       ├── N3A_A0110020.dbf                    # 2) 터널명 및 구조 속성 DB
│       ├── N3A_A0110020.shx                    # 3) 공간 도형 인덱스
│       └── N3A_A0110020.prj                    # 4) 좌표계 정의
│
├── 4_restrictions/                              # [4대 영역: 법정 규제 완충 회피 레이어]
│   ├── 06. 06-07 금연구역 통합본.csv               # 학교(200m)/어린이집(30m) 이격거리 (268개소)
│   ├── 07. 담배꽁초_상습_무단투기.csv              # 상습 무단투기 민원 개소 데이터
│   ├── 용산구_어린이집_유치원_통합_인허가정보.csv    # 보호구역 좌표 데이터
│   ├── 용산구_전체_흡연구역_폴리곤.csv              # 기존 설치 흡연구역 GIS 폴리곤
│   └── 서울특별시_용산구_흡연구역.csv
│
└── 5_indicators/                                # [5대 영역: 생활인구 및 상권 지표]
    ├── 서울시 버스정류소 위치정보_YONGSAN.csv        # 버스정류장 마스터 좌표
    ├── 02. 지하철역 위치.csv                       # 지하철역 마스터 좌표
    ├── BUS_STATION_BOARDING_MONTH_202605_YONGSAN.csv # 버스 승하차 유동인구 통계
    ├── CARD_SUBWAY_MONTH_202605_YONGSAN.csv       # 지하철 승하차 유동인구 통계
    ├── LOCAL_PEOPLE_DONG_202605_YONGSAN_PEAK.csv  # 피크 타임 생활인구 통계
    ├── 10. 소상공인시장진흥공단_상가.csv            # 6,509개 소상공인 상가 포인트
    ├── 02. 용산구_가로휴지통.csv
    └── 11. 용산구_유흥시설_통합_인허가정보.csv
```

---

## 3. 필수 3. 환경변수 (`.env`) 설정 및 키 규격

프로젝트 루트 디렉토리에 `.env` 파일을 작성해야 하며, 아래 키들이 필수 설정되어야 합니다.

```env
# 1. OpenAI API Key (AI 3자 모의 토론 및 RAG OCR 조례 해독 필수)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# 2. PostgreSQL DB 접속 URL (PostGIS 확장 포함)
DATABASE_URL=postgresql+psycopg://Admin:admin1234@database:5432/postgres

# 3. JWT 인증 암호화 키 (기본값)
JWT_SECRET_KEY=omnisite-sdss-v150-zerobias-jwt-secret-key-2026

# 4. 프론트엔드 ➔ 백엔드 REST API 통신 주소 (상용 배포 시 고정 공인 IP 매핑)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. 필수 4. 1-Click DB 자동 시딩 및 ML 모델 학습

환경 구축 후 단 2개의 파이썬 명령어로 전체 데이터베이스 및 인공지능 모델을 자동 시딩합니다.

### 4.1. 1-Click DB 시딩 및 공간 인덱싱 (`seed_db.py`)
```bash
docker-compose exec backend python seed_db.py
```
- **수행 내용**:
  1. PostgreSQL PostGIS 및 pgvector 확장(Extension) 자동 활성화
  2. `users`, `cadastral_parcels`, `commercial_shops`, `decision_histories`, `system_notices`, `community_posts` 6개 테이블 자동 생성
  3. `Datasets/` 폴더 내 1_boundaries(emd.shp), 2_cadastral(지적도.shp), 3_infrastructure(교량/터널.shp), 4_restrictions, 5_indicators 공간 데이터를 파싱하고 PostGIS GIST R-Tree 공간 인덱스 생성
  4. 사전 승인 최고 관리자 계정 (`admin` / `Admin1234!`) 시딩

### 4.2. 1-Click XGBoost ML 모델 자동 학습 (`train_css_model.py`)
```bash
docker-compose exec backend python app/scripts/train_css_model.py
```
- **수행 내용**: 시딩된 공간 통계와 민원 패턴을 기계학습하여 주민갈등도(CSS 0~100) 예측 모델을 생성 및 `app/models/registry/` 레지스트리에 자동 등록합니다.

---

## 5. 필수 5. 초기 시스템 계정 및 승인 권한 정책

- **초기 사전 승인 최고 관리자 계정**:
  - **아이디**: `admin`
  - **비밀번호**: `Admin1234!` (대문자 `A`, 숫자, 특수문자 `!` 필수)
  - **권한**: 관리자 콘솔 접근, 공지사항 등록, 신규 실무관 가입 승인 권한 보유.
- **신규 회원가입 실무관 계정 승인 정책**:
  - 실무관이 신규 회원가입(`/api/v1/auth/register`)을 진행한 계정은 보안상 기본적으로 **승인 대기 상태(`is_approved = FALSE`)**로 적재됩니다.
  - 최고 관리자(`admin`)로 로그인 후 `⚙️ 관리자 콘솔` ➔ `회원 승인 관리` 탭에서 **[승인]** 버튼을 클릭해야 정상 로그인 및 분석이 가동됩니다.

---

## 6. 초기화 검증 체크리스트 (Initialization Checklist)

- [ ] Docker Desktop 고래 아이콘 🐳 (`Running`) 가동 확인
- [ ] `.env` 파일 내 `OPENAI_API_KEY` 기입 확인
- [ ] `Datasets/1_boundaries/extracted/` 내 `emd.shp` 4종 세트 존재 확인
- [ ] `Datasets/2_cadastral/extracted/` 내 `LSMD_CONT_LDREG...shp` 5종 세트 존재 확인
- [ ] `Datasets/3_infrastructure/` 내 교량/터널 SHP 4종 세트(`.shp`, `.dbf`, `.shx`, `.prj`) 존재 확인
- [ ] `docker-compose up -d --build` (3개 컨테이너 구동)
- [ ] `docker-compose exec backend python seed_db.py` (`[+] All Coldstart Procedures completed successfully!` 확인)
- [ ] `docker-compose exec backend python app/scripts/train_css_model.py` (`SUCCESS: Model registration completed.` 확인)
- [ ] `http://localhost:3000` 접속 후 `admin` / `Admin1234!` 로그인 성공 확인
