# AWS 배포 타당성 및 런타임 위험 정밀 감리서 (v1.2.0-alpha-DeploymentAudit)

본 감리서는 조장(USER)의 무편향·냉철 감리 지침에 따라, **OmniSite v1.2.0** 프로토타입의 실 AWS 클라우드 배포 적합성과 런타임 환경 기동 시 폭사(Crash)할 수 있는 기술적 위험 요인을 엄격하게 파악·기술한 품질 보증 보고서입니다.

---

## ⚖️ 1. 배포 타당성 종합 판정 (Production Readiness Verdict)

> 🟢 **종합 판정: 배포 가증 (Deployment PASS - 조건부 배포 가능)**
> - **인프라 패키징 무결성**: 이전 감리를 통해 누락되었던 실물 빌드 명세서(`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.production.yml`)가 완공되었고, `requirements.txt`에 상용 서버 기동용 `gunicorn` 의존성이 보강되었습니다.
> - **컴파일 정적 빌드**: Next.js 16.2.10 버전에 대한 프로덕션 정적 빌드(`npm run build`) 결과 오류 0건으로 컴파일 타당성이 검증되었습니다.
> - **데이터 무결성**: 101~104번의 과거 더미데이터 시드가 DB 마이그레이션 도구에서 삭제되어 대시보드가 0건 상태로 깨끗하게 대기 중입니다.
> - **결론**: 인프라 배포의 기술적 준비는 끝났으나, 아래의 **4대 런타임 위험 요인**이 배포 과정에서 제어되지 않으면 가동 즉시 먹통(White-out)이 되므로 조건부 패스로 판정합니다.

---

## 🚨 2. 배포 가동 즉시 폭사할 수 있는 4대 위험 요인 (Runtime Risks)

### ① 위험 1: CORS 정책 및 Next.js API URL 미스매치 리스크
- **원인**: `docker-compose.production.yml` 내 `frontend` 서비스 환경변수로 `NEXT_PUBLIC_API_URL=http://localhost:8000` 이 기재되어 있습니다.
- **폭사 시나리오**: 클라이언트 브라우저가 클라우드 IP 또는 외부 도메인(예: `http://3.35.x.x`)을 타고 웹에 진입했을 때, 브라우저는 백엔드 API 서버(`http://localhost:8000`)에 직접 통신을 요청하게 됩니다. 이때 클라이언트 로컬 컴퓨터의 8000번 포트는 닫혀있으므로 **모든 API 페치(로그인, 입지분석 등)가 즉각 실패하며 화면이 멈춥니다(CORS Mismatch 및 Connection Refused).**
- **대응책**: AWS Lightsail 기동 시 할당받은 공인 고정 IP(Elastic IP) 또는 도메인을 `NEXT_PUBLIC_API_URL` 값에 확실히 인가하여 빌드해야 합니다.

### ② 위험 2: OpenAI API Key 미인가로 인한 RAG 감리 모듈 마비 리스크
- **원인**: 대시보드의 준공/고시 PDF 공문서 RAG OCR 교차 검증 및 AHP 규제 조례 분석은 `OPENAI_API_KEY`를 필수로 사용합니다.
- **폭사 시나리오**: 도커 컨테이너 기동 시 환경변수(`.env` 또는 Compose Env)에 OpenAI API Key가 유실되거나 올바르지 않으면, PDF 업로드 즉시 백엔드에서 **500 Internal Server Error (Unauthorized / Key Missing)**를 뱉으며 RAG 감리 기능이 마비됩니다.
- **대응책**: 배포 전 호스트 서버의 `.env` 파일에 유효한 OpenAI API Key 바인딩을 강제해야 합니다.

### ③ 위험 3: 초경량 인스턴스(AWS Lightsail 2GB RAM) OOM(Out of Memory) 셧다운 리스크
- **원인**: Next.js 프로덕션 빌드(`npm run build`)는 Webpack/Turbopack 컴파일 과정에서 일시적으로 약 1.5GB 이상의 메모리를 점유합니다.
- **폭사 시나리오**: Swap 공간이 설정되지 않은 2GB RAM 단일 VPS 인스턴스에서 도커 이미지를 다이렉트로 빌드하면, **OOM Killer가 작동하여 Docker 빌드 데몬 또는 PostgreSQL 컨테이너를 강제 강등 셧다운**시켜 인스턴스 자체가 다운됩니다.
- **대응책**: 빌드 기동 전 반드시 **최소 4GB 이상의 SSD 가상 Swap 메모리를 할당**하는 스크립트를 최우선 실행해야 합니다.

### ④ 위험 4: DB 패스워드 평문 하드코딩 및 외부 포트 무단 노출 리스크
- **원인**: docker-compose 상에 DB 패스워드가 평문으로 노출되거나 5432 포트가 전체 개방될 경우 보안 스캔 도구에 의해 무단 침투의 표적이 됩니다.
- **대응책**: `docker-compose.production.yml` 내부에서 `database` 포트를 `127.0.0.1:5432:5432`로 격리 바인딩하여 백엔드 컨테이너만 네트워크 인터페이스로 DB에 접근할 수 있도록 차단 장치를 유지해야 합니다.
