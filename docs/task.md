# v3.8.0 Execution Task List

- `[x]` 1. [Backend] `backend/app/routers/spatial.py` - `DebateRequest` DTO에 `intensity_level` 추가 및 선택된 갈등 강도별 3종 LLM System Prompt 분기 조건 추가
- `[x]` 2. [Backend] `backend/app/routers/spatial.py` - 토론 종료 시 로컬 파일 시스템 `data/debates/debate_{pnu}_{intensity}.json` 격리 적재 로직 구현 (OpenAI & Mock 공통)
- `[x]` 3. [Backend] `backend/app/routers/spatial.py` - `mock_event_generator`에 갈등 강도별 3단계(보통, 위험, 매우 위험) 전용 장문 실측 지표 연계 모킹 대본 설계 및 Yield 버퍼 튜닝
- `[x]` 4. [Frontend] `frontend/src/app/page.js` - `pipelineStep >= 4` 영역에 금지구역(규제 버퍼) 옅은 빨간색 서클 오버레이 가시화 추가
- `[x]` 5. [Frontend] `frontend/src/app/page.js` - 모의 토론 모달 상단에 갈등 강도 3단계 선택 UI 적용 및 payload 전달 연동
- `[x]` 6. [Verification] E2E API 테스트 수행 및 Next.js 프로덕션 빌드 체크
