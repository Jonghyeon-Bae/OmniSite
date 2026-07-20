# 로컬 핫리로드 개발 환경 및 상용 배포 환경 복합 이중화 구축 계획서 (v1.2.0-alpha-Rev99)

본 계획은 조장(USER)의 지시에 따라, 로컬 테스트/개발 환경(Development Environment)과 실제 클라우드 배포 환경(Production Environment)을 포트 충돌이나 환경 파일 꼬임 없이 상호 독립적 및 병행 구동할 수 있도록 이중 컨테이너 구성을 수립하기 위함입니다.

## User Review Required

> [!IMPORTANT]
> - **로컬 개발 전용 `docker-compose.yml` 완공**:
>   - 로컬 소스 변경 시 실시간 반영되도록 볼륨 마운트(`bind-mount`) 처리.
>   - 백엔드는 `--reload`를 켜고, 프론트엔드는 `npm run dev`로 개발 핫 리로더 기동.
> - **상용 배포 전용 `docker-compose.production.yml` 분리**:
>   - 소스코드가 내장된 정적 컨테이너 이미지 빌드.
>   - 백엔드는 `gunicorn` 다중 프로덕션 모드 가동, 프론트엔드는 Next.js 프로덕션 컴파일 상태로 기동하여 고가용성 보장.

## Proposed Changes

### Docker Orchestration Components

#### [MODIFY] [docker-compose.yml (Local Development)](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/최종1차/1.0-prototype/docker-compose.yml)
- 기존 db 단독 명세에서 백엔드(FastAPI Uvicorn Reload), 프론트엔드(Next.js dev hot-reload) 3개 통합 기동으로 개조.
- 로컬 변경 내역 실시간 바인딩 볼륨 마운트 지정.

#### [MODIFY] [docker-compose.production.yml (Cloud Production)](file:///c:/Users/Admin/Desktop/빅프로젝트/관련자료/최종1차/1.0-prototype/docker-compose.production.yml)
- 소스 마운트 없이 정적으로 컨테이너 빌드 완료 후 Gunicorn & Next.js production 가동.

## Verification Plan

### Automated Tests
- Next.js 개발 서버 빌드 정합성을 크로스 검증합니다.

### Manual Verification
- 로컬 docker-compose 기동 시 코드 변경 사항이 브라우저에 즉각 핫 리로딩 갱신 반영되는지 실측 검사합니다.
