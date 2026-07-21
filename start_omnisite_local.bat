@echo off
title OmniSite Local Hybrid Runner (v1.2.0)
echo ====================================================================
echo                OmniSite 로컬 간편 기동 및 자동 세팅 도구
echo ====================================================================
echo.
echo [공지] 이 도구는 도커(Docker Desktop)가 실행 중인 상태에서 작동합니다.
echo.

:: 1. Docker 실행 여부 검증
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Docker Desktop이 꺼져있거나 실행되지 않았습니다!
    echo        Docker Desktop을 먼저 실행한 뒤 아무 키나 눌러주세요.
    pause
    exit /b
)

echo [1/4] 데이터베이스 컨테이너(PostGIS)를 가동합니다...
docker-compose up database -d
echo.

:: 2. 백엔드 세팅
echo [2/4] 백엔드(FastAPI) 파이썬 가상환경 및 패키지 세팅 중...
cd backend
if not exist venv (
    echo 파이썬 가상환경 생성 중...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo 백엔드 패키지 의존성 최신화 인스톨 중...
pip install -r requirements.txt --quiet
echo.

:: 3. 최초 콜드스타트 데이터 벌크 적재 및 조인 실행 여부 검사
echo [3/4] 최초 콜드스타트 데이터 세트 적재 및 공간 조인 실행 중...
python app/scripts/clean_and_organize_datasets.py
python app/scripts/create_decision_histories_table.py
python app/scripts/train_css_model.py
echo.

:: 4. 백엔드 및 프론트엔드 동시 실행
echo [4/4] 프론트엔드(Next.js) 의존성 확인 후 통합 핫리로드 구동...
start /b cmd /c "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

cd ../frontend
if not exist node_modules (
    echo 프론트엔드 node 패키지 최초 인스톨 중...
    npm install --silent
)
echo Next.js 서버 기동 중...
start /b cmd /c "npm run dev"

echo.
echo ====================================================================
echo  OmniSite 기동 성공! 잠시 후 웹 브라우저가 자동으로 켜집니다.
echo  - 웹 화면 접속 주소: http://localhost:3000
echo  - 백엔드 API 주소  : http://localhost:8000
echo ====================================================================
echo.

timeout /t 5 >nul
start http://localhost:3000

:: 프로세스 잔존 대기
pause
