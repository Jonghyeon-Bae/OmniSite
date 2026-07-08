# v3.9.2 Execution Task List

- `[x]` 1. [Backend] `backend/app/routers/spatial.py` - `DebateRequest` DTO에 `intensity_level` 추가 및 선택된 갈등 강도별 3종 LLM System Prompt 분기 조건 추가
- `[x]` 2. [Backend] `backend/app/routers/spatial.py` - 토론 종료 시 로컬 파일 시스템 `data/debates/debate_{pnu}_{intensity}.json` 격리 적재 로직 구현 (OpenAI & Mock 공통)
- `[x]` 3. [Backend] `backend/app/routers/spatial.py` - `mock_event_generator`에 갈등 강도별 3단계(보통, 위험, 매우 위험) 전용 장문 실측 지표 연계 모킹 대본 설계 및 Yield 버퍼 튜닝
- `[x]` 4. [Frontend] `frontend/src/app/page.js` - `pipelineStep >= 4` 영역에 금지구역(규제 버퍼) 옅은 빨간색 서클 오버레이 가시화 추가
- `[x]` 5. [Frontend] `frontend/src/app/page.js` - 모의 토론 모달 상단에 갈등 강도 3단계 선택 UI 적용 및 payload 전달 연동
- `[x]` 6. [Verification] E2E API 테스트 수행 및 Next.js 프로덕션 빌드 체크
- `[x]` 7. [Backend] `upload.py` 및 `spatial.py` 내 pgvector 코사인 유사도 연산자 `<=>` 파라미터 `::vector` 명시적 타입 캐스팅 적용 (Type Mismatch 500 크래시 해결)
- `[x]` 8. [Frontend] `page.js` 모듈 레벨에 relative `/api/v1` 요청을 `http://localhost:8000` 직접 라우팅하는 Custom Fetch 래퍼 주입 (Next.js proxy socket hang up / ECONNRESET 해결)
- `[x]` 9. [Frontend] Custom Fetch 식별자명을 `fetch`에서 `apiFetch`로 변경 및 전체 개별 비동기 호출 치환 (SWC 컴파일러 폴리필 섀도잉 무한 루프 락인 해결 - v3.9.1)
- `[x]` 10. [Backend] `spatial.py` 공간 입지 추천 query 내 배제 필터 대상을 빈 `childcare_centers` 테이블에서 실물 데이터가 적재된 `restricted_zones` 테이블로 정정 (금지구역 내부 추천 결함 해결 - v3.9.2)
- `[x]` 11. [Backend] `spatial.py` 내 후보군 스캔 LIMIT를 15개에서 150개로 대폭 확장하여 AHP 주변 환경 요소 가산 반영 정합성 고도화 (v3.9.2)
