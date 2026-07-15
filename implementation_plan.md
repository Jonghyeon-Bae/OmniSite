# [v1.1-stable] 코드 정리 및 상용화 수준 종합 문서(Spec/Journal/Deployment) 구축 계획서

본 계획서는 **OmniSite v1.1-stable** 격상 승인 이후, 프로토타입의 기술적 무결성을 검증하고 상용 서버 이식 준비를 위한 1) 백엔드/프론트엔드 리팩토링 및 2) 백과사전식 종합 문서 편찬(연구노트/스펙서/배포계획서)의 실행 전략을 수립합니다.

## User Review Required

> [!IMPORTANT]
> 본 태스크는 실물 코드의 파괴적 수정을 배제하고, 혼재된 중복 구문 정리와 시스템의 구조적 안전성을 확보하는 데 중점을 둡니다.
> 생성할 3대 문서([final_project_spec.md](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/final_project_spec.md), [development_journal.md](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/development_journal.md), [deployment_plan.md](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/deployment_plan.md))는 공무원 및 면접관이 시스템 전체를 뜯어볼 수 있을 정도로 세부적인 수식(AHP, XGBoost, Cosine Similarity)과 아키텍처 다이어그램을 다수 내포할 예정입니다.

## Proposed Changes

---

### 1. 코드 정리 및 최적화 (Code Infiltration & Refactoring)

#### [MODIFY] [spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py)
*   하단부 `/spatial/history` API 이식 시 중복 정의된 일부 임포트(`import io`, `from pypdf import PdfReader` 등)와 클래스 선언들의 중복 유무를 검사하여 파일 최상단 또는 적합한 계층으로 리팩토링 정렬합니다.
*   *주의:* Leaflet GIS 및 마커 드래그 최적화 캐시 로직(동결 규칙)은 100% 보존합니다.

#### [MODIFY] [DebateSimulatorModal.jsx](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/components/DebateSimulatorModal.jsx)
*   정규식 패턴 바인딩의 예외 처리(Fallback) 구문을 확실하게 정비하여 주소명 누락 시에도 서버 적재가 정상 수행됨을 보증합니다.

---

### 2. 상용화 대비 3대 핵심 문서 신설 및 바탕화면 편찬

#### [NEW] [final_project_spec.md](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/final_project_spec.md)
*   **목적:** 상용화 수준의 시스템 아키텍처 및 알고리즘 적합성 상세 스펙 문서.
*   **주요 포함 목차:**
    1. **시스템 개요:** B2G 스마트 입지 의사결정 지원 시스템(SDSS) 정의 및 비즈니스 타겟.
    2. **하이브리드 AI 아키텍처:** XGBoost 피처 중요도의 AHP 슬라이더 가중치 선전(Calibration) 역학 및 매핑 수식.
    3. **공간 분석 알고리즘:** PostGIS 및 PostgreSQL 구면 기하 계산 메트릭(`ST_DWithin` 등) 및 하버사인 필터링의 수치 정합성.
    4. **AI 시맨틱 감리 및 pgvector RAG:** 준공 문서 OCR 텍스트 대조, RAG 유사도 검색 메트릭(Cosine Similarity `1 - (embedding <=> query)`) 설명.
    5. **최초 계획서 대비 완성도 검증:** 프로토타입 범위 합치성 및 미진 사항의 방어 논리.

#### [NEW] [development_journal.md](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/development_journal.md)
*   **목적:** 개발 착수 시점부터 v1.1-stable에 도달하기까지의 핵심 마일스톤과 문제 해결 이력을 기록한 일일 개발 저널(연구노트).
*   **주요 포함 목차:**
    1. **Phase 1 (초기 모델링):** 순정 XGBoost 예측 모델의 한계 및 AHP 융합 계기.
    2. **Phase 2 (공간 연산 오차 극복):** 3번 마커 규제 원 내부 침범 문제, 위경도 좌표축 교란(338건 스왑 데이터 오류) 디버깅 기록.
    3. **Phase 3 (DB 영구 이관):** 인메모리 휘발성 해결을 위한 `decision_histories` 및 `verified_precedents` 영구 아카이빙 구축 이력.
    4. **Phase 4 (Zero-Hardcoding):** OCP 원칙 위반 경고 수렴 후 정규식 추출 및 dynamic 목적 바인딩 고도화 이력.

#### [NEW] [deployment_plan.md](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/deployment_plan.md)
*   **목적:** AWS Lightsail 및 Docker-Compose 기반 클라우드 이관/배포 블루프린트.
*   **주요 포함 목차:**
    1. **AWS 가상 인스턴스 명세:** Lightsail $5 or $10 단일 노드 스펙 및 우분투 환경.
    2. **가상 메모리(Swap 4GB) 설정 가이드:** 물리 메모리 부족으로 인한 OOM 컨테이너 킬 예방 세부 명령어.
    3. **Docker Compose Production 환경설정:** `.env.production` 환경변수 설계 및 Nginx Reverse Proxy 설정 양식.
    4. **데이터베이스 초기 시딩(Seeding):** `11. 국유부동산정보.csv` 및 법규 데이터셋 클라우드 DB 고속 Ingestion 전략.

---

## Verification Plan

### Automated Tests
*   `npm run build`를 통한 프론트엔드 정적 번들 컴파일 무오류 검증.
*   FastAPI의 `main.py` 기동 및 REST API 스웨거 스펙 대조.

### Manual Verification
*   사용자 작업 공간(`1.0-prototype`) 폴더 내 생성된 3대 `.md` 문서 파일의 출력 인코딩(UTF-8) 정합성 확인.
