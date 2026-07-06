# 📋 조례 목록 조회, 중복 검증 및 삭제 기능 구현 계획서 (v2.3.0)

본 계획서는 등록된 조례(법규) 파일들의 목록 조회뿐만 아니라, **중복 업로드 예방 및 적재된 조례의 개별 삭제(물리 삭제 및 캐시 정리) 기능**을 아키텍처에 추가 반영한 UI/UX 개선안입니다.

---

## 1. 🔍 설계 변경 및 기능 개선 요약

### 1.1. 중복 업로드 예방 조치 (Duplication Guard)
- **백엔드 업로드 검증**:
  - `POST /api/v1/upload/regulation` 진입 시, 업로드 타겟 파일명이 `UPLOAD_DIR` 내에 이미 물리적으로 존재하는지 스캔합니다.
  - 중복 파일이 존재할 경우 파일 쓰기를 중단하고 `400 Bad Request` 에러(`"이미 등록된 법규 파일입니다: [파일명]"`)를 반환합니다.
- **프론트엔드 피드백**:
  - 중복 업로드 오류 발생 시 경고 창(`alert`)을 띄워 사용자에게 중복 사실을 고지하고, 비정상 상태 유입을 방지합니다.

### 1.2. 법규 개별 삭제 기능 구현 (Deletion Flow)
- **백엔드 삭제 API 구현 (`DELETE /api/v1/upload/regulations/{filename}`)**:
  - 지정된 파일명의 원본 파일(PDF)을 서버 내 원천 저장소(`data/raw`)에서 즉각 삭제합니다.
  - 동시에, 해당 PDF에서 추출하여 보관 중이던 캐시 텍스트 파일(`[filename].txt`) 또한 함께 깔끔하게 수거하여 저장소 용량을 보존합니다.
- **프론트엔드 조례 목록 내 삭제(🗑️) 단추 배치**:
  - `📋 등록된 조례 목록` 모달 내부에 나열된 파일 우측에 휴지통 아이콘(또는 `삭제` 버튼)을 배치합니다.
  - 삭제를 진행할 때 사용자에게 재확인 모달(`confirm`)을 띄우고, 승인 시 백엔드 삭제 API를 호출하여 즉시 반영합니다. 삭제가 성공하면 목록을 새로고침합니다.

### 1.3. 글로벌 네비게이션 헤더 개편 및 연동
- 상단 헤더에 **"📋 조례 목록 조회"** 단추를 신설하여 독립 모달(`showRegulationListModal`)을 제어합니다.
- `RAG 데이터베이스 관리` 모달에서 PDF 업로드가 끝난 시점에도 목록을 즉시 갱신할 수 있도록 리스너를 바인딩합니다.
- 지도의 Leaflet 렌더링 로직(동결 영역)은 절대 훼손하지 않습니다.

---

## 2. Proposed Changes

### 💻 백엔드 컴포넌트 (`backend/app/routers/upload.py`)

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)
1. **중복 검증 로직 추가 (`POST /upload/regulation`)**:
   - `saved_path = os.path.join(UPLOAD_DIR, filename)` 검사 시 `os.path.exists(saved_path)` 분기를 넣어 중복 시 `HTTPException(400)` 처리.
2. **삭제 API 신설 (`DELETE /upload/regulations/{filename}`)**:
   - 원천 PDF 파일 삭제 및 `file_path + ".txt"` 캐시 텍스트 파일 동시 수거 로직 작성.

---

### 🎨 프론트엔드 컴포넌트 (`frontend/src/app/page.js`)

#### [MODIFY] [page.js](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/frontend/src/app/page.js)
1. **React State 추가**:
   - `showRegulationListModal` (`boolean`), `regulationList` (`array`) 상태 신설.
2. **비동기 목록 조회 및 삭제 함수 구현**:
   - `fetchRegulations()`: `GET /api/v1/upload/regulations` 연동.
   - `handleDeleteRegulation(filename)`: `DELETE /api/v1/upload/regulations/{filename}` 연동 후 `fetchRegulations()` 연쇄 갱신.
3. **글로벌 헤더 버튼 및 모달 팝업 추가**:
   - 헤더 우측 영역에 `📋 조례 목록 조회` 버튼을 삽입합니다.
   - 목록 모달 내에 각 조례 아이템 우측에 `🗑️` 삭제 버튼을 배치하고 이벤트 핸들러를 래핑합니다.
   - 목록이 비어 있는 예외 상태에 대해 대응 처리합니다.

---

## 3. Verification Plan

### Automated Tests
- `scratch/e2e_test.py` 스크립트를 보강하여 중복 업로드 거부 테스트와 개별 조례 삭제 API 테스트 케이스를 가동하고 **200 OK** 및 **400 Bad Request**가 정의된 대로 리턴되는지 검증합니다.

### Manual Verification
1. 브라우저에서 동일한 PDF 파일을 다시 업로드할 때, 에러 알림창이 표출되며 적재가 차단되는지 확인.
2. 조례 목록 모달을 열고 특정 파일 옆의 `🗑️` 아이콘 클릭 시 컨펌 창이 뜨고, 삭제 승인 시 목록에서 해당 파일이 제거되는지 확인.
