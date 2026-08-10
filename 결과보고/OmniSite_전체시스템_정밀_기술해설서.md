# 🏛️ OmniSite SDSS 전체 시스템 정밀 청사진 및 기술해설서 (Technical Blueprint v1.0.0-Production Release)

> **"지자체 공간 빅데이터, PostGIS 공간 수학 연산, XGBoost 머신러닝, pgvector 1,536차원 RAG 조례 매핑, GPT-4o 3자 AI 모의 심의 토론, SHA-256 해시 체인 감사 원장 및 GitHub Actions CI/CD 무중단 배포를 아우르는 B2G 엔터프라이즈 스마트시티 공간의사결정지원시스템"**

---

## 📋 목차 (Table of Contents)
1. [시스템 아키텍처 및 하이브리드 데이터 흐름도](#1-시스템-아키텍처-및-하이브리드-데이터-흐름도)
2. [PostGIS `geography` 공간 수학 연산 & 2단계 차등 입지 엔진](#2-postgis-geography-공간-수학-연산--2단계-차등-입지-엔진)
3. [XGBoost ML 공공 갈등 민감도(CSS) 및 Closed-Loop 재학습 엔진](#3-xgboost-ml-공공-갈등-민감도css-및-closed-loop-재학습-엔진)
4. [pgvector 기반 3단계 Zero-Hardcoding 하이브리드 RAG 엔진](#4-pgvector-기반-3단계-zero-hardcoding-하이브리드-rag-엔진)
5. [3자 Multi-Agent AI 모의 심의 토론 & SSE 스트리밍 엔진](#5-3자-multi-agent-ai-모의-심의-토론--sse-스트리밍-엔진)
6. [SHA-256 블록체인형 행정 감사 원장 (Audit Ledger)](#6-sha-256-블록체인형-행정-감사-원장-audit-ledger)
7. [AWS Lightsail + Let's Encrypt SSL + GitHub Actions CI/CD 파이프라인](#7-aws-lightsail--lets-encrypt-ssl--github-actions-cicd-파이프라인)
8. [6단계 파이프라인 정밀 모듈 명세](#8-6단계-파이프라인-정밀-모듈-명세)

---

## 1. 시스템 아키텍처 및 하이브리드 데이터 흐름도

OmniSite SDSS 플랫폼은 초저지연 브라우저 연산과 고성능 파이썬 인공지능 백엔드, 공간 데이터베이스를 통합한 하이브리드 클라우드 아키텍처로 구축되었다.

```mermaid
graph TD
    Client[사용자 브라우저 (Next.js 16 Client Component)] -->|HTTPS / REST & SSE Stream| Nginx[Nginx Reverse Proxy (Port 80/443)]
    Nginx -->|Proxy Pass /| FE[Next.js 16 Server (Port 3000)]
    Nginx -->|Proxy Pass /api/v1| BE[FastAPI Backend Server (Port 8000)]
    
    BE -->|SQLAlchemy 2.0 Pool| DB[(PostgreSQL 15 + PostGIS 3.3 + pgvector 0.4.4)]
    BE -->|Async Client| GPT[OpenAI GPT-4o Multi-Agent API]
    BE -->|3-Stage RAG Vector Search| VectorDB[(district_regulations Vector Table)]
    BE -->|Audit Chain| HashChain[SHA-256 Audit Ledger]
    
    GitHub[GitHub Push origin main] -->|GitHub Actions Workflow| CI[appleboy/ssh-action Remote SSH]
    CI -->|Auto Build & Deploy| Docker[AWS Lightsail Docker Compose Production]
```

### 1.1 주요 서브시스템 역할 명세
- **Frontend (Next.js 16.2.10 Turbopack)**: Leaflet 1.9 비동기 싱글톤 지도 렌더링, 6단계 파이프라인 인터랙티브 UI, SSE 스트리밍 타자기 말풍선 분리 렌더링, A4 PDF 결재 리포트 생성.
- **Backend (FastAPI 0.110 Python 3.11)**: RESTful API 제공, PostGIS Spatial 쿼리 빌딩, AHP 고유값 연산, XGBoost CSS 모델 파이프라인, Async OpenAI SSE 스트리밍, SHA-256 해시 체인 연산.
- **Database (PostgreSQL 15 + PostGIS 3.3 + pgvector 0.4.4)**: 6,524개 지적 필지 공간 조인, 6,509개 상가 Point R-Tree 인덱싱, 72개 조례 문단 1,536차원 HNSW 임베딩 벡터 검색.

---

## 2. PostGIS `geography` 공간 수학 연산 & 2단계 차등 입지 엔진

### 2.1 위도 경도 구면 도(Degree) 단위 오차 극복 (WGS84 Ellipsoid)
서울 위도(37.53° N) 환경에서 단순 위경도 도(Degree) 단위 차이(`ST_DWithin(geom1, geom2, 0.002)`)를 적용하면, 경도 1도당 거리가 약 $88,200	ext{m}$로 축소되어 200m 규제가 실제 $176.4	ext{m}$로 연산되는 심각한 왜곡이 발생한다.

이를 차단하기 위해 [backend/app/routers/spatial.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/spatial.py) 621행의 공간 연산 구문을 **PostGIS WGS84 타원체 geography 실측 미터 연산**으로 승격시켰다:

```sql
SELECT c.pnu, c.address, c.land_area,
       ST_Distance(c.geom::geography, rz.geom::geography) AS distance_meters
FROM cadastral_lands c
JOIN restricted_zones rz ON ST_DWithin(c.geom::geography, rz.geom::geography, :parsed_dist)
WHERE c.is_excluded = FALSE;
```

### 2.2 2단계 차등 입지 정책 (2-Tier Exclusion Policy)
- **Tier 1 (법정 절대 금지구역 - Hard Drop 100% 원천 탈락)**:
  - 유치원/초중고등학교 교육환경보호구역 경계 200m 내부
  - 어린이집 보호구역 50m 내부
  - 버스정류소 10m 내부
  - 사용자 지정 가상 금지구역(`user_exclusion_zones`) 내부 침범 필지
  - ➔ 입지 추천 쿼리에서 **100% 원천 배제 (0% 오버랩)**.
- **Tier 2 (조건부 행정 주의구역 - Administrative Warning)**:
  - 완충 지대(200m~250m) 경계 인접 필지 및 사유지 필지
  - ➔ 입지 추천 리스트에 포함하되 UI 및 심의 결과에 **'⚠️ 행정 주의 부가설명'** 태그 박제.

---

## 3. XGBoost ML 공공 갈등 민감도(CSS) 및 Closed-Loop 재학습 엔진

### 3.1 갈등 민감도 (CSS, Conflict Sensitivity Score) 수식 명세
후보 부지에 대해 머신러닝 모델(XGBoost Classifier)이 산출하는 갈등 민감도 수식은 다음과 같다:

$$	ext{CSS} = f_{	ext{XGBoost}}\Big(	ext{Population}_{	ext{flow}}, 	ext{Shops}_{	ext{density}}, 	ext{Distance}_{	ext{school}}, 	ext{Complain}_{	ext{count}}, 	ext{Area}_{	ext{land}}\Big) 	imes 100$$

- **CSS < 30점 (🟢 보통)**: 갈등 요소 적음.
- **30 ≤ CSS < 70점 (🟡 위험)**: 상권 활성화와 주민 민원 대립.
- **CSS ≥ 70점 (🔴 매우 위험)**: 초밀집 주거지 및 학교 인접 구역.

### 3.2 Closed-Loop 피드백 재학습 파이프라인
사용자가 모의 심의 의결을 완료하거나 실증 사례를 추가할 때, 백엔드 비동기 서비스가 [backend/app/scripts/train_css_model.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/scripts/train_css_model.py)를 실행하여 XGBoost 모델을 핫스왑(Hot-swap) 재학습함으로써 정확도를 지속적으로 자가 진화시킨다.

---

## 4. pgvector 기반 3단계 Zero-Hardcoding 하이브리드 RAG 엔진

### 4.1 3단계 순차적 조례 탐색 파이프라인
1. **Stage 1 (OpenAI 1,536D Vector Similarity)**:
   $$	ext{Similarity} = 1 - ig(	ext{embedding} \Leftrightarrow 	ext{query\_vec}ig) \ge 0.20$$
   `district_regulations` 테이블 HNSW 인덱스를 통해 유사도 20% 이상의 자치구 조례 문단을 인출.
2. **Stage 2 (Dynamic Keyword Extraction Search)**:
   불용어를 제거한 동적 키워드(SQL `ILIKE` OR 조건)를 결합하여 조례 문단 보강.
3. **Stage 3 (DB Fallback Default Query)**:
   임베딩 연산 실패 시 자치구 기본 금연환경 조성 조례를 안전 폴백 인출.

하드코딩된 한국어 텍스트(`"금연"`, `"흡연"`)를 100% 척출하여 지자체 조례 파일이 변경되어도 자동으로 적용되는 **Zero-Hardcoding RAG 파이프라인**을 완성했다.

---

## 5. 3자 Multi-Agent AI 모의 심의 토론 & SSE 스트리밍 엔진

### 5.1 3인 페르소나 독립 릴레이 8턴 토론
- 👨‍💼 **상인대표 페르소나**: 유동인구 수용, 상권 활성화, 경제적 실익 피력.
- 🧑‍🤝‍🧑 **주민대표 페르소나**: 주거 정주 환경 파괴, 소음/악취, 무단투기 민원 우려 및 아이들 보행 안전 강조.
- ⚖️ **갈등조정관 페르소나**: 이격거리 1.5배 후퇴, 주민 위생 감찰권 및 삼진아웃 가동정지권 부여 중재안 타결.

### 5.2 SSE (Server-Sent Events) 브라우저 타자기 스트리밍
백엔드 FastAPI `EventSourceResponse`를 통해 10ms 단위 타자기 효과로 전달되며, Front-End React 렌더링 파서가 `data.meta` 태그를 분석하여 `[찬성측]`, `[반대측]`, `[정부측]`, `[시스템]` 4개 카드로 100% 독점 분리 표출한다.

---

## 6. SHA-256 블록체인형 행정 감사 원장 (Audit Ledger)

모든 의사결정 파이프라인은 DB `pipeline_execution_logs` 테이블에 블록체인 구조로 기록된다:

$$	ext{Current\_Hash} = 	ext{SHA256}(	ext{Prev\_Hash} + 	ext{Session\_ID} + 	ext{Step\_Number} + 	ext{Action\_Type} + 	ext{Detail\_JSON})$$

단 1비트의 사후 위변조도 체인 붕괴로 즉시 적발되어 행정 감사관에게 보고된다.

---

## 7. AWS Lightsail + Let's Encrypt SSL + GitHub Actions CI/CD 파이프라인

### 7.1 프로덕션 배포 토폴로지
- **도메인**: `omnisite.p-e.kr` (내도메인.한국 A 레코드 바인딩)
- **SSL 보안**: Let's Encrypt 90일 자동 갱신 HTTPS (포트 443 ➔ Nginx ➔ 3000/8000)
- **CI/CD 파이프라인**: [.github/workflows/deploy.yml](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/.github/workflows/deploy.yml) 이식 완료.
  - `git push origin main` ➔ GitHub Actions ➔ AWS SSH ➔ `docker compose up -d --build` 원클릭 30초 무중단 배포 완공.

---

## 8. 6단계 파이프라인 정밀 모듈 명세

```mermaid
graph LR
    S1[Step 1: AI 감리] --> S2[Step 2: ML 재학습]
    S2 --> S3[Step 3: HITL 마커]
    S3 --> S4[Step 4: AHP 가중치]
    S4 --> S5[Step 5: 입지 추천]
    S5 --> S6[Step 6: AI 토론]
```

- **Step 1**: `POST /api/v1/upload/audit` PDF OCR & 3단계 RAG 조례 감리
- **Step 2**: `POST /api/v1/model/retrain` Closed-Loop XGBoost ML 재학습
- **Step 3**: Leaflet GIS `marker.on('dragend')` & 버퍼 침범 롤백 (`isWarning = false`)
- **Step 4**: `POST /api/v1/ahp/calculate` 쌍대비교 $CR < 0.1$ 일관성 검증
- **Step 5**: `POST /api/v1/spatial/recommend-sites` PostGIS geography TOP 5 필지 랭킹
- **Step 6**: `GET /api/v1/spatial/debate-stream` SSE 8턴 멀티에이전트 토론 & PDF 보고서 인출

---
**최종 문서 승인**: 2026년 8월 10일  
**시스템 버전**: `v1.0.0-Production Release`  
**작성 기관**: 스마트시티 SDSS 옴니사이트(OmniSite) 개발팀