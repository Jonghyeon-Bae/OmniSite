# 다목적 도메인 시맨틱 추론 및 프론트엔드 연동 구현 계획서 (v1.2.0)

본 계획서는 OmniSite 플랫폼의 AI 감리 API(`/upload/audit`)가 대용량 공간 데이터(CSV)를 수신했을 때 발생하는 성능 오버헤드를 원천 차단하기 위해, **"내부 전체 데이터를 스캔하지 않고 파일 이름과 컬럼 헤더(컬럼명)만을 추출하여 AI 교차 추론에 공급하도록 최적화"**하는 개선안을 추가한 상세 엔지니어링 계획입니다.

---

## 1. 🔍 문제 진단 및 개선 방향

### 1.1. 기존 아키텍처의 한계
- 기존의 `/upload/audit` API는 업로드된 CSV에 대해 내부 `analyze_csv_data`를 호출하여 전체 `rows = list(reader)`를 메모리에 적재하고 루프를 돌며 위경도 범위 결측치를 세었습니다.
- 이는 수만~수십만 행의 행정 공간 데이터가 업로드되는 실무 환경에서 OOM(Out of Memory) 또는 API 타임아웃(504 Gateway Timeout)을 초래합니다.
- AI 시맨틱 감리는 도메인(목적)의 의도를 파악하는 것이 주 목적이므로, 데이터 내부 값 전체를 파싱할 이유가 전혀 없습니다.

### 1.2. 개선 방향 (경량 헤더 분석 구조)
- **경량 헤더 파서 도입**: CSV 파일의 첫 행(Header)만 스트리밍으로 읽어 들이고 즉시 스트림을 닫는 `parse_csv_header` 헬퍼 함수를 신규 도입합니다.
- **AI 감리 API 최적화**: 감리 API(`/upload/audit`)에서는 오직 **파일명**과 **컬럼 헤더 목록**만 취합해 OpenAI GPT-4o 프롬프트에 주입하여 도메인을 추론합니다.
- **역할 격리**: 결측치 정밀 검정 및 좌표 오차 매핑은 감리 단계가 아닌, Step 2의 시각화 및 최종 DB 적재 시점(`/upload/hitl/commit` 및 `/upload/geojson/{filename}`)에서 필요할 때만 지연 처리(Lazy Evaluation)하도록 아키텍처 역할을 격리합니다.

---

## 2. Proposed Changes (백엔드 / 프론트엔드 연동)

### 💻 백엔드 컴포넌트

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)
* **`parse_csv_header` 신규 추가**:
  ```python
  def parse_csv_header(file_path: str) -> List[str]:
      # 첫 줄만 읽고 즉시 파일 스트림 Close 처리
  ```
* **`/upload/audit` 성능 개선**:
  - `csv` 확장자 감지 시 `analyze_csv_data` 대신 `parse_csv_header`를 가볍게 호출.
  - GPT-4o에 전송되는 공간 데이터 정보 컨텍스트에 파일명과 컬럼 헤더 목록만 결합 주입.
  - 개별 파일 결과(`results`) 조립 시 `schema_errors` 및 `missing_coordinates` 탐색을 배제하고 컬럼 정합 판단만 선제 반환.
* **지연된 위경도 결측 검증**:
  - 실제 결측 좌표의 보정 검증은 사용자가 승인 처리하여 `/upload/geojson/{filename}`을 호출하거나 `/upload/hitl/commit`을 쏠 때 내부적으로 `analyze_csv_data`를 수행해 보정 결과를 DB에 안전하게 이관 적재하도록 구성합니다.

---

## 3. Verification Plan

### Automated Tests
* **FastAPI 백엔드 벤치마크 테스트**:
  - 대용량 가상 CSV 데이터(10만 행 이상)를 업로드하고 `/upload/audit` 호출 시 처리 속도가 100ms 미만으로 즉시 응답되는지 프로파일링 및 렉 유무 검증.
  - `/upload/hitl/commit` 호출 시에만 지연 분석을 거쳐 PostGIS에 롤백 제어와 함께 이관 적재되는지 최종 DB 스캔 확인.

### Manual Verification
- 브라우저 상에서 대용량 데이터를 일괄 업로드했을 때, AI 목적 추론 결과가 지연 없이 즉각적으로 화면에 팝업되는지 확인.
