# 📋 Task List: 법규 RAG 독립 모달 분리 및 다중 업로드(Multi-Upload) 지원

- [x] **1단계: Next.js 프론트엔드 UI/UX 수정 (`page.js`)**
  - [x] React 상태값에 `showRagModal` 및 `ragUploadSuccess` 추가
  - [x] 글로벌 헤더 우측 소속 정보 영역 옆에 **"⚖️ 법규 RAG 관리"** 단추 추가 및 모달 트리거 바인딩
  - [x] 메인 좌측 플로팅 패널(Left Panel)에서 조례 PDF 업로드 섹션 완전히 제거
  - [x] 팝업 모달 다이얼로그 `⚖️ 법규 RAG 데이터베이스 관리` 마크업 및 스타일링 신설
  - [x] 조례 업로드 함수 `handleRegulationFileChange`를 세션 보존이 아닌 단발성 "캐싱 성공 피드백"으로 교정
  - [x] 조례 및 공간 CSV 업로더를 모두 다중 파일 선택(`multiple`) 및 다중 파일 서버 전송(FormData `files` 루프) 구조로 전면 확장
- [x] **2단계: E2E 통합 테스트 및 이관**
  - [x] 브라우저 상에서 RAG 모달을 통한 PDF 등록 및 메인 CSV 감리 연동 수동 검증
  - [x] `task.md` 및 `walkthrough.md` 최신 상태 동기화 및 1.0-prototype/docs/ 폴더로 복사 이관
