# OmniSite 클라우드 이관 및 AWS 실전 배포 매뉴얼 (v1.2.0-stable)

본 문서는 **OmniSite v1.2.0** 프로덕션 빌드의 실제 AWS(Lightsail 등) 클라우드 배포를 위해 인프라를 무결하게 빌드하고 런칭하기 위한 실전 기술 명세서입니다.

---

## 🖥️ 1. 클라우드 인스턴스 사양 (AWS Lightsail)

비용 최적화와 격리 보안성을 동시에 충족하는 권장 VPS 사양입니다.

- **플랫폼:** AWS Lightsail (EC2 대비 고정 데이터 요금제로 요금 폭탄 예방)
- **스펙:** **1 vCPU / 2GB RAM / 40GB SSD** (월 $10 고정 플랜)
- **OS:** Ubuntu 22.04 LTS (x86_64)
- **사전 설정:** AWS Lightsail 인스턴스 관리 콘솔에서 고정 IP(Static IP)를 발급받아 연결해야 합니다.

---

## 💾 2. 메모리 고갈(OOM) 방지를 위한 Swap 설정 (필수)

2GB RAM 단일 서버에서 DB, 백엔드, Next.js 컨테이너를 한 번에 빌드하고 기동하면 메모리가 부족하여 인스턴스가 셧다운됩니다. 빌드 전 반드시 아래 명령어로 **Swap 공간을 4GB 확장**하십시오.

```bash
# 1. 4GB 스왑 파일 할당
sudo fallocate -l 4G /swapfile

# 2. 보안 권한 설정
sudo chmod 600 /swapfile

# 3. 스왑 포맷팅 및 활성화
sudo mkswap /swapfile
sudo swapon /swapfile

# 4. 재부팅 시 자동 활성화되도록 fstab 등록
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 5. 활성화 여부 확인
free -h
```

---

## 🐳 3. docker-compose.production.yml 패키지 구동

저희가 빌드한 상용 컨테이너 빌드 명세를 활용하여 프로젝트 루트 경로에서 배포 컨테이너를 가동합니다.

### 3.1. 호스트 환경 변수 파일 생성 (`.env`)

루트 경로에 `.env` 파일을 생성하고 실제 상용 운영 키값을 기재합니다.

```env
OPENAI_API_KEY=your_real_openai_api_key_here
NEXT_PUBLIC_API_URL=http://your_aws_static_ip_here:8000
```

> [!WARNING]
>
> - `NEXT_PUBLIC_API_URL` 값에 `localhost` 대신 **AWS 실제 고정 IP 주소**를 정확히 명기해야 브라우저의 CORS 매칭 오류가 발생하지 않습니다.

### 3.2. 상용 백그라운드 구동 명령어

```bash
# 1. 이전 빌드 캐시 청소 및 백그라운드 빌드/가동
docker-compose -f docker-compose.production.yml up --build -d

# 2. 컨테이너 가동 정합성 검수
docker-compose -f docker-compose.production.yml ps
```

---

## 🔒 4. Nginx Reverse Proxy 및 SSL (HTTPS) 연동

사용자 웹 트래픽을 안전하게 HTTPS 프로토콜로 우회 처리하기 위해 Nginx 리버스 프록시 설정을 전위에 배치합니다.

### 4.1. Nginx 설치 및 Let's Encrypt SSL 발급

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Certbot을 통한 도메인 SSL 인증서 발급
sudo certbot --nginx -d your-domain.com
```

### 4.2. /etc/nginx/sites-available/default 프록시 바인딩 설정

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri; # HTTP -> HTTPS 강제 리다이렉트
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Next.js 프론트엔드 프록시 (포트 80요청 -> 3000포트 전달)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # FastAPI 백엔드 API 프록시 (포트 8000요청 -> 8000포트 전달)
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

설정 후 Nginx를 리로드합니다: `sudo systemctl restart nginx`

---

## 🗄️ 5. 클라우드 기동 후 초기 데이터 마이그레이션 프로시저

컨테이너가 최초로 올라가면 데이터베이스는 뼈대만 있는 상태이므로, 백엔드 컨테이너 셸에 진입하여 시군구/읍면동 공간 경계 및 지적 데이터 세트를 적재합니다.

```bash
# 1. 백엔드 컨테이너 내부 셸 접속
docker exec -it omnisite_prod_be bash

# 2. Datasets/ 디렉토리로 분류 이관된 파일을 PostGIS 공간 테이블로 로딩
# (경계선, 지적도 벌크 인서트 및 공간 조인 정합 일치 연산 실행)
python app/scripts/clean_and_organize_datasets.py

# 3. 비어있는 의사결정 이력 테이블 뼈대 생성
python app/scripts/create_decision_histories_table.py

# 4. XGBoost 모델의 일반화 파라미터 기반 초기 훈련 가동
python app/scripts/train_css_model.py
```

이 매뉴얼 순서대로 기동하면 로컬 종속성이 완전히 배제된 상태로 AWS 클라우드 상에 **OmniSite v1.2.0**이 안전하게 런칭됩니다.
