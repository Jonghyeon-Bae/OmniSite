# AWS Lightsail 미래 배포 아키텍처 확정 및 주니어 인계 매뉴얼 계획서 (v1.2.0-alpha-Rev107)

본 계획은 조장(USER)의 직접 지시에 따라, 미래 배포 인프라를 AWS EKS(쿠버네티스)에서 가성비와 네트워크 요금 예측이 투명한 **AWS Lightsail 단일 인스턴스 정액제 배포**로 확정하여 종합 연구노트에 명문화하고, 알파테스트를 집행할 주니어 레벨 개발자들의 온보딩 삽질을 방지하기 위해 깃 주소 외에 추가로 공급해야 할 4대 핵심 인계 자산을 정의하기 위함입니다.

## User Review Required

> [!IMPORTANT]
> - **미래 배포 계획 Lightsail 확정 등재**:
>   - EKS 컨트롤 플레인의 고정비($72/월) 및 무제한 아웃바운드 트래픽 요금 폭탄 리스크를 예방하기 위해, 월 $10 고정 Lightsail 단일 인스턴스 사양 배포 아키텍처를 공식 미래 계획으로 종합 연구노트에 등재합니다.
> - **주니어용 4대 인계 자산 패키징 가이드**:
>   - **OpenAI API Key가 주입된 `.env`** 파일
>   - 깃에서 배제된 **`Datasets/` 폴더 원천 압축 팩** (`Datasets.zip`)
>   - 윈도우 원클릭 자동 런처 `start_omnisite_local.bat` 실행 유도
>   - RAG 검증 테스트용 **모의 고시 공문 PDF 샘플 파일**

## Proposed Changes

### Research Notebook Updates

#### [MODIFY] [스마트시티_SDSS_옴니사이트_종합_연구노트.md](file:///c:/Users/Admin/Desktop/빅프로젝트%20관련자료/스마트시티_SDSS_옴니사이트_종합_연구노트.md)
- 미래 계획 로드맵 섹션에 AWS Lightsail 비용 최적화 배포안을 확정 추가.

## Verification Plan

### Automated Tests
- Next.js 프로덕션 컴파일 빌드 검증을 가동하여 영향도가 없음을 입증합니다.

### Manual Verification
- 주니어 인계용 Datasets 폴더와 테스트 PDF가 물리 공간 내에 완전무결하게 존재하고 있는지 크로스 검수합니다.
