# [v1.1-stable] 구현 체크리스트

- [x] 1. 기본 어드민 계정 시딩 자동화 (`seed_db.py` 수정)
- [x] 2. 백엔드 계정 관리 API 이식 (`backend/app/routers/auth.py` 수정)
  - [x] 2.1. 로그인 시 `require_password_change` 플래그 반환 로직 추가
  - [x] 2.2. 사용자 비밀번호 자가 변경 API 구현 (`POST /change-password`)
  - [x] 2.3. 사용자 목록 조회 API 구현 (`GET /users`)
  - [x] 2.4. 사용자 삭제 API 구현 (`DELETE /users/{user_id}`)
  - [x] 2.5. 사용자 비밀번호 강제 초기화 API 구현 (`POST /users/{user_id}/reset-password`)
- [x] 3. Shapefile 벌크 Ingestion API 구축 (`backend/app/routers/upload.py` 수정)
  - [x] 3.1. `.shp`, `.dbf`, `.shx` 파일 수집 및 `pyshp` 파싱 로직 구현
  - [x] 3.2. Auto-SRID 판독 및 PostGIS `ST_Transform` 공간 변환 이관 적재 구현
- [x] 4. 모의 심의 토론 3자 페르소나 양식 핫픽스 (`backend/app/routers/spatial.py` 및 프론트엔드 수정)
  - [x] 4.1. SSE 토론 시작 시 메타 헤더 전송 구현 (`spatial.py`)
  - [x] 4.2. 화자 분류 정규식 매핑 보정 (`spatial.py`)
  - [x] 4.3. 토론 모달 말풍선 색상 뒤바뀜 핫픽스 (`DebateSimulatorModal.jsx`)
- [x] 5. 프론트엔드 최초 로그인 패스워드 변경 의무화 UI 구현 (`frontend/src/app/page.js` 수정)
- [x] 6. 프론트엔드 관리자 콘솔 탭 UI 및 계정 CRUD 연동 (`frontend/src/app/spatial/page.js` 수정)
- [x] 7. 최종 빌드 및 공간 적재/계정 생명주기 기능 동작 검증
