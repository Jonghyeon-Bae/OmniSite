# [v1.1-stable] 관리자 콘솔 고도화, 어드민 계정 관리 및 ML 모델 자동 재학습 수립 계획서

본 계획서는 **OmniSite v1.1-stable**의 무결성을 최종 확보하기 위해, 관리자 콘솔(Admin Console)의 원천 데이터 적재 범위를 ESRI Shapefile로 확장하고, 공무원 사용자 계정의 생명주기 관리(CRUD) 체계를 완전 조립하며, **행정 데이터 연동형 ML 모델 자동 재학습(Retraining) 및 동적 피처 생성 파이프라인**을 수립하기 위한 추가 개발 설계서입니다.

## User Review Required

> [!IMPORTANT]
> 1. **버전 관리 시작:** 마스터 연구노트의 공식 버전을 `v1.1-stable` 체계로 승격하고, 현 리비전부터 역사 기록을 상시 가동합니다.
> 2. **모의 심의 토론 페르소나 양식 무결화:** SSE 토론 스트리밍 시작부에서 찬성측/반대측/정부측 메타 헤더를 전송하여 프론트엔드 파서 및 대화 풍선 렌더링 색상이 뒤바뀌거나 깨지는 버그를 원천 진압합니다.
> 3. **어드민 로그인 및 비밀번호 자가 리셋:** 콜드 부팅 시 기본 어드민 계정(`admin` / `admin1234`)이 DB에 자동 인서트되도록 초기 시드 스크립트를 개조하고, 로그인 상태에서 비밀번호를 즉시 변경할 수 있는 신규 API를 장착합니다.
> 4. **관리자 최초 로그인 시 패스워드 변경 강제 유도:** 기본 패스워드(`admin1234`) 상태인 관리자 계정 로그인 시 백엔드에서 `require_password_change: true` 플래그를 반환하고, 프론트엔드 로그인 페이지에서 다른 모든 화면 진입을 전면 차단한 채 비밀번호 강제 교체 모달을 우선 실행시킵니다.
> 5. **공간지리 Shapefile (shp, dbf, shx) Ingestion 파이프라인 개발 및 데이터 교체(Replace/Append) 정책 구현:** 지적도 공간정보를 신규 읍면동 단위로 셋업할 때 백엔드로 SHP 셋을 업로드하면, PostGIS 상에서 좌표계를 스스로 판독(Auto-SRID)하여 위경도 MultiPolygon으로 자동 변환 이관 적재하는 경량 GIS Ingestion 엔진을 구축합니다. 특히 데이터 갱신 시 중복 적재를 막고 안전한 교체를 보장하기 위해, 업로드 시 **"덮어쓰기 (Replace - 기존 테이블 비우고 새로 올리기)"** 및 **"추가 적재 (Append - 중복 지번/PNU 필터링 후 덧붙이기)"**의 Ingestion 정책 옵션을 어드민 콘솔에 제공하고 백엔드 트랜잭션에서 기존 데이터를 자동으로 날리거나 중복 충돌을 방어 처리하도록 구현합니다.
> 6. **동적 ML 모델 재학습 및 피처 추출 자동화:** 공간 데이터 및 행정구역 변동 발생 시 최신 DB 상태(`cadastral_lands`, `restricted_zones`)로부터 피처를 실시간 조인 및 공간 계산(`ST_Distance`)하여 최신 훈련 데이터셋을 동적 합성하고, Uvicorn 서버 락을 차단하는 비동기(`BackgroundTasks`) XGBoost 재학습 API 및 관리자 콘솔 탭 UI를 전격 도입합니다.

---

## Proposed Changes

### 1. 백엔드(FastAPI) 계정 관리, 데이터 적재 및 ML 재학습 엔진

#### [MODIFY] [auth.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/auth.py)
*   **로그인 응답 스키마 확장:**
    *   `/login` 엔드포인트에서 로그인 대상이 `admin` 이고, 해시 검증 결과 디폴트 패스워드(`admin1234`)가 여전히 가용 상태라면 응답 페이로드에 `require_password_change: true` 상태 플래그를 실어서 반환하도록 로직을 변경합니다.
*   **비밀번호 자가 변경 API 추가 (`POST /api/v1/auth/change-password`):**
    *   현재 로그인된 사용자(`get_current_user`)가 기존 비밀번호 검증을 거쳐 안전하게 패스워드를 갱신할 수 있는 트랜잭션을 구현합니다.
*   **사용자 디렉토리 관리 API 추가:**
    *   `GET /api/v1/auth/users`: 등록된 모든 실무관 계정 목록 조회 (어드민 전용 가드).
    *   `DELETE /api/v1/auth/users/{user_id}`: 특정 실무관 계정 강제 삭제 (어드민 전용 가드).
    *   `POST /api/v1/auth/users/{user_id}/reset-password`: 특정 사용자 비밀번호 관리자 강제 재설정 (어드민 전용 가드).

