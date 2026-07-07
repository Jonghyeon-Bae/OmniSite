# 📋 Task List: AHP 동적 검정 및 PostGIS 차집합 입지 연산 구현 (v3.0.0)

- [x] **1단계: 백엔드 AHP & 공간 추천 API 개발 (`backend/app/routers/`)**
  - [x] 신규 라우터 `ahp.py` 작성: 실수형 가중치 수신, $n$차 R.I. 동적 매핑, Numpy 최대 고유값 기반 C.R. 실수 연산 및 `ahp_models` 락(Lock) 저장 구현
  - [x] 신규 라우터 `spatial.py` 작성: 지하철(10m)/학교(200m) 버퍼 합집합 마스크 생성, `cadastral_lands` 국공유지 공간 차집합(`ST_Difference`) 연산, 동적 AHP 지표별 공간 속성 집계 및 Min-Max 가중합 순위 추천 (Top 1~3) 연산 구현
  - [x] `backend/app/main.py`에 신규 라우터 추가 등록
- [x] **2단계: 프론트엔드 UI/UX 개편 및 연동 (`frontend/src/app/page.js`)**
  - [x] `criteriaList` 및 실수 step(`0.1`) 슬라이더 동적 생성 마크업 적용
  - [x] AHP 잠금 클릭 시 백엔드 `POST /ahp/lock` 호출 연동
  - [x] 잠금 성공 후 `GET /spatial/recommend` 트리거 및 `selectedParcel` 바인딩을 통한 지도 마커/우측 속성창 실시간 리렌더링
- [x] **3단계: 통합 검증 및 문서 이관**
  - [x] 백엔드 및 프론트엔드 프로세스 구동
  - [x] `scratch/ahp_spatial_test.py` 작성 및 Numpy/PostGIS 벤치마크 테스트
  - [x] `task.md` 및 `walkthrough.md` 최신 상태 동기화 및 1.0-prototype/docs/ 폴더로 최종 이관 복사
