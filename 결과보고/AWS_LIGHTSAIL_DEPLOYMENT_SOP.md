# ☁️ OmniSite SDSS AWS Lightsail 클라우드 배포 및 초기 세팅 SOP (v2.0.0)

본 지침서는 **AWS Lightsail 인스턴스(4GB RAM, 2 vCPU, 80GB SSD)** 환경 상에서 OmniSite SDSS 플랫폼을 단 한 번의 오류도 없이 1:1 완벽 복제 배포하고, 우분투 패키지 락 충돌 및 메로리 부족 멈춤을 100% 방지하기 위한 초보자용 표준 운영 절차서(SOP)입니다.

---

## 📋 1. 사전 인스턴스 및 네트워크 설정

### 1-1. 권장 인스턴스 사양
- **OS**: Ubuntu 22.04 LTS (64-bit)
- **사양**: Memory 4 GB / 2 vCPUs / 80 GB SSD

### 1-2. 인바운드 방화벽 규칙 (AWS Lightsail 콘솔 Networking 탭)
Lightsail 관리 콘솔 ➔ Networking 탭에서 아래 5개 포트가 열려있는지 확인합니다:

| 프로토콜 | 포트 범위 | 용도 |
| :--- | :--- | :--- |
| **TCP** | `22` | SSH 원격 접속 |
| **TCP** | `80` | Next.js 프론트엔드 웹 서비스 (HTTP 접속 대문) |
| **TCP** | `8000` | FastAPI 백엔드 API 서비스 |
| **TCP** | `443` | SSL/TLS (HTTPS) |
| **TCP** | `3000` | 프론트엔드 자체 내부 포트 |

---

## 🚀 2. AWS Lightsail 실전 5단계 초기 세팅 (SSH 터미널 실행)

AWS Lightsail 웹 SSH 터미널을 열고 아래 명령어를 순서대로 복사하여 붙여넣으십시오.

---

### 1단계: Swap 가상 메모리 4GB 추가 (빌드 시 OOM 멈춤 원천 차단)
Next.js Turbopack 프로덕션 빌드 시 메모리가 부족하여 서버가 멈추는 현상을 방지합니다.

```bash
# 1. 4GB Swap 파일 생성 및 권한 설정
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. 서버 부팅 시 자동 적용 등록
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab

# 3. 가상 메모리 확보 확인 (Swap: 4.0Gi 확인)
free -h
```

---

### 2단계: 패키지 꼬임 복구 및 도커(Docker) 공식 자동 설치
`apt upgrade` 집행 시 발생하는 우분투 패키지 충돌(`pkgProblemResolver`)을 우회하는 안전 설치법입니다.

```bash
# 1. 의존성 꼬임 복구 및 기본 apt 최신화 (upgrade 불필요)
sudo dpkg --configure -a
sudo apt --fix-broken install -y
sudo apt update -y && sudo apt install -y git curl

# 2. 도커(Docker Engine & Compose V2) 공식 자동 설치 스크립트 실행
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 3. 현재 사용자 도커 권한 부여 및 그룹 갱신
sudo usermod -aG docker $USER
newgrp docker

# 4. 도커 정상 가동 확인
docker compose version
```

---

### 3단계: 소스코드 클론 및 프로덕션 환경 변수(`.env`) 설정

```bash
# 1. 깃허브 프로젝트 클론 및 이동
git clone https://github.com/Jonghyeon-Bae/OmniSite.git omnisite
cd omnisite

# 2. .env 프로덕션 환경 변수 파일 생성
# (※ <YOUR_LIGHTSAIL_PUBLIC_IP> 자리에 본인 인스턴스의 공인 IP를 적어주십시오)
cat << 'EOF' > .env
POSTGRES_PASSWORD=admin1234_production_key
OPENAI_API_KEY=your_openai_api_key_here
NEXT_PUBLIC_API_URL=http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000
CORS_ORIGINS=http://localhost:3000,http://<YOUR_LIGHTSAIL_PUBLIC_IP>,http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000,*
EOF

# 3. IP 주소 수정 필요 시 nano 편집기 사용
nano .env
```

---

### 4단계: 도커 프로덕션 멀티 컨테이너 빌드 & 실행

```bash
# 1. 멀티 컨테이너 무결성 빌드 및 백그라운드 가동
docker compose -f docker-compose.production.yml up -d --build

# 2. 가동 상태 실측 확인 (omnisite_prod_db, be, fe 3개 모두 healthy/running 확인)
docker compose -f docker-compose.production.yml ps
```

---

### 5단계: 로컬 100% exact-copy 데이터베이스 시딩 (Coldstart Seeding)

```bash
# 1. 백엔드 컨테이너 내부에서 seed_db.py 콜드스타트 실행
docker compose -f docker-compose.production.yml exec backend python /workspace/seed_db.py

# 2. DB 시딩 무결성 건수 검증
docker compose -f docker-compose.production.yml exec database psql -U Admin -d postgres -c "SELECT 'cadastral_lands' AS table_name, COUNT(*) FROM cadastral_lands UNION ALL SELECT 'commercial_shops', COUNT(*) FROM commercial_shops UNION ALL SELECT 'restricted_zones', COUNT(*) FROM restricted_zones;"
```

- **정상 인출 수치**:
  - `cadastral_lands`: **6,524**
  - `commercial_shops`: **6,509**
  - `restricted_zones`: **268**

---

## 🌐 3. 클라우드 서비스 접속 주소

- **웹 플랫폼 접속 주소 (HTTP 80포트 대문)**: `http://<YOUR_LIGHTSAIL_PUBLIC_IP>`
- **FastAPI 백엔드 Swagger API (8000포트)**: `http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000/docs`
- **초기 관리자 계정**: ID `admin` / Password `admin1234`

---

## 📌 4. 서버 유지보수 및 재가동 명령어 족보

```bash
# 컨테이너 실시간 로그 확인
docker compose -f docker-compose.production.yml logs -f

# 서비스 완전 재가동
docker compose -f docker-compose.production.yml restart

# 서비스 완전 종료
docker compose -f docker-compose.production.yml down
```

---
**작성일자**: 2026년 8월 8일  
**작성자**: Antigravity Senior Peer Development Team  
