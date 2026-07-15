# OmniSite 지능형 다목적 SDSS 종합 연구노트 & 주니어 개발자 연대기 교본 (v1.1-stable)

본 문서는 B2G 스마트시티 다기준 의사결정 지원 시스템(SDSS) **OmniSite**의 탄생(0.1 기획)부터 최종 프로덕션 안정화 버전(**v1.1-stable**)에 도달하기까지의 전체 아키텍처 진화 과정, 데이터베이스 스크립트 설계, GIS 공간 연산의 기하학적 난제 극복, 그리고 현업 인프라 이식 시 필요한 환경 튜닝을 백과사전식으로 편찬한 **주니어 엔지니어링 가이드 및 연구노트**입니다.

---

## 🏛️ 제 1 장. 시스템 기본 구조와 엔지니어링 철학

OmniSite는 공공 입지 선정 시 필연적으로 마주하는 두 가지 핵심 난제인 **'공간적 정합성(GIS 이격/규제)'**과 **'행정적 리스크(주민 NIMBY 갈등)'**를 기술적으로 해결하기 위해 설계된 플랫폼입니다.

### 1.1. Monolithic 통합 파이프라인
데이터 파편화와 네트워크 호출 비용을 최소화하기 위해 **Python FastAPI Monolith** 방식을 고수합니다. 
*   **이점:** Next.js 브라우저 단에서 단 한 번의 파일 업로드를 수행하면, 데이터 감리, DB 이관, PostGIS 추천, AHP 가중합 연산, OpenAI GPT-4o 기반 LangGraph 찬반 모의 토론 및 SSE 스트리밍이 동일 백엔드 메모리 컨텍스트에서 막힘없이 실행됩니다.
*   **주의 사항:** 주니어 개발자는 API 포트를 외부에 무작위 노출하지 않고, 반드시 후술할 Nginx 리버스 프록시 뒤로 격리 은닉하여 배포해야 합니다.

### 1.2. 개방-폐쇄 원칙(OCP)과 Zero-Hardcoding
시스템 전반에 하드코딩된 도메인 분기문(예: `if facility_type == 'smoking_zone'`)을 완전히 걷어내고, 데이터베이스 메타데이터(`registered_domain_tags`)와 정규식 파서를 기반으로 설계했습니다.
*   **지명 정규 표현식 파서:**
    ```javascript
    const addressPattern = /([가-힣]+(?:특별시|광역시|특별자치시|도|특별자치도))\s+([가-힣]+(?:구|군|시))\s+([가-힣0-9·]+(?:동|읍|면|리))/;
    ```
    대한민국 지번 정보가 유입될 때 복잡한 지명 DB 공간 쿼리나 행정구역 매핑 딕셔너리 없이 **O(1)의 속도로 시·도 및 시·군·구, 행정동을 안전하게 격리 파싱**합니다.

---

## 📅 제 2 장. 백과사전식 연구개발 연대기 (0.1 ~ v1.1-stable)

### 📌 Phase 1. 기초 수집 및 1차 구상 단계 ([0701] ~ [0.1] 감리 단계)
*   **마일스톤:** 용산구 19종 공공데이터셋 구축 및 학교 보호구역 200m, 버스정류장 10m 등 차집합 PostGIS 공간 연산 PoC 확립.
*   **핵심 해결:** 사용자가 원천 데이터를 가공 없이 업로드할 때 하자가 기하학적으로 전이되는 현상을 막기 위해, 데이터 업로드 즉시 표준 컬럼 스키마와 위경도 경계선을 전수 조사하는 **AI 데이터 감리(Step 2 HITL)** 메커니즘을 최초 설계하였습니다.

### 📌 Phase 2. 모의 시뮬레이션 및 데이터 오염 차단 ([0.2] ~ [0.4] 아키텍처 다각화)
*   **마일스톤:** LangGraph 기반 3자(찬성/반대/정정) 가상 모의 토론 도입.
*   **핵심 해결 (Model Collapse 방지):** AI가 모의 심의 과정에서 생성한 가상의 주민 토론 텍스트가 RAG(Retrieval-Augmented Generation) 지식베이스로 무방비 유입될 시, 실제 조례와 가상 데이터가 혼재되어 RAG의 신뢰성이 붕괴하는 문제를 발굴하였습니다.
    *   **조치:** 토론 데이터 생성 시 실시간 DB 적재를 원천 배제하고, `backend/data/debates/` 디렉터리 아래에 `debate_{pnu}_{intensity}.json` 형태의 **로컬 파일 시스템 캐시 구조로 완전히 물리 격리 적재**하도록 구현해 RAG 벡터 풀 오염을 차단했습니다.

