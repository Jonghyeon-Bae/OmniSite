# 🖥️ OmniSite SDSS 로컬(Local) 환경 초기 세팅 가이드 (초보자용 100% 실전 지침서)

본 지침서는 **컴퓨터 프로그래밍이나 터미널 명령어에 익숙하지 않은 행정관, 심사위원, 초보 개발자**분들도 단 한 번의 에러 없이 OmniSite SDSS 플랫폼을 로컬 컴퓨터에 100% 성공적으로 구동할 수 있도록 작성된 초상세 표준 가이드입니다.

---

## 📋 1. 사전 준비물 (Prerequisites)

시스템을 구동하기 전, 아래 2가지 프로그램이 컴퓨터에 설치되어 있어야 합니다.

### 1-1. Docker Desktop 설치
1. [도커 데스크톱 공식 다운로드 페이지](https://www.docker.com/products/docker-desktop/)로 이동하여 **`Download for Windows`** (또는 Mac) 버튼을 클릭합니다.
2. 다운로드된 설치 파일을 실행하여 기본 옵션 그대로 `Next`를 눌러 설치를 완료합니다.
3. 컴퓨터를 재부팅한 후 **Docker Desktop** 프로그램을 실행합니다.
4. 화면 우측 하단(작업 표시줄)의 **고래 모양 아이콘에 녹색 불(Running)**이 들어오면 준비 완료입니다.

### 1-2. OpenAI API 키 준비
- 본 플랫폼은 3자 AI 모의 심의 토론 및 RAG 조례 매핑을 위해 OpenAI GPT-4o를 사용합니다.
- 개인 또는 기관의 `sk-proj-...` 형식의 OpenAI API Key를 준비해 주십시오.

---

## 🚀 2. [방식 A] 도커(Docker) 원클릭 자동 실행 가이드 (가장 추천하는 방법)

복잡한 파이썬이나 노드JS 패키지 설치 없이, **단 3줄의 명령어**로 모든 웹 화면과 인공지능 백엔드, 공간 DB가 자동으로 조립되어 실행되는 방식입니다.

### 1단계: 프로젝트 폴더에서 터미널 열기
1. 프로젝트 폴더(`1.0-prototype`)로 이동합니다.
2. 폴더 빈 공간에서 `Shift + 마우스 우클릭` ➔ **`여기에 PowerShell 창 열기`** (또는 `CMD에서 열기`)를 클릭합니다.

### 2단계: 환경 변수(`.env`) 파일 확인
프로젝트 루트 디렉터리의 `.env` 파일을 메모장으로 열고 본인의 OpenAI API Key를 입력 후 저장합니다:
```env
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

### 3단계: 도커 컨테이너 빌드 및 실행
터미널에 아래 명령어를 복사하여 입력하고 엔터를 칩니다:
```bash
docker compose up -d --build
```
- **어떤 과정인가요?**: 웹 화면(Next.js), AI 백엔드(FastAPI), 공간 DB(PostgreSQL+PostGIS) 3개 가상 시스템을 자동으로 조립하는 과정입니다. (최초 실행 시 약 1~2분 소요)
- **성공 로그**:
  ```text
  ✔ Container omnisite_dev_db     Started
  ✔ Container omnisite_dev_be     Started
  ✔ Container omnisite_dev_fe     Started
  ```

### 4단계: 용산구 공공 지리정보 데이터셋 적재 (Seeding)
터미널에 아래 명령어를 입력합니다:
```bash
docker compose exec backend python seed_db.py
```
- **어떤 과정인가요?**: 6,524개 지적 필지, 6,509개 상가, 268개 제한구역 공간 빅데이터를 DB에 적재하는 단계입니다.
- **성공 로그**: 화면 맨 아래에 **`[+] Seeding completed successfully!`** 문구가 나오면 성공입니다.

### 5단계: 갈등 예측 인공지능(ML) 학습 모델 적재
터미널에 아래 명령어를 입력합니다:
```bash
docker compose exec backend python app/scripts/train_css_model.py
```
- **성공 로그**: 화면 맨 아래에 **`SUCCESS: Model registration completed.`** 문구가 나오면 인공지능 모델 등록 완료입니다.

---

## 🌐 3. 시스템 접속 및 로그인 방법

1. 브라우저(Chrome, Edge)를 열고 주소창에 아래 주소를 입력합니다:
   - **웹 플랫폼 접속 주소**: [http://localhost:3000](http://localhost:3000)
2. 초기 관리자 계정으로 로그인합니다:
   - **아이디**: `admin`
   - **비밀번호**: `admin1234`
3. 로그인 성공 시 화면 상단 세션 타이머가 작동하며 **`용산구 공간 입지 분석 및 AI 모의 심의 대시보드`**가 정상 표출됩니다.

---

## 💻 4. [방식 B] 개발자용 로컬 직접 가동 가이드 (소스코드 수정/디버깅용)

개발자분들이 VS Code 등에서 소스코드를 직접 고치며 핫리로드(Hot-reload) 상태로 테스트할 때 사용하는 방식입니다.

### 4.1 PostgreSQL 공간 DB 단독 켜기
```bash
# 프로젝트 루트 디렉터리에서 실행
docker compose up database -d
```

### 4.2 FastAPI 백엔드 개발 서버 실행
```bash
# 1. backend 폴더로 이동
cd backend

# 2. 파이썬 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate          # Windows CMD 기준 (PowerShell은 venv\Scripts\Activate.ps1)

# 3. 의존성 라이브러리 설치
pip install -r requirements.txt

# 4. 백엔드 핫리로드 서버 가동 (8000포트)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4.3 Next.js 프론트엔드 개발 서버 실행
```bash
# 새로운 터미널 창을 열고 frontend 폴더로 이동
cd frontend

# 노드 패키지 설치 및 개발 서버 실행 (3000포트)
npm install
npm run dev
```

---

## ❓ 5. 자주 발생하는 초보자 질문 및 해법 (Troubleshooting)

### Q1. `http://localhost:3000` 접속 시 "사이트에 연결할 수 없음"이라고 뜹니다.
- **원인**: Docker Desktop이 꺼져있거나 컨테이너가 켜지지 않은 상태입니다.
- **해결**: Docker Desktop 우측 하단 고래 아이콘 녹색 불을 확인하고, `docker compose up -d` 명령어를 다시 실행하십시오.

### Q2. 로그인 후 AI 모의 심의 토론이 시작되지 않거나 멈춥니다.
- **원인**: `.env` 파일의 OpenAI API Key가 올바르지 않거나 잔액이 부족한 경우입니다.
- **해결**: `.env` 파일의 `OPENAI_API_KEY=sk-proj-...` 값을 확인하고 올바른 키로 수정한 뒤 백엔드를 재기동하십시오.

---


---

## ☁️ 6. AWS Lightsail 프로덕션 배포 및 내도메인.한국 SSL(HTTPS) 연동 가이드

본 섹션은 구축된 OmniSite SDSS 클라우드 서비스를 실제 고정 도메인 및 HTTPS 보안 연동으로 상용화하기 위한 표준 가이드입니다.

### 6-1. AWS Lightsail 도메인 A 레코드 연결 (내도메인.한국)
1. **[내도메인.한국](https://xn--299a1v27nv4m.xn--3e0b707e/) 접속 및 로그인** 후 등록된 도메인의 **[상세설정]**으로 이동합니다.
2. **대표 주소(루트) IP연결(A)** 항목에 체크 후 AWS Lightsail 고정 IP를 등록합니다.
3. **`www` 서브도메인 레코드** 항목에도 동일한 Lightsail 고정 IP를 등록 후 저장합니다.
4. AWS SSH 터미널에서 `ping yourdomain.p-e.kr`을 실행하여 고정 IP 핑 응답을 확인합니다.

### 6-2. 호스트 Nginx 설정 및 Let's Encrypt Certbot SSL 무료 인증서 발급
1. **Nginx 및 Certbot 패키지 설치**:
   ```bash
   sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
   ```
2. **Nginx 프록시 설정 (`/etc/nginx/sites-available/default`)**:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.p-e.kr www.yourdomain.p-e.kr;

       location / {
           proxy_pass http://127.0.0.1:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /api/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           client_max_body_size 50M;
       }
   }
   ```
3. **80 포트 점유 해제 및 Nginx 재시작 후 SSL 인증서 발급**:
   ```bash
   docker compose -f docker-compose.production.yml down
   sudo systemctl restart nginx
   sudo certbot --nginx -d yourdomain.p-e.kr -d www.yourdomain.p-e.kr
   ```
4. **프로덕션 도커 재배포**:
   ```bash
   docker compose -f docker-compose.production.yml up -d --build
   ```

---
**최종 개정일자**: 2026년 8월 10일  
**작성자**: Antigravity Senior Peer Development Team  
