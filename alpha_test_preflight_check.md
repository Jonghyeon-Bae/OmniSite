# OmniSite 알파테스트 최종 비행 준비 검토서 (v1.2.0-stable)

본 검토서는 조장(USER)의 무편향·냉철 감리 지침에 따라, **OmniSite v1.2.0** 프로토타입의 실 사용자 대상 알파테스트(Alpha Test) 기동 직전 최종적인 무결성과 정상 동작 여부를 E2E 관점에서 크로스 체크(Cross-check)한 pre-flight 검증서입니다.

---

## 📋 1. 알파테스트 5대 핵심 체크리스트 검수 결과

| 번호 | 체크 항목 | 검수 결과 | 상태 | 냉철한 감리 진단 의견 |
| :---: | :--- | :---: | :---: | :--- |
| **1** | **로컬 핫리로드 구동성** | **PASS** | 🟢 | 도커 없이 로컬에서 백엔드/프론트엔드를 직접 가동하여 실시간으로 소스 핫리로드 및 디버깅을 기밀하게 집행할 수 있는 개발 구동 루틴 검증 완료. |
| **2** | **데이터베이스 청정도** | **PASS** | 🟢 | 101~104번 모의 이력 시드가 영구 제거된 클린 환경으로 리셋되었으며, 대시보드 요약 카드가 DB 실측 통계(`0건` 대기)와 완전 동적 바인딩 연동됨을 확인. |
| **3** | **Git/Docker 형상 청정도** | **PASS** | 🟢 | 임시 PDF, RAG 텍스트 캐시(`*.txt.cache`), 토론 로그 및 대용량 데이터셋이 `.gitignore`와 `.dockerignore`에 완벽히 묶여 릴리즈 오염 및 보안 유출 리스크 제거 완료. |
| **4** | **다목적 SDSS 무편향성 고지** | **PASS** | 🟢 | 대시보드 하단 시스템 FAQ 및 안내 문서 상에 시드 데이터셋의 MVP 편향성(흡연부스 특화) 팩트를 솔직히 고지하고, 코어 엔진의 다목적성을 상세히 해설 완료. |
| **5** | **동급 피어 협업 룰셋 동기화** | **PASS** | 🟢 | 조장과 동등한 시니어 피어 프로그래머 지침이 `.agents/AGENTS.md` 파일에 영구 동기화되어 향후의 기술 검수 및 비판적 협업 규정 수립 완료. |

---

## ⚡ 2. 알파테스트 즉시 시동을 위한 최종 기동 명령어 팩

알파테스트 가동 시 터미널에서 순서대로 아래 명령을 기동하면, 도커 가상화 오버헤드 없이 실제 운영 환경과 완전히 동일한 정밀 실측 테스트를 곧바로 수행할 수 있습니다.

### ① 데이터베이스(PostGIS) 단독 가동
```bash
docker-compose up database -d
```

### ② [최초 1회 필수] 클린 DB 마이그레이션 및 공간 Join 적재
```bash
cd backend
# 1. 읍면동 경계 및 지적 데이터 벌크 적재 & PostGIS Spatial Join 고속 갱신 (10초 완공)
venv\Scripts\python app\scripts\clean_and_organize_datasets.py

# 2. 의사결정 이력 클린 테이블 생성 (더미 시드 없음)
venv\Scripts\python app\scripts\create_decision_histories_table.py

# 3. XGBoost 일반화 최적 규격 초기 학습
venv\Scripts\python app\scripts\train_css_model.py
```

### ③ 백엔드 API 서버 로컬 직접 구동
```bash
cd backend
venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### ④ 프론트엔드 Next.js 개발 서버 로컬 구동
```bash
cd frontend
npm run dev
```
*(브라우저에서 `http://localhost:3000` 으로 접속하여 즉시 테스트 가능)*
