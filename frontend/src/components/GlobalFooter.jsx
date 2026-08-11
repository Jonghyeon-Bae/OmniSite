'use client';
import React, { useState } from 'react';

export default function GlobalFooter() {
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [activeTab, setActiveTab] = useState('terms'); // 'terms', 'ai_disclaimer', 'data_sources', 'audit_log'

  const openModalWithTab = (tab) => {
    setActiveTab(tab);
    setShowTermsModal(true);
  };

  return (
    <>
      <footer className="w-full bg-slate-900/90 backdrop-blur-md border-t border-slate-800 text-slate-400 text-xs py-6 px-4 md:px-8 mt-auto z-30">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          {/* 좌측: 프로그램명 & 버전을 명확히 표출 */}
          <div className="flex flex-col gap-1 text-center md:text-left">
            <div className="flex items-center gap-2 justify-center md:justify-start flex-wrap">
              <span className="font-bold text-slate-200 text-sm tracking-wide">
                OmniSite SDSS
              </span>
              <span className="bg-indigo-900/80 text-indigo-300 text-[10px] font-semibold px-2 py-0.5 rounded border border-indigo-700/50">
                v1.0.0-Production / Root.B
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-300">지자체 공공 공간의사결정지원 시스템</span>
            </div>
            <p className="text-slate-500 text-[11px]">
              시스템 제공자: <strong className="text-slate-300">KT Aivle 9기 2반 4조</strong> &nbsp;|&nbsp; 
              사업자 및 대표 연락처: <strong className="text-slate-300">KT Aivle 9기 2반 4조 / 배종현</strong>
            </p>
          </div>

          {/* 우측: 이용약관 & 고지사항 팝업 및 저작권 */}
          <div className="flex flex-col items-center md:items-end gap-1.5 text-center md:text-right">
            <div className="flex items-center gap-2.5 flex-wrap justify-center md:justify-end text-[11px]">
              <button
                onClick={() => openModalWithTab('terms')}
                className="text-slate-300 hover:text-indigo-400 underline underline-offset-2 transition-colors font-medium cursor-pointer"
              >
                📜 B2G 서비스 이용약관
              </button>
              <span className="text-slate-600">|</span>
              <button
                onClick={() => openModalWithTab('ai_disclaimer')}
                className="text-amber-400/90 hover:text-amber-300 underline underline-offset-2 transition-colors font-medium cursor-pointer"
              >
                ⚠️ AI 면책 고지
              </button>
              <span className="text-slate-600">|</span>
              <button
                onClick={() => openModalWithTab('data_sources')}
                className="text-slate-300 hover:text-indigo-400 underline underline-offset-2 transition-colors font-medium cursor-pointer"
              >
                🗺️ 데이터 출처
              </button>
              <span className="text-slate-600">|</span>
              <button
                onClick={() => openModalWithTab('audit_log')}
                className="text-emerald-400/90 hover:text-emerald-300 underline underline-offset-2 transition-colors font-medium cursor-pointer"
              >
                🛡️ 감사 원장
              </button>
            </div>
            <p className="text-slate-500 text-[11px] flex items-center gap-1.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>개인식별정보(PII) 미수집 B2G 행정 전용 플랫폼</span>
              <span>&nbsp;© 2026 OmniSite SDSS. All Rights Reserved.</span>
            </p>
          </div>
        </div>
      </footer>

      {/* 엔터프라이즈급 상세 법적 고지 통합 모달 */}
      {showTermsModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl w-full p-6 text-slate-200 shadow-2xl flex flex-col h-[88vh]">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
              <div className="flex items-center gap-2.5">
                <h3 className="text-lg font-bold text-indigo-400 flex items-center gap-2">
                  🏛️ OmniSite SDSS B2G 행정 준법 명세서 및 약관
                </h3>
                <span className="bg-emerald-950 text-emerald-300 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/40">
                  개인식별정보(PII) 미수집 안전 플랫폼
                </span>
              </div>
              <button
                onClick={() => setShowTermsModal(false)}
                className="text-slate-400 hover:text-white text-xl font-bold px-2 cursor-pointer transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-800 mb-3 gap-1 overflow-x-auto pb-1 text-xs font-sans">
              <button
                onClick={() => setActiveTab('terms')}
                className={`px-4 py-2 rounded-t-xl font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'terms'
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>📜</span>
                <span>B2G 서비스 이용약관 (10개 조항)</span>
              </button>
              <button
                onClick={() => setActiveTab('ai_disclaimer')}
                className={`px-4 py-2 rounded-t-xl font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'ai_disclaimer'
                    ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/30'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>⚠️</span>
                <span>AI 시뮬레이션 면책고지 (7개 조항)</span>
              </button>
              <button
                onClick={() => setActiveTab('data_sources')}
                className={`px-4 py-2 rounded-t-xl font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'data_sources'
                    ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/30'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>🗺️</span>
                <span>공공 데이터 출처 (6개 조항)</span>
              </button>
              <button
                onClick={() => setActiveTab('audit_log')}
                className={`px-4 py-2 rounded-t-xl font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'audit_log'
                    ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>🛡️</span>
                <span>SHA-256 감사원장 (5개 조항)</span>
              </button>
            </div>

            {/* Modal Body Content */}
            <div className="overflow-y-auto space-y-4 text-xs leading-relaxed text-slate-300 pr-3 flex-1 custom-scrollbar">
              {/* Tab 1: Terms of Service (10 Articles) */}
              {activeTab === 'terms' && (
                <div className="space-y-3 font-sans">
                  <div className="bg-blue-950/60 p-3.5 rounded-xl border border-blue-500/40 text-blue-200 text-[11px] leading-relaxed">
                    💡 <strong>[개인식별정보(PII) 미수집 보장]</strong> 본 시스템은 주민등록번호, 전화번호, 생년월일, 금융정보 등 개인식별정보를 일체 수집·저장·처리하지 않습니다. 오직 관할 자치구 공무원 및 심의위원의 행정 세션 식별자(`session_id`)와 공간 지적도 데이터(PNU)만을 다루는 순수 B2G 행정 결정 지원 시스템입니다.
                  </div>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제1조 (목적)</h4>
                    <p className="text-slate-300">
                      본 약관은 KT Aivle 9기 2반 4조(대표자: 배종현)가 제공하는 지능형 다목적 스마트시티 입지 선정 및 공공갈등 예측 플랫폼 『OmniSite SDSS v1.0.0-Production』의 서비스 이용 조건, 권리·의무, 세션 파티션 관리 및 행정 처결 절차를 상세히 규정함을 목적으로 합니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제2조 (용어의 정의)</h4>
                    <ul className="list-disc pl-4 space-y-1 text-slate-300">
                      <li><strong>SDSS (Spatial Decision Support System):</strong> 공간 빅데이터 및 GIS 기반 입지 분석 및 의사결정을 지원하는 행정 시스템.</li>
                      <li><strong>PNU (Parcel Number Code):</strong> 대한민국 필지별 19자리 고유 지적 식별 번호.</li>
                      <li><strong>AHP (Analytic Hierarchy Process):</strong> 계층화 분석법을 통한 다기준 가중치 산출 알고리즘.</li>
                      <li><strong>CSS (Conflict Sensitivity Score):</strong> XGBoost 머신러닝 기반 주민 갈등 민감도 예측 벡터.</li>
                      <li><strong>ISI (Impact Stability Index):</strong> AHP 수용성과 CSS 감점을 통합 연산한 Closed-Loop 적격도 점수.</li>
                      <li><strong>HITL (Human-In-The-Loop):</strong> AI 감리 결과를 인간 공무원이 최종 검수·승인하는 세이프가드 프로토콜.</li>
                    </ul>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제3조 (약관의 효력 및 개정)</h4>
                    <p className="text-slate-300">
                      1. 본 약관은 이용자가 시스템에 접속하여 행정 심의 세션을 가동함과 동시에 효력이 발생합니다.  
                      2. 행정 법령 개정 또는 지자체 조례 변경에 따라 약관이 개정될 수 있으며, 개정 사항은 시스템 하단 공지사항을 통해 사전 고지됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제4조 (세션 관리 및 동시성 파티션)</h4>
                    <p className="text-slate-300">
                      1. 본 시스템은 단일 세션 강제 튕김 락을 배제하고, 사용자 Key(`session_id`) 기반의 세션 파티션 체인(`Per-Session State Channel`)을 제공합니다.  
                      2. 다수의 공무원 및 심의위원이 동시에 접속하더라도 상호 간 간섭 없이 100% 병렬 처리가 보장됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제5조 (이용자의 의무 및 금지행위)</h4>
                    <p className="text-slate-300">
                      이용자는 시스템 구동 중 다음 각 호의 행위를 하여서는 안 됩니다.  
                      가. 백엔드 REST API에 대한 불법적 역공학(Reverse Engineering) 및 크래킹 행위  
                      나. 공간 데이터베이스(`cadastral_lands`)에 대한 위·변조 SQL 주입(SQL Injection) 행위  
                      다. 세션 감사 원장(`pipeline_execution_logs`)을 고의로 무단 멸실 또는 조작하려는 행위
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제6조 (서비스 제공 및 인프라 표준)</h4>
                    <p className="text-slate-300">
                      시스템은 연중무휴 24시간 제공을 원칙으로 하며, AWS Lightsail 프로덕션 도커 및 Uvicorn 멀티 프로세스(`--workers 4`) 환경에서 안정적으로 유지됩니다. 정기 점검 시 사전 고지 후 점검이 집행될 수 있습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제7조 (지적재산권 및 행정 자산의 귀속)</h4>
                    <p className="text-slate-300">
                      1. 시스템의 알고리즘 소스코드, ERD 스키마 설계서, 5각 레이더 매트릭스 UI 컴포넌트의 지적재산권은 개발팀(KT Aivle 9기 2반 4조)에 있습니다.  
                      2. 심의를 통해 최종 생성된 공문서 PDF/Word 결재 보고서 및 구정 의결 산출물의 소유권은 해당 관할 지자체에 귀속됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제8조 (관리자 콘솔 및 보안 인가)</h4>
                    <p className="text-slate-300">
                      관리자 콘솔(`/admin`) 내 조례 태그 갱신 및 마스터 복구 기능은 동적 마스터 보안 인증 코드를 통과한 최고 행정 관리자에 한해 승인됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제9조 (손해배상 및 분쟁 해결)</h4>
                    <p className="text-slate-300">
                      시스템 이용 중 발생하는 행정 해석상의 분쟁은 관할 지자체 심의위원회 규정 및 대한민국 관련 법령에 따라 해결합니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-indigo-300 text-sm">제10조 (소프트웨어 라이선스 명시)</h4>
                    <p className="text-slate-300">
                      본 시스템은 Next.js (MIT), FastAPI (MIT), PostgreSQL/PostGIS (PostgreSQL License), XGBoost (Apache 2.0) 오픈소스 라이선스 규정을 준수합니다.
                    </p>
                  </section>
                </div>
              )}

              {/* Tab 2: AI Disclaimer (7 Articles) */}
              {activeTab === 'ai_disclaimer' && (
                <div className="space-y-3 font-sans">
                  <div className="bg-amber-950/60 p-3.5 rounded-xl border border-amber-500/40 text-amber-200 text-[11px] leading-relaxed">
                    ⚠️ <strong>[AI 예측 및 시뮬레이션 보조 성격 고지]</strong> 본 플랫폼이 구동하는 머신러닝(XGBoost) 갈등 수치, 미래 변동 스트레스 테스트 및 3자 생성형 AI(LLM) 모의 심의 토론 결과는 행정 의사결정을 돕기 위한 **확률론적 시뮬레이션 자문 지표**입니다.
                  </div>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제1조 (행정 당국의 최종 결재권 보장)</h4>
                    <p className="text-slate-300">
                      AI 입지 추천 점수(ISI) 및 가상 주민/전문가 모의 토론 결과는 법적 효력을 갖는 최종 행정 처분을 대신하지 아니하며, 최종 입지 확정 및 조례 지정의 법적 의결 권한은 관할 자치구 행정위원회 및 지자체장에 있습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제2조 (확률론적 오차 및 스트레스 테스트 수시 변동)</h4>
                    <p className="text-slate-300">
                      미래 변동 스트레스 테스트(Optimal / Normal / Worst 3가지 시나리오) 및 안정 변동성 지수(Robustness Index)는 입력 조건 변동 시 실시간 가변되는 과학적 시뮬레이션 수치로서, 미래 발생 가능한 100% 절대적 결과를 보장하지 않습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제3조 (인간 개입 의무화 Protocol - HITL Guard)</h4>
                    <p className="text-slate-300">
                      1단계 조례 AI 감리 요약 및 추천지 리스트에 대해 담당 공무원은 2차 정밀 실측 검수(Human-In-The-Loop)를 집행해야 하며, AI의 독립적 판단으로 인한 결과가 자동 집행되지 않도록 차단 조치되어 있습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제4조 (AI 생성형 모의 토론 환각 방지)</h4>
                    <p className="text-slate-300">
                      LangGraph 기반 GPT-4o / EXAONE 3자 토론 모델은 오직 RAG 지식베이스에 적재된 공문서 및 법정 조례 원문만을 인용하도록 시드 격리되어 있으며, 환각(Hallucination) 방지를 위해 면책 뱃지가 상시 바인딩됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제5조 (주민 갈등 예측의 한계)</h4>
                    <p className="text-slate-300">
                      XGBoost 갈등 민감도($CSS$)는 과거 민원 발생 패턴과 소상공인 상가 밀집도 통계를 기반으로 계산되므로, 통계 외적인 돌발 집단 집회나 사회적 이슈는 반영되지 않을 수 있습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제6조 (조례 검색 개정 시차 면책)</h4>
                    <p className="text-slate-300">
                      pgvector 코사인 유사도 기반 조례 임베딩 RAG 검색 결과는 최신 공공 고시문 시딩 시점 기준이며, 고시 후 당일 변경된 지자체 조례의 실시간 개정 시차에 대한 확인 의무는 이용자에 있습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-amber-300 text-sm">제7조 (손해배상 책임의 배제)</h4>
                    <p className="text-slate-300">
                      AI 시뮬레이션 추천 지표를 행정 참고 자료로 인용하는 과정에서 발생한 행정적·재정적 판단에 대하여 고의 또는 중과실이 없는 한 개발 플랫폼은 손해배상 책임을 지지 않습니다.
                    </p>
                  </section>
                </div>
              )}

              {/* Tab 3: Data Sources (6 Articles) */}
              {activeTab === 'data_sources' && (
                <div className="space-y-3 font-sans">
                  <div className="bg-sky-950/60 p-3.5 rounded-xl border border-sky-500/40 text-sky-200 text-[11px] leading-relaxed">
                    🗺️ <strong>[공공 공간 데이터 출처 및 저작권 명시]</strong> OmniSite SDSS는 대한민국 국토교통부 국가공간정보포털(NSIC) 및 서울시 용산구 공공데이터포털 19종 정품 데이터셋을 기반으로 무편향 공간 연산을 수행합니다.
                  </div>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-sky-300 text-sm">제1조 (수집 19종 정품 공간 데이터셋 목록)</h4>
                    <ul className="list-disc pl-4 space-y-1 text-slate-300">
                      <li><strong>연속지적도 (cadastral_lands):</strong> 용산구 관할 6,524개 필지 경계 및 PNU 지번 속성</li>
                      <li><strong>상가 업소 데이터 (commercial_shops):</strong> 소상공인진흥공단 6,509개 상가업소 위치 및 업종 분류</li>
                      <li><strong>법정 제한구역 (restricted_zones):</strong> 용산구 268개 문화재, 교량, 터널, 하천, 금연구역 SHP</li>
                      <li><strong>대중교통 네트워크 (transit_stations):</strong> 서울시 버스정류소 및 지하철역 10m 규제 버퍼</li>
                      <li><strong>교육 및 보육 정화구역:</strong> 유치원/초중고 200m 절대 보호구역 및 어린이집 50m 버퍼</li>
                    </ul>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-sky-300 text-sm">제2조 (공공데이터 이용 허락 라이선스)</h4>
                    <p className="text-slate-300">
                      본 시스템이 활용하는 공공데이터는 「공공데이터의 제공 및 이용 활성화에 관한 법률」 및 공공누리(KOGL) 제1유형(출처표시 조건 자유 이용) 규정을 준수합니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-sky-300 text-sm">제3조 (지도 엔진 및 타일 서빙 저작권)</h4>
                    <p className="text-slate-300">
                      2D/3D 지도 렌더링은 OpenStreetMap(OSM) 타일 서버 및 Leaflet.js 오픈소스 타일 클라이언트를 사용하며, 지오코딩 및 로드뷰 기능은 카카오맵 REST API 사용 약관에 따라 연동됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-sky-300 text-sm">제4조 (PostGIS geography 실측 연산 무결성)</h4>
                    <p className="text-slate-300">
                      거리 연산 시 도(Degree) 단위 환산 오차를 배제하기 위해 PostGIS `geography` 미터 단위 공간 연산(`ST_DWithin`)을 주입하여 0.000m의 수치적 무결성을 유지합니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-sky-300 text-sm">제5조 (국유재산 및 토지 소유구분 갱신)</h4>
                    <p className="text-slate-300">
                      기재부 국유부동산 정보와 매칭하여 468개 지적 필지의 소유구분('국유지', '시유지', '구유지', '사유지')을 100% 갱신 관리합니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-sky-300 text-sm">제6조 (무단 전재 및 제3자 전송 제한)</h4>
                    <p className="text-slate-300">
                      본 시스템에서 가공·제공되는 통합 공간 빅데이터는 행정 전용 목적 외에 제3자에게 상업적으로 무단 재배포할 수 없습니다.
                    </p>
                  </section>
                </div>
              )}

              {/* Tab 4: Audit Log (5 Articles) */}
              {activeTab === 'audit_log' && (
                <div className="space-y-3 font-sans">
                  <div className="bg-emerald-950/60 p-3.5 rounded-xl border border-emerald-500/40 text-emerald-200 text-[11px] leading-relaxed">
                    🛡️ <strong>[SHA-256 행정 감사 원장 기록 및 투명성 고지]</strong> 행정 처결의 투명성과 책임성을 입증하기 위해 이용자의 1~5단계 모든 심의 조작 이력은 SHA-256 해시 체인으로 불변(Immutable) 기록됩니다.
                  </div>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-emerald-300 text-sm">제1조 (감사 원장 자동 이력 적재)</h4>
                    <p className="text-slate-300">
                      1단계 AI 감리 승인, 2단계 ML 재학습, 4단계 AHP 가중치 락, 5단계 최종 의결 등 모든 조작 이력은 `pipeline_execution_logs` DB 테이블에 SHA-256 암호화 해시로 자동 적재됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-emerald-300 text-sm">제2조 (세션 파티션 해시 체이닝)</h4>
                    <p className="text-slate-300">
                      단일 DB 체인 경쟁으로 인한 병목을 방지하기 위해 사용자 Key(`session_id`) 기반의 세션 파티션 해시 체인(`Per-Session State Channel`)을 제공하여 체인 꼬임 현상을 0%로 차단합니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-emerald-300 text-sm">제3조 (위·변조 감지 및 보안 사고 탐지)</h4>
                    <p className="text-slate-300">
                      감사 원장에 대해 0.001초 단위로 이전 해시(`prev_hash`)와 현재 해시(`current_hash`)를 대조하여 멸실 또는 위·변조 시 백엔드 `STEP_SECURITY_INCIDENT` 에러가 즉시 트리거됩니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-emerald-300 text-sm">제4조 (행정 감사 제출용 렌더링 무결성)</h4>
                    <p className="text-slate-300">
                      기록된 해시 체인은 대시보드 감사 원장 검증 모달 및 공문서 결재 보고서에 1:1로 렌더링되어 법적 감사 시 완벽한 증빙자료로 인출될 수 있습니다.
                    </p>
                  </section>

                  <section className="bg-slate-800/70 p-4 rounded-xl border border-slate-700/60 space-y-1">
                    <h4 className="font-bold text-emerald-300 text-sm">제5조 (마스터 키 기반 세이프가드 프로토콜)</h4>
                    <p className="text-slate-300">
                      감사 원장 멸실 등 비상 상황 발생 시 동적 마스터 보안 키 인증을 거친 최고 보안 승인자 프로토콜을 통해서만 원장 재동기화 및 치유(Re-healing)가 집행됩니다.
                    </p>
                  </section>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between font-sans">
              <span className="text-[11px] text-slate-500">
                제공자: KT Aivle 9기 2반 4조 (대표: 배종현) &nbsp;|&nbsp; 문의: 지자체 SDSS 인프라 구축팀
              </span>
              <button
                onClick={() => setShowTermsModal(false)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-6 py-2 rounded-xl transition-all cursor-pointer shadow-lg shadow-indigo-600/30"
              >
                확인 및 닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
