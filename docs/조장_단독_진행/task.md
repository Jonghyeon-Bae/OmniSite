# 📋 Task List: 조례 목록 조회, 중복 검증 및 삭제 기능 구현

- [x] **1단계: 백엔드 API 보완 (`backend/app/routers/upload.py`)**
  - [x] 조례 PDF 업로드 (`POST /upload/regulation`) 시 동일한 파일명이 존재할 경우 중복 예외(400) 반환
  - [x] 조례 물리 파일 및 텍스트 캐시 동시 수거 API (`DELETE /upload/regulations/{filename}`) 신규 작성
- [x] **2단계: 프론트엔드 UI/UX 개발 (`frontend/src/app/page.js`)**
  - [x] React 상태값에 `showRegulationListModal` 및 `regulationList` 추가
  - [x] 조례 목록 조회 비동기 fetch 함수 (`fetchRegulations`) 및 삭제 핸들러 (`handleDeleteRegulation`) 구현
  - [x] 조례 업로드 성공 시 `fetchRegulations()` 연동 갱신 추가
  - [x] 글로벌 헤더에 **"📋 조례 목록 조회"** 단추 추가 및 모달 트리거 바인딩
  - [x] `📋 등록된 조례 목록` 독립 모달 컴포넌트 마크업 설계 (스크롤 및 휴지통 삭제 단추 포함)
- [x] **3단계: 통합 검증 및 문서 이관**
  - [x] 백엔드 및 프론트엔드 프로세스 가동
  - [x] `scratch/e2e_test.py`에 조례 중복 및 삭제 검증 코드 추가 후 통합 테스트 실행
  - [x] `task.md` 및 `walkthrough.md` 상태 업데이트 동기화 및 1.0-prototype/docs/ 폴더로 최종 이관 복사
