# Git 불필요/임시 산출물 배제(Ignore) 및 정리 계획서 (v1.2.0-alpha-Rev100-Clean)

본 계획은 실제 구동 및 배포에 불필요하거나 개인정보/행정 기밀 노출 우려가 있는 임시 파일들(모의 토론 JSON 로그, RAG 감리 임시 PDF 및 텍스트 캐시, 일회성 테스트 스크립트 등)을 Git 형상관리 대상에서 전격 제외하여 저장소(Repository)의 무결점과 청정 상태를 확보하기 위함입니다.

## User Review Required

> [!IMPORTANT]
> - **Git 영구 제외 및 정리 대상 명세**:
>   - **임시 PDF 및 텍스트 캐시 (`*.pdf`, `*.pdf.txt`)**: PDF OCR 감리 시 로컬 디렉토리에 캐싱되는 원천 문서들로, 보안 및 개인정보 침해 소지가 있어 제외합니다.
>   - **임시 토론/RAG 캐시 JSON (`backend/data/raw/*.json`)**: 웹 구동 시 실시간 적재 및 휘발되는 캐시 데이터이므로 형상관리에서 영구 격리합니다.
>   - **ML 훈련 데이터 중간 산출물 (`backend/data/processed/css_train_dataset.csv`)**: 이미 완성된 ML 모델(`smoking_zone_v1.pkl`)이 레지스트리에 내장되어 있어 Git 업로드 불필요로 판정해 제외합니다.
>   - **일회성/테스트 스크립트 및 백업본 (`frontend.zip`, `create_pdf_raw.py` 등)**: 로컬 검증만을 위한 일회성 쓰레기 코드로, 배포 패키지 오염을 유발하므로 제외합니다.

## Proposed Changes

### Configuration Components

#### [MODIFY] [.gitignore](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/최종1차/1.0-prototype/.gitignore)
- L34 ~ L44 구역을 개조하여 상기 명세된 임시 캐시 및 텍스트 데이터의 영구 제외 규칙을 추가 보완합니다.

#### [NEW] [.dockerignore (backend)](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/최종1차/1.0-prototype/backend/.dockerignore)
- 도커 이미지 빌드 용량 최적화를 위해 가상환경(`venv`) 및 임시 PDF, `__pycache__` 등을 빌드 대상에서 전격 제외합니다.

#### [NEW] [.dockerignore (frontend)](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/최종1차/1.0-prototype/frontend/.dockerignore)
- `node_modules` 및 `.next` 컴파일 임시 디렉토리를 이미지 전송 대상에서 차단합니다.

## Verification Plan

### Automated Tests
- Next.js 프로덕션 컴파일 빌드를 재동작시켜 정적 무결성을 증명합니다.

### Manual Verification
- git status 검사 시 임시 PDF나 토론 캐시 파일들이 정상적으로 스킵되어 깨끗한 트래킹 상태가 유지되는지 확인합니다.