#### [MODIFY] [seed_db.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/seed_db.py)
*   데이터베이스 시딩 완료 시점에 `users` 테이블을 검사하고, 기본 관리자 계정(`admin`/`admin1234`)이 존재하지 않을 시 bcrypt 해싱을 가동해 자동 주입 적재하는 방어 모듈을 주입합니다.

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)
*   **Shapefile 마스터 벌크 적재 API 추가 및 Ingestion 모드 구현 (`POST /api/v1/upload/seed-shapefile`):**
    *   관리자 콘솔에서 업로드한 `.shp`, `.dbf`, `.shx` 파일 셋을 병렬 수집하고, `pyshp`를 기동하여 공간 지오메트리를 추출합니다.
    *   **Auto-SRID 감지 알고리즘:** X 좌표 범위가 120~132 이면 EPSG:4326, 15만~25만 이면 EPSG:5186 (중부원점), 80만~110만 이면 EPSG:5179 (UTM-K)로 감지하여 PostGIS `ST_Transform` 쿼리를 통해 `city_spatial_features` 혹은 `cadastral_lands` 테이블에 다각형 geom을 정합 이관 적재합니다.
    *   **데이터 갱신/덮어쓰기 모드 도입:** 업로드 시 `mode` 파라미터(`"replace"` or `"append"`)를 추가로 받아, `"replace"` 일 경우 데이터를 삽입하기 전 해당 `target_table`을 비우는(`DELETE FROM` or `TRUNCATE`) 트랜잭션을 선행 구동합니다. `"append"` 일 경우엔 기존 데이터를 보존한 채 신규 데이터만 추가로 인서트합니다. (중복 검사를 위해 `cadastral_lands` 의 경우 `pnu` 중복 레코드는 스킵하는 로직을 반영합니다)

#### [NEW] [model.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/model.py)
*   **모델 재학습 및 피처 추출 API 구현 (`POST /api/v1/model/retrain`):**
    *   관리자가 콘솔에서 훈련 대상 도메인(예: `smoking_zone`)을 선택하여 학습을 요청하면 `BackgroundTasks`로 비동기 훈련 파이프라인을 기동합니다.
    *   **휘발성 임시 캐시 격리 및 검증 데이터셋(Verified Precedents) 연동:** 
        *   사용자가 수시로 업로드하는 Step 1 임시 데이터셋은 DB 오염을 방지하기 위해 ML 모델 훈련 대상에서 **철저히 배제(Exclusion)**합니다.
        *   대신, `Audit AI`가 최종 공문서 PDF 검증을 완료하여 공식 승인한 실재 행정 데이터셋인 **`verified_precedents` 테이블의 데이터만을 ML 학습의 정답 레이블(Target Label) 소스로 활용**합니다.
        *   **콜드 스타트 방어 가드 (Cold-Start Fallback):** 만약 새로운 지자체 환경에 최초 구동되어 `verified_precedents` 의 실측 데이터가 없거나 훈련 최소 조건(예: 30건 미만)에 부합하지 못하는 콜드 상태일 경우, 시스템 크래시를 방지하기 위해 패키지 내에 기본 동봉된 **`backend/data/processed/css_train_dataset.csv` 일반화 지리 통계 데이터셋을 파일 시스템에서 강제 로드하여 대체 학습(Fallback Train)**하도록 구현합니다.
    *   `verified_precedents` 내의 입지 중심 좌표(`geom`)와 `restricted_zones`(공인 규제 보호시설)과의 실제 지리적 이격 거리를 PostGIS `ST_Distance` 로 직접 쿼리하여 `dist_to_school`, `dist_to_childcare` 피처 값을 런타임에 동적 산출합니다.
    *   학습용으로 변환된 피처 매트릭스를 XGBoost Classifier 파이프라인 모델에 피팅시킨 뒤, 생성된 바이너리를 `backend/app/models/registry` 하위에 저장하고 인메모리 싱글톤 모델 레지스트리를 즉시 핫 리로드(Hot-reload)합니다.
*   **모델 성능 상태 조회 API 구현 (`GET /api/v1/model/status`):**
    *   현재 싱글톤 레지스트리에 메모리 로드되어 가용 중인 XGBoost 모델의 학습 통계(정확도, F1-Score) 및 피처 기여도(Feature Importance) 배열을 조회합니다.

#### [MODIFY] [spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py)
*   **SSE 메타 헤더 송출:** `stream_debate_sim` 내에서 OpenAI 스트림이 최초 가동되는 즉시 `data: {"meta": true, "personas": ["찬성측", "반대측", "정부측"]}` JSON 청크를 발행하도록 조치합니다.
*   **화자 분류 정규식 매핑 보정:** `save_debate_log_to_file` 의 화자 분리 시, `'찬성측'`, `'반대측'`, `'정부측'` 문자열과 동적 페르소나 매핑 명칭이 콜론 뒤에서 파열되지 않도록 정규식 스캔 구조를 고도화합니다.

---

### 2. 프론트엔드(Next.js) 관리자 콘솔 3대 탭 확장 및 UX 바인딩

