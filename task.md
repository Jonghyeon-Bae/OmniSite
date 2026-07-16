# [v1.2-alpha-Enhancement] 구현 작업 목록

- [x] 1. 백엔드 멀티에이전트(Multi-agent) 토론 스트리밍 파이프라인 구현 (`backend/app/routers/spatial.py`)
  - [x] 1.1. 찬성측, 반대측, 정부측 3대 독립 에이전트 시스템 프롬프트 세분화
  - [x] 1.2. `chat_history`를 컨텍스트로 전달하는 8턴 연쇄 스트리밍 루프 개발
  - [x] 1.3. Mock Fallback 역시 턴 단위 지연 스트리밍 방식으로 멀티에이전트처럼 작동하도록 통일
- [x] 2. 프론트엔드 UI/UX 개조 및 이쁜 커스텀 토스트 알림 적용 (`frontend/src/app/spatial/page.js`)
  - [x] 2.1. `toast` 상태 및 `showToast(msg, type)` 커스텀 디자인 팝업 컴포넌트 추가
  - [x] 2.2. 모달 내 `alert()` 호출부들을 전량 커스텀 토스트로 교체
  - [x] 2.3. 통합 관리자 콘솔 모달 크기 확장 (`max-w-lg` ➔ `max-w-4xl`)
  - [x] 2.4. 데이터 벌크 탭 내 `🚀 원천 데이터 벌크 적재` 우측에 호버 툴팁 가이드 인포 단추 신설
- [x] 3. 전체 시스템 연동 빌드 테스트 및 마스터 연구노트 `Rev 64` 갱신
  - [x] 3.1. Next.js Turbopack 빌드 및 FastAPI Uvicorn 구동 성공 여부 테스트
  - [x] 3.2. 연구노트 내 `Rev 64` 기록 추가 및 자치구청장 동적 PDF 연동 최종 점검