### 📌 Phase 3. GIS 맵핑 오차 및 스크립트 중복 크래시 해결 (Rev 1 ~ Rev 8)
*   **Leaflet Y축 마우스 클릭 64px 편차 버그:** 브라우저 인라인 스타일 `padding-top`에 의해 Leaflet 지도 캔버스의 내부 좌표가 픽셀 단위로 왜곡되던 문제를 스타일 구조 정리로 완치.
*   **동적 스크립트 로더 싱글톤화:** 사용자 스텝 전환 시 브라우저 내에서 Leaflet `<script>` 태그를 반복 로딩해 `window.L` 전역 상태가 충돌하고 브라우저 탭이 강제 셧다운되던 심각한 문제를 해소. `useEffect` 진입 시 마운트 1회만 비동기 감지하는 구조로 변경하여 메모리 릭(Leak) 박멸.
*   **60fps 핀 드래그 감도 최적화 (DOM Thrashing 방지):**
    *   **원인:** 마커를 마우스로 드래그할 때 실시간 규제 영역 침범 여부를 판단하기 위해 매 프레임(60fps)마다 `marker.setIcon()`이 트리거되어 DOM 트리가 파괴/재생성되면서 웹 브라우저 전체가 정지하는 병목 발생.
    *   **해결:** 마커 내부 상태를 캐싱하는 `marker.isWarning` 상태 플래그를 삽입. **안전 구역 ➔ 위험 구역으로 상태가 '변화(Toggle)'하는 단 1회에만 setIcon이 호출**되도록 분기 처리하여 핀 드래그 렉을 0%로 하향시킴.

### 📌 Phase 4. pgvector RAG 컴파일 에러 및 루프백 hang up 극복 (Rev 9 ~ Rev 22)
*   **pgvector 파라미터 타입 불일치 (`vector <=> double precision[]`):**
    *   **원인:** FastAPI에서 OpenAI 임베딩 API가 반환한 `float` 배열을 SQL 쿼리에 그대로 바인딩하자 PostgreSQL pgvector 라이브러리가 명시적 타입 변환 실패로 500 내부 서버 에러를 출력.
    *   **해결:** 비교 대상 파라미터에 명시적 타입 캐스팅(`CAST(:query_embedding AS vector)`)을 적용하여 psycopg3 커넥터 환경 하에서 SyntaxError를 완전히 소거.
*   **Next.js Proxy Server hang up 및 무한 재귀 호출:**
    *   **원인:** Next.js 개발 프록시 단에서 POST JSON 데이터를 백엔드로 보낼 때 내부 스트림 중복 소모로 `ECONNRESET` 소켓 단절이 발생. 이를 우회하기 위해 `window.fetch` 전역 변수명을 모듈 스코프에서 그대로 덮어쓰자 전역 호출이 무한 재귀에 빠져 브라우저 CPU 점유율이 100%에 달하는 장해 발생.
    *   **해결:** 전역 fetch 덮어쓰기를 롤백하고, 모듈 격리 스코프의 독자적인 `apiFetch` 래퍼 헬퍼 함수를 구현하여 Next.js 프록시 우회 및 무한 루프 사슬을 끊음.

### 📌 Phase 5. PostGIS 300m/200m 거리 정밀도 및 지리 형태학적 종횡비 가드 (Rev 23 ~ Rev 39)
*   **Bounding Box 오프셋 튜닝 (`ST_Expand`):** 
    *   공간 쿼리 성능을 높이기 위해 R-Tree 공간 인덱스(GIST)가 우선 가동되도록 경계 박스 오프셋을 기존 0.005도에서 `0.003도` (200m) 단위로 축소하여 쿼리 레이턴시를 0.1초 미만으로 단축.
*   **지리 형태학적 종횡비 가드 (Morphological Aspect Ratio Guard):**
    *   국유지 면적 제한(`ST_Area > 800`)만 통과하면 기차역 철로변, 터널 보도 등 폭 0.5m의 비정상적 협소 보도가 최적지로 무더기 추천되는 지리 데이터 결함 발생.
    *   **해결:** 후보지 다각형의 가로세로 바운딩 비율인 종횡비가 **`8.0` 이상**인 극단적 형상의 도로/선로 부지는 공간 추천 엔진에서 강제 누락(`ST_Envelope` 비율 분석 처리)하는 필터 탑재 완료.

