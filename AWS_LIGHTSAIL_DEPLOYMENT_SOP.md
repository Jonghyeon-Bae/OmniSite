# OmniSite AWS Lightsail 프로덕션 배포 및 DB 복제 SOP (v1.5.0)

본 지침서는 **AWS Lightsail 인스턴스** 상에서 OmniSite SDSS 플랫폼을 단 한 번의 오류도 없이 1:1 완벽 복제 배포하고, `pgvector`/`PostGIS` 마운트 에러 및 경로 불일치를 완전히 방지하기 위한 표준 운영 절차서(Standard Operating Procedure)입니다.

---

## 📋 1. 사전 권장 인스턴스 및 네트워크 설정

### 1-1. 인스턴스 사양
* **OS**: Ubuntu 22.04 LTS (64-bit)
* **권장 사양**: Memory 4 GB / 2 vCPUs / 80 GB SSD (최소 사양: 2 GB RAM)
* **인바운드 방화벽 규칙 (Lightsail Networking 탭)**:
  | 프로토콜 | 포트 범위 | 용도 |
  | :--- | :--- | :--- |
  | **TCP** | `22` | SSH 원격 접속 |
  | **TCP** | `80` | Next.js 프론트엔드 웹 서비스 (HTTP) |
  | **TCP** | `8000` | FastAPI 백엔드 API 서비스 |
  | **TCP** | `443` | SSL/TLS (HTTPS 적용 시 선택) |

---

## 🛠️ 2. AWS Lightsail 초기 도커(Docker) 환경 구축

인스턴스 SSH 접속 후 아래 명령어를 순차적으로 실행합니다.

```bash
# 1. 패키지 업데이트 및 도커/도커 컴포즈 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git

# 2. 현재 사용자 도커 권한 부여 (재접속 필요)
sudo usermod -aG docker $USER
newgrp docker

# 3. 도커 서비스 가동 확인
docker --version
docker compose version
```

---

## 📂 3. 프로젝트 소스코드 클론 및 환경 변수 설정

```bash
# 1. 프로젝트 디렉터리 클론 및 이동
git clone https://github.com/Jonghyeon-Bae/OmniSite.git omnisite
cd omnisite

# 2. 프로덕션 전용 환경 변수 파일 생성 (.env)
cat << 'EOF' > .env
POSTGRES_PASSWORD=admin1234_production_key
OPENAI_API_KEY=your_openai_api_key_here
# AWS Lightsail 인스턴스의 공인 IP(Public IP)로 설정 (예: http://54.180.123.45:8000)
NEXT_PUBLIC_API_URL=http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000
CORS_ORIGINS=http://localhost:3000,http://<YOUR_LIGHTSAIL_PUBLIC_IP>,http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000,*
EOF

# 3. Public IP 반영 (IP 주소 직접 수정)
nano .env
```

---

## 🚀 4. 컨테이너 빌드 및 프로덕션 배포

`docker-compose.production.yml` 기반으로 DB(`PostGIS` + `pgvector`), 백엔드(`FastAPI`), 프론트엔드(`Next.js`) 3대 컨테이너를 가동합니다.

```bash
# 1. 도커 이미지 무결성 빌드 (DB pgvector 컴파일 포함)
docker compose -f docker-compose.production.yml build

# 2. 백그라운드 멀티 컨테이너 가동 (DB Healthcheck 자동 대기)
docker compose -f docker-compose.production.yml up -d

# 3. 가동 상태 실측 확인
docker compose -f docker-compose.production.yml ps
```

---

## 🗄️ 5. 데이터베이스 exact-copy 시딩 (ColdStart Pipeline)

AWS 인스턴스 DB에 로컬 데이터베이스와 동일한 21개 스키마 구축 및 6,524 필지, 6,509 상가, 268 제한구역 데이터 전수 적재를 진행합니다.

```bash
# 백엔드 컨테이너 내부에서 seed_db.py 콜드스타트 실행
docker compose -f docker-compose.production.yml exec backend python /workspace/seed_db.py
```

### 🎯 시딩 무결성 검증 (DB 데이터 건수 실측)
```bash
docker compose -f docker-compose.production.yml exec database psql -U Admin -d postgres -c "SELECT 'cadastral_lands' AS table, COUNT(*) FROM cadastral_lands UNION ALL SELECT 'commercial_shops', COUNT(*) FROM commercial_shops UNION ALL SELECT 'restricted_zones', COUNT(*) FROM restricted_zones;"
```
* **정상 결과 수치**:
  - `cadastral_lands`: **6,524**
  - `commercial_shops`: **6,509**
  - `restricted_zones`: **268**

---

## 🔍 6. 자주 발생하는 AWS 마운트/배포 에러 및 해결 가이드 (Troubleshooting)

| 에러 유형 | 원인 | 조치 사항 (본 SOP 자동 반영됨) |
| :--- | :--- | :--- |
| **`pgvector` Extension Error** | PostgreSQL 기본 이미지에 vector 빌드 헤더 부재 | `DB/Dockerfile` 내 `postgresql-server-dev-15` 헤더 기반 `pgvector` v0.4.4 자동 컴파일 처리됨 |
| **`Datasets/` Path Not Found** | 백엔드 컨테이너 내 시딩 데이터셋 부재 | `docker-compose.production.yml`에 `./Datasets:/workspace/Datasets:ro` 볼륨 마운트 적용 완료 |
| **Table Mismatch (`Relation does not exist`)** | 초기 DB 스키마 21개 미생성 | `./DB/init/01_schema.sql`이 `/docker-entrypoint-initdb.d`로 자동 마운트되어 DB 최초 가동 시 100% 자동 생성 |
| **Frontend API Connection Refused** | `NEXT_PUBLIC_API_URL`이 `localhost`로 고정됨 | `.env` 파일 내 `NEXT_PUBLIC_API_URL=http://<LIGHTSAIL_IP>:8000`으로 유동 바인딩 적용 |
| **Module Import Error (`backend.app...`)** | 도커 컨테이너 내부 파이썬 경로 차이 | 백엔드 컨테이너 환경변수에 `PYTHONPATH=/workspace` 지정으로 해결됨 |

---

## 📌 7. 배포 유지보수 및 재가동 명령어

```bash
# 컨테이너 로그 실시간 모니터링
docker compose -f docker-compose.production.yml logs -f

# 서비스 재가동
docker compose -f docker-compose.production.yml restart

# 시스템 완전 종료
docker compose -f docker-compose.production.yml down
```
