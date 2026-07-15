# OmniSite 클라우드 이관 및 배포 가이드라인 (v1.1-stable)

본 문서는 **OmniSite v1.1-stable**의 상용 서비스 릴리즈를 위해 가성비 가상 사설 서버(AWS Lightsail, Vultr 등) 및 Docker-Compose 컨테이너 오케스트레이션을 활용하여 인프라를 무결하게 빌드하고 배포하기 위한 기술 명세서입니다.

---

## 🖥️ 1. 클라우드 인프라 노드 사양 (Specification)

비용 최적화(Cost Optimization)와 인프라 격리성을 동시에 만족하는 단일 VPS 배포 사양입니다.

*   **권장 플랫폼:** AWS Lightsail (EC2 대비 아웃바운드 네트워크 전송 트래픽 정액 제공으로 요금 폭탄 예방)
*   **인스턴스 스펙:** **1 vCPU / 2GB RAM / 40GB SSD** (월 $10 고정 플랜)
    *   *크레딧 적용 시:* AWS 가입 시 지급되는 180일간의 무료 크레딧 범위 내에서 월 비용 0원 청구 가능.
*   **OS:** Ubuntu 22.04 LTS (x86_64)

---

## 💾 2. 메모리 고갈(OOM) 방지를 위한 Swap Space 설정

제한된 RAM(1~2GB) 하에서 DB, 백엔드, 프론트엔드 컨테이너 3개를 가동하면 메모리 고갈로 인한 프로세스 셧다운이 발생하므로 SSD에 가상 Swap 메모리를 강제 할당해야 합니다.

### 🛠️ Swap 메모리 4GB 강제 할당 터미널 명령어
```bash
# 1. 4GB 크기의 스왑 파일 생성
sudo fallocate -l 4G /swapfile

# 2. 파일 권한을 루트 전용(읽기/쓰기)으로 제한
sudo chmod 600 /swapfile

# 3. 파일을 Linux 스왑 공간으로 포맷
sudo mkswap /swapfile

# 4. 스왑 공간 활성화
sudo swapon /swapfile

# 5. 재부팅 시에도 유지되도록 /etc/fstab에 영구 추가
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 6. 활성화 정상 여부 검증
free -h
```

---

## 🐳 3. Docker-Compose 상용 배포 환경 (Production Suite)

### 3.1. [NEW] docker-compose.production.yml 설정 파일 구조
```yaml
version: '3.8'

services:
  database:
    image: postgis/postgis:15-3.3
    container_name: omnisite_prod_db
    restart: always
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: Admin
      POSTGRES_PASSWORD: admin1234_production_key
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    # 호스트 외부 포트(5432)는 격리하여 보안 침투 차단

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: omnisite_prod_be
    restart: always
    environment:
      - DATABASE_URL=postgresql+psycopg://Admin:admin1234_production_key@database:5432/postgres
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - database

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: omnisite_prod_fe
    restart: always
    ports:
      - "80:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://your-domain-or-ip:8000
    depends_on:
      - backend

volumes:
  postgres_prod_data:
```

---

## 🔒 4. Nginx Reverse Proxy 및 SSL(HTTPS) 연동

클라이언트의 요청을 대문에서 받아 안전하게 분배하고 암호화 프로토콜을 적용하기 위해 Nginx 설정을 전위에 배치합니다.

### 🛠️ /etc/nginx/sites-available/default 설정 양식
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Certbot Let's Encrypt 인증용 챌린지 라우트
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # HTTP 요청을 HTTPS로 강제 리다이렉트
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Next.js 프론트엔드 프록시
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # FastAPI 백엔드 API 프록시
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 🗄️ 5. 클라우드 기동 후 초기 데이터 시딩 프로시저

컨테이너가 최초 기동되면 DB는 빈 상태이므로, 백엔드 컨테이너 내부에 접속하여 지적 및 의사결정 이력 테이블과 조례 임베딩 데이터를 벌크 적재(Ingestion)해야 합니다.

```bash
# 1. 실행 중인 백엔드 컨테이너 셸 접속
docker exec -it omnisite_prod_be bash

# 2. 공간 cadastral_lands 테이블 및 국유재산 병합 시딩 스크립트 실행
python app/scripts/import_national_assets.py

# 3. 조례 RAG 임베딩 데이터 pgvector 적재 실행
python app/scripts/ingest_regulations.py

# 4. 의사결정 심의 이력 테이블 생성 및 시드 데이터 적재 실행
python app/scripts/create_decision_histories_table.py
```

상기 명시된 순서대로 배포 명령어를 수행하면 로컬 호스트 의존성 및 하드코딩 리스크가 제거된 상태로 클라우드 상에 **OmniSite v1.1-stable**이 완전 무오류 런칭됩니다.