#### [MODIFY] [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/page.js)
*   **최초 로그인 패스워드 강제 리셋 UI 추가:**
    *   로그인 API 호출 후 `require_password_change: true` 플래그 수신 시, 기존의 대시보드 강제 리다이렉션을 차단하고, 화면 전체에 **"최초 로그인 보안 비밀번호 변경 안내"** 모달을 띄워 패스워드 교체 전에는 메인 시스템에 진입할 수 없도록 강제 유도 프로세스를 구축합니다.

#### [MODIFY] [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/spatial/page.js)
*   **관리자 콘솔 UI 구조 변경:**
    *   통합 관리자 콘솔 모달 내부를 **"📊 데이터 벌크 적재"**, **"👥 실무자 계정 관리"**, **"🤖 ML 모델 재학습"**의 3개 탭 레이아웃으로 확장 개편합니다.
    *   **데이터 벌크 적재 탭:**
        *   CSV/Shapefile 업로드 제어판 상단에 **"적재 옵션"** 라벨과 함께 **"기존 데이터 비우고 덮어쓰기 (Replace)"** 및 **"기존 데이터에 덧붙이기 (Append)"** 라디오 버튼 컴포넌트를 설계하여 백엔드 `/upload/seed-shapefile` 에 `mode` 쿼리 파라미터를 연동 전달합니다.
        *   데이터 종류 선택 셀렉트박스의 기계적 테이블 명칭(예: `cadastral_lands`)을 **"🗺️ 토지 지적도 및 필지 정보"**, **"🚫 법정 용도제한 보호구역"**, **"🛍️ 소상공인 상권 점포 분포"**, **"💬 주민 불편 민원 접수 대장"** 등 직관적인 한글 행정 명칭으로 교체합니다.
        *   선택된 테이블 항목에 따라 **"허용 포맷(.csv 또는 .shp 셋)"**과 **"데이터 맵핑 항목(지번, PNU, 좌표 등)"** 및 데이터의 정의를 친절하게 해설하는 **동적 행정 설명 가이드 박스**를 표출하여 실무자의 오작동을 차단합니다.
    *   **ML 모델 재학습 탭:**
        *   현재 활성화된 XGBoost 모델의 정확도, F1-Score와 피처 중요도 상위 항목 리스트(Bar 형태의 시각적 컴포넌트)를 렌더링하고, **"⚡ ML 모델 재학습 수행"** 버튼을 제공합니다.
        *   탭 내에 **"📖 ML 학습 데이터 구성 및 훈련 메커니즘 설명서"** 섹션을 상시 노출합니다. 여기에는 모델이 훈련에 사용하는 핵심 피처(`지목 코드`, `국공유지 유형`, `필지 면적`, `학교까지의 이격거리`, `어린이집 금역 이격거리`)가 실제 DB의 공간 데이터로부터 결합 추출되어 가해지는 방식과 XGBoost 학습의 목적을 개식체로 친절히 설명하여 공무원 실무진의 XAI(설명 가능한 AI) 활용성을 확보합니다.
        *   버튼 클릭 시 백엔드 재학습 API를 비동기 호출하고, 훈련 중 상태(로딩 인디케이터 및 펄스 애니메이션)를 화면에 표시하며 훈련 완료 시 즉시 갱신된 학습 결과를 시각 리렌더링합니다.

#### [MODIFY] [DebateSimulatorModal.jsx](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/components/DebateSimulatorModal.jsx)
*   **색상 뒤바뀜 핫픽스:**
    *   *찬성측* (상권 옹호 / 생존권 호소) ➔ `text-rose-400 font-medium` (상인측)
    *   *반대측* (정주권 침해 / 아이들 보행 안전) ➔ `text-emerald-400 font-medium` (주민측)
    *   *정부측* (RAG 법령 매핑 / 중재 조정안) ➔ `text-sky-400 font-medium`

---

## Verification Plan

### Automated Tests
*   `seed_db.py` 완료 후 DB 상 `users` 테이블 내 `admin` 계정 및 `hashed_password` 유무 확인 테스트.
*   Shapefile 업로드 후 변환된 PostGIS geom 레코드들의 유효성(`ST_IsValid`) 수동 쿼리 대조.
*   `/api/v1/model/retrain` API 비동기 구동 시 백그라운드 스레드 정상 실행 여부 및 학습 완료된 pkl 파일 교체 스냅샷 검증.

### Manual Verification
*   관리자 콘솔을 열어 계정 목록 탭 기동 시 등록된 실무관 목록이 정합성 있게 출력되는지, 신규 추가/삭제가 즉시 리렌더링되는지 브라우저에서 검증.
*   **ML 모델 재학습 탭**에서 재학습 기동 후, 정확도 통계 및 피처 중요도가 동적으로 새로고침 갱신되어 출력되는지 브라우저에서 검증.
*   실시간 모의 토론 모달 3자 대사에서 색상 대비 및 화자 꼬리표 파열이 없음(Strict regex 매핑 성공)을 육안 확인.