### 📌 Phase 6. 관리자 콘솔, ESRI Shapefile 적재, 최초 로그인 비밀번호 강제 변경 및 PDF 보고서 제로 하드코딩 (Rev 55 ~ Rev 62)
*   **마일스톤:** B2G 보안 규격에 부합하는 JWT 세션 통제, 최고관리자 전용 CRUD 계정 발급, ESRI Shapefile 백엔드 파싱 자동 적재 및 자치구별 PDF 명의 제로 하드코딩 완전 해결.
*   **핵심 해결:**
    *   **공용 공간 Shapefile 파이프라인:** `.shp`, `.dbf`, `.shx` 파일 묶음을 `pyshp`로 열고 지오메트리를 파싱한 뒤 X좌표의 범위를 분석해 좌표계(WGS84, 중부원점, UTM-K)를 판독해 `ST_Transform` 후 PostGIS 다각형 객체로 적재하는 자동 SRID 검출 파이프라인 완성.
    *   **최초 로그인 패스워드 리셋 의무화:** `seed_db.py`에 자동 삽입되는 기본 어드민 계정(`admin`/`admin1234`) 또는 무작위 시딩 계정에 대해 최초 로그인 시 `require_password_change` 플래그를 내려보내, 비밀번호 강제 변경 모달을 통해 변경을 완료할 때까지 플랫폼 제어 권한을 엄격히 차단함.
    *   **기관 보고서 발송처 제로 하드코딩:** 결과 PDF 발급 시 기존 용산구청장으로 고정되어 있던 하드코딩 명의를 로그인된 공무원의 실제 소속 자치구 `district_id`와 연계 조회하여, 발신 명의자 및 보고서 종합 고시 안내문 내 자치구명을 실시간 치환 렌더링하고 `(직인생략)` 서명을 자동 인자하도록 완치함.

---

## 🛠️ 제 3 장. 주니어 엔지니어를 위한 핵심 트러블슈팅 및 가이드라인 (Best Practices)

### 3.1. [React] Leaflet 지도 컴포넌트의 수명 주기(Lifecycle) 제어
리액트는 가상 DOM을 이용해 화면을 다시 그리지만, Leaflet이나 OpenLayers 같은 공간 맵 라이브러리는 브라우저의 실제 DOM에 직접 캔버스를 주입합니다. 따라서 리액트 상태가 바뀔 때 지도가 겹쳐 렌더링되거나 인스턴스가 좀비 프로세스로 메모리에 상주하지 않도록 명시적으로 제거(Clean-up)해 주어야 합니다.

*   **주니어 가이드 모범 예시:**
```javascript
import { useEffect, useRef } from 'react';

export default function MapComponent() {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // 1. 지도 초기화 및 싱글톤 인스턴스 할당
    const map = L.map(mapContainerRef.current, {
      center: [37.53, 126.97],
      zoom: 14,
      zoomControl: true
    });
    
    mapInstanceRef.current = map;

    // 2. 컴포넌트 언마운트 시점에 명시적으로 DOM 리소스를 릴리즈
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  return <div id="map-container" ref={mapContainerRef} style={{ height: '500px' }} />;
}
```

### 3.2. [PostGIS] 구면 기하 거리 계측과 geography 형변환
PostgreSQL 내에서 위경도(EPSG:4326)를 그대로 사용해 `ST_Distance(g1, g2)`를 연산하면 미터가 아닌 각도 단위(degree)를 반환하며, 이는 위도가 높아질수록 동서 거리가 급격히 좁아지는 왜곡을 야기합니다.
*   **수학적 해결책:** 반드시 피처들을 `::geography` 타입으로 캐스팅하여 WGS84 구면 회전 타원체 기준으로 거리가 **미터(meters)** 단위로 계산되도록 강제하십시오.

```sql
-- [경고] 평면 각도 연산으로 오차 유발
-- SELECT id FROM cadastral_lands WHERE ST_Distance(geom, :ref_geom) < 0.002;

-- [권장] 300m 구면 실제거리 완벽 필터링 (GIST 인덱스 정상 가동)
SELECT id, jibun
FROM cadastral_lands
WHERE ST_DWithin(geom::geography, ST_GeomFromText('POINT(126.97 37.53)', 4326)::geography, 300.0);
```

---

## 💾 제 4 장. 상용 배포 환경과 스왑 메모리 튜닝 (Production System)

서버리스(Vercel, Render 등) 배포는 Cold Start와 네트워크 전송 레이턴시가 파편화되어 B2G GIS 시스템 기동에 부적합합니다. 이에 따라 단일 AWS Lightsail 인스턴스(1vCPU / 2GB RAM / 월 $10 플랜)에 Docker Compose를 통합 가동하는 물리 배포 아키텍처를 적용합니다.

### 4.1. Swap Space 설정의 필수성
*   **OOM Killer 현상:** 2GB RAM 환경에서 PostgreSQL GIS 팽창 연산 및 Next.js SSR 빌드가 동시에 돌 때 메모리가 100%에 달하면 리눅스 커널이 시스템 셧다운을 방지하기 위해 컨테이너 프로세스를 강제 종료(`exit code 137`)시킵니다.
*   **해결:** 하드디스크의 일부 공간을 스왑 파일로 4GB 확보하여 물리 메모리가 넘칠 경우 디스크 공간으로 스위칭(Swap-out)함으로써 서비스 가동성을 99.9% 안전하게 방어합니다. (스왑 4GB 할당 상세 터미널 스크립트는 `deployment_plan.md`를 즉시 참조하십시오.)
