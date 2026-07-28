# 🏛️ OmniSite 시스템 핵심 알고리즘 및 엔진 기술 스펙 가이드 (Technical Engine Guide)

본 문서는 스마트시티 공간 의사결정 지원 시스템(OmniSite SDSS)의 백엔드 분석 엔진, 머신러닝 모델, RAG 지식베이스, 감사 암호화 체인의 상세 기술 사양 및 수학적 공식을 체계적으로 보관하는 기술 전용 해설서입니다.

---

## 1. AHP 다기준 계층 분석 및 고유벡터(Eigenvector) 가중치 연산 엔진
* **수학적 모델**: 쌍대비교 행렬 $A = (a_{ij})_{n 	imes n}$에 대해 최고 고유치 $\lambda_{\max}$와 고유벡터 $w$를 산출합니다.
  $$A w = \lambda_{\max} w$$
* **일관성 비율(Consistency Ratio, C.R.) 검증**:
  $$C.I. = rac{\lambda_{\max} - n}{n - 1}, \quad C.R. = rac{C.I.}{R.I.}$$
  일관성 비율 $C.R. \le 0.1$ 만족 시에만 가중치가 락(Lock) 승인되어 공간 연산에 진입합니다.

---

## 2. XGBoost 머신러닝 주민갈등도(CSS) 및 Closed-Loop ISI 통합 공식
* **XGBoost Classifier**: 필지의 지목, 공시지가, 보호구역 이격거리 분포를 학습하여 잠재 민원 강도 $CSS \in [0, 100]$를 추론.
* **Closed-Loop ISI 통합 수용성 공식**:
  $$ISI = 	ext{Score}_{	ext{AHP}} 	imes \left(1.0 - 0.35 	imes \left(rac{CSS}{100}ight)^2ight)$$
  기본 AHP 입지 점수에 주민갈등 패널티(-0%~-35%)를 실시간 소급 감점하여 최종 입지를 확정합니다.

---

## 3. v2.5.0 파이프라인 5단계 무결성 검증 엔진 (`validate_step_integrity`)
* Step 1 AI 감리 ➔ Step 2 3D 작도 ➔ Step 3 AHP 락 ➔ Step 4 PostGIS/XGB 추천 ➔ Step 5/6 AI 심의의 선행 조건을 백엔드와 프론트엔드에서 이중 검증하여 이탈을 차단함.

---

## 4. v2.6.0 좁고 긴 골목길/선형 필지(폭 < 2.5m) 보행 장애 자동 감리
* 지적 Bounding Box 최소 폭 $W_{\min} < 2.5	ext{m}$ 또는 종횡비 $> 3.0$ 감지 시 `⚠️ [골목길 선형 필지 경고]` 태그 및 안전 보도폭(1.2m) 확보 위험 카드를 인출함.

---

## 5. v2.8.0 RAG pgvector 코사인 유사도(>=75%) 오토 체이닝 및 SHA-256 감사 체인
* OpenAI `text-embedding-3-small` (1,536차원) 코사인 유사도 연산으로 기존 조례 개정판(v2.0)을 자동 추적 적재함.
* 파이프라인 단계별 연산 결과 및 `step_validation` 메타데이터를 SHA-256 단방향 해시 체인으로 암호화 적재하여 실시간 위변조를 탐지함.
