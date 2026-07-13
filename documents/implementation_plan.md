# [공간 데이터 캐시 수명주기 정합 및 재커밋 예외 완치 계획서]

조장님이 감리 도중 발견하신 현상은 극도로 크리티컬한 상태 전이 결함입니다. 
분석 결과, 백엔드 `upload.py` 의 `/upload/hitl/commit` API가 실행 완료 시점에 **임시 업로드된 원본 CSV 파일들을 `os.remove` 로 영구 제거**해 버리는 것이 문제의 근원이었습니다.

이 때문에 0개 예외가 발생하거나 실무자가 좌표를 미세하게 재조정하기 위해 Step 2 로 복귀하여 두 번째 커밋을 호출할 시, 원본 파일 소실로 인해 **"404 업로드된 파일을 찾을 수 없습니다"** 라는 치명적인 런타임 예외가 발생했습니다.

이를 완치하기 위해, **커밋 시 원본 CSV 파일을 삭제하지 않고 캐시 상태를 보존**하며, 해당 파일의 물리 삭제는 사용자가 명시적으로 처음부터 재시작하는 **`/upload/clear` (플랫폼 초기화) API 기동 시점에만 실행되도록 생명주기를 정합 조율**합니다.

---

## 🛠️ 1. HITL CSV 보존 및 삭제 수명주기 이관 (Zero Cost)

*   **백엔드 `/upload/hitl/commit` 내 파일 삭제 로직 제거:**
    - `upload.py` 에서 커밋 성공 후 `committed_files` 내부의 CSV 원본들을 삭제하는 `os.remove` 루프를 안전하게 Prune(삭제) 및 주석 격리 처리합니다.
*   **효과:** 사용자가 Step 2 로 복귀하여 몇 번을 튜닝하고 보정 커밋을 날리더라도, `uploads` 디렉터리 내에 CSV 파일이 온전하게 유지되어 무오류로 연산이 즉각 재기동됩니다.
*   **파일 수명 종료 청소:** 전체 초기화 시점인 `/upload/clear` 호출 시에는 `uploads` 내의 `.csv`, `.json` 이 전량 자동 삭제되므로 불필요한 좀비 파일이 누적되지 않고 안전 청소됩니다.

---

## User Review Required

> [!IMPORTANT]
> - **보행 쾌적성 300m 검색 및 미터 시각화 유지:**
>   - 최대 스캔 한계 반경을 도보 접근 임계인 **300m (`search_radius = 0.003` 도)** 로 타이트하게 고정하고, 지수 거리 감쇠 상수도 150m (`exp(-d/150)`) 로 유지합니다.
>   - 실제 조례 반경(학교 200m 등)을 1:1 실크기(Meter)로 정합 드로잉하는 상태도 완벽 유지합니다.

## Proposed Changes

---

### [Backend API Layer]

#### [MODIFY] [upload.py](file:///c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/backend/app/routers/upload.py)
- **`commit_hitl_data` 의 CSV 물리 삭제 루프 주석 격리:**
  - 1224~1229라인의 다음 삭제 로직을 비활성화합니다.
    ```python
    # [v4.9.21 핫픽스] 0개 예외 및 Step 2 복귀 재보정 커밋을 다회 가능하도록 원본 CSV 물리 삭제 임시 유예
    # for cf in committed_files:
    #     try:
    #         os.remove(os.path.join(UPLOAD_DIR, cf))
    #     except Exception as e:
    #         print(f"[Cleanup Error] Failed to remove committed file {cf}: {e}")
    ```

## Verification Plan

### Automated Tests
- `ahp_spatial_test.py` E2E 테스트 시나리오 ALL PASS 검증 유지.
- 테스트 시나리오에 다회 커밋 시뮬레이션을 추가 확인.
