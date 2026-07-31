# [OmniSite SDSS] 콜드스타트(최초 구동) 및 최종 상용 배포 종합 가이드라인 (실측 검증 완료)

---

## Executive Summary

본 가이드라인은 OmniSite SDSS 플랫폼을 신규 서버, 로컬 컴퓨터, 또는 클라우드 가상 사설 서버(AWS Lightsail 등)에 **최초 설치 및 기동(Coldstart)**할 때 필요한 **데이터 시딩 파이프라인, 원클릭 시동 도구(`start_omnisite_local.bat`) 사용법, 상용 배포 절차 및 실측 무결성 검증 체계**를 100% 실측 파일 경로에 맞춰 기술한 정식 운영 매뉴얼입니다.

---

## 🚀 1. 콜드스타트 (Coldstart) 실측 아키텍처 및 데이터 생태계

### 📁 Datasets/ 실제 6대 디렉터리 구조 (Real Physical Structure)
OmniSite는 최초 구동 시 프로젝트 루트의 `Datasets/` 디렉터리에 위치한 6대 물리 폴더 및 데이터를 읽어 PostGIS 데이터베이스에 자동 파싱 적재합니다:

```
Datasets/
├── 1_boundaries/       # 용산구 법정동-행정동 연계매핑 CSV 및 36개 법정동 Shapefile(emd.shp)
├── 2_cadastral/        # 05.용산구 부지면적 좌표(6,524 필지) 및 11.국유부동산정보(국공유지)
├── 3_infrastructure/   # 교량(N3A_A0070000.shp) 및 터널(N3A_A0110020.shp) 공간 배제 지오메트리
├── 4_restrictions/     # 06.금연구역 통합본 및 07.담배꽁초 상습 무단투기 지역
├── 5_indicators/       # 버스정류장, 지하철역, 유동인구 통계, 소상공인 상가(6,509개소)
└── 6_duplicates/       # 격리 수록된 구버전/중복 보관 데이터셋
```

---

## ⚡ 2. 콜드스타트 시딩 실행 절차 (Coldstart Execution Flow)

1. **루트 시딩 파이프라인 실행 (`seed_db.py`)**:
   ```bash
   # 프로젝트 루트(1.0-prototype) 위치에서 실행
   python seed_db.py
   ```
   - **실측 시딩 결과**:
     - `cadastral_lands`: 6,524개 지적 필지 적재 및 GIST 공간 인덱스/이격거리 선계산 ($O(1)$) 빌드.
     - `commercial_shops`: 6,509개 상가업소 위치 적재.
     - `restricted_zones`: 268개 법정 배제구역(학교 200m, 어린이집 50m, 금연구역 10m, 육교/터널 15m) 적재.
     - `emd_boundaries`: 용산구 36개 법정동 정밀 MultiPolygon 경계 적재.

2. **XGBoost ML 주민갈등도($CSS$) 모델 훈련**:
   ```bash
   cd backend
   python app/scripts/train_css_model.py
   ```
   - `smoking_zone_v1.pkl` 피클 모델 바이너리 생성 및 메모리 레지스트리 핫스왑.

---

## 💻 3. 원클릭 실행 런처 (`start_omnisite_local.bat`) 수리 완료 내역

이전 배치 파일 내의 구버전 미존재 스크립트 경로(`clean_and_organize_datasets.py`)를 정정하고, **루트 `seed_db.py`를 정식 가동**하도록 100% 수리 집행 완료했습니다:

```bat
:: [3/4] 최초 콜드스타트 데이터 세트 적재 및 공간 조인 실행
cd backend
python ../seed_db.py
python app/scripts/train_css_model.py
```

- **공무원/일반 실무자 실행 방법**:
  - `start_omnisite_local.bat` 파일 더블클릭 ➔ Docker 검증 ➔ Python/Node 의존성 셋업 ➔ `seed_db.py` 시딩 ➔ `train_css_model.py` 훈련 ➔ 백엔드/프론트엔드 동시 기동 및 **웹 브라우저 자동 연결**.

---

## 🔒 4. 콜드스타트 무결성 동결 수칙 (Freeze Rules)

1. **`seed_db.py` 및 `Datasets/` 6개 폴더 구조 완전 동결**:
   - 데이터 구조 멸실을 방지하기 위해 루트 `seed_db.py` 및 `Datasets/` 6개 디렉터리는 **조장(USER)의 명시적 사전 승인 없이 수정을 엄격히 금지**합니다.
2. **Leaflet GIS 싱글톤 및 마커 드래그 락 동결**:
   - `spatial/page.js` 내 Leaflet 비동기 싱글톤, Ref 캐시 해제 `.enable()`, 마커 드래그 스로틀링 및 롤백 로직은 **완전 동결 유지**합니다.

---

## 🧪 5. 배포 전 최종 검증 체계 (Pre-flight Audit)

1. **자동 E2E 파이프라인 풀 수트 검증**:
   ```bash
   cd backend
   python app/scripts/test_e2e_full_pipeline.py
   ```
2. **프론트엔드 static 컴파일 검증**:
   ```bash
   cd frontend
   npm run build
   ```
3. **백엔드 py_compile 구문 검증**:
   ```bash
   cd backend
   python -m py_compile app/routers/spatial.py
   ```
