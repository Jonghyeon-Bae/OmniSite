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

      {/* 서비스 이용약관 및 법적 고지 통합 모달 */}
      {showTermsModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full p-6 text-slate-200 shadow-2xl flex flex-col max-h-[85vh]">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-indigo-400">
                  🏛️ OmniSite SDSS B2G 행정 준법 및 법적 고지서
                </h3>
                <span className="bg-emerald-950 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-500/30">
                  개인정보 미수집 플랫폼
                </span>
              </div>
              <button
                onClick={() => setShowTermsModal(false)}
                className="text-slate-400 hover:text-white text-xl font-bold px-2 cursor-pointer transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Navigation Tabs */}
            <div className="flex border-b border-slate-800 mb-4 gap-1 overflow-x-auto pb-1 text-xs">
              <button
                onClick={() => setActiveTab('terms')}
                className={`px-3 py-2 rounded-t-lg font-bold transition-all cursor-pointer ${
                  activeTab === 'terms'
                    ? 'bg-indigo-600 text-white border-b-2 border-indigo-400'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                📜 B2G 서비스 이용약관
              </button>
              <button
                onClick={() => setActiveTab('ai_disclaimer')}
                className={`px-3 py-2 rounded-t-lg font-bold transition-all cursor-pointer ${
                  activeTab === 'ai_disclaimer'
                    ? 'bg-amber-600 text-white border-b-2 border-amber-400'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                ⚠️ AI 시뮬레이션 면책고지
              </button>
              <button
                onClick={() => setActiveTab('data_sources')}
                className={`px-3 py-2 rounded-t-lg font-bold transition-all cursor-pointer ${
                  activeTab === 'data_sources'
                    ? 'bg-sky-600 text-white border-b-2 border-sky-400'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                🗺️ 공간 데이터 출처
              </button>
              <button
                onClick={() => setActiveTab('audit_log')}
                className={`px-3 py-2 rounded-t-lg font-bold transition-all cursor-pointer ${
                  activeTab === 'audit_log'
                    ? 'bg-emerald-600 text-white border-b-2 border-emerald-400'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                🛡️ SHA-256 감사원장
              </button>
            </div>

            {/* Modal Body Content */}
            <div className="overflow-y-auto space-y-4 text-xs leading-relaxed text-slate-300 pr-2 flex-1">
              {/* Tab 1: Terms of Service */}
              {activeTab === 'terms' && (
                <div className="space-y-3">
                  <div className="bg-blue-950/40 p-3 rounded-xl border border-blue-500/30 text-blue-200 text-[11px] leading-normal">
                    💡 <strong>개인식별정보(PII) 미수집 고지:</strong> 본 시스템은 주민등록번호, 전화번호, 생년월일 등 개인식별정보를 일체 수집·저장하지 않으며, 오직 공무원/심의위원 세션 식별자(`session_id`)와 공간 필지 데이터(PNU)만을 다루는 순수 B2G 행정 결정 지원 시스템입니다.
                  </div>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-slate-100 mb-1 text-sm">제1조 (목적)</h4>
                    <p>
                      본 약관은 KT Aivle 9기 2반 4조(대표자: 배종현)가 제공하는 지능형 다목적 스마트시티 입지 선정 및 공공갈등 예측 플랫폼 『OmniSite SDSS v1.0.0-Production』의 서비스 이용 조건 및 행정 절차를 규정함을 목적으로 합니다.
                    </p>
                  </section>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-slate-100 mb-1 text-sm">제2조 (이용 권한 및 세션 관리)</h4>
                    <p>
                      본 시스템은 관할 자치구 구정 실무자, 행정 심의위원, 감사관의 승인된 세션에 한해 이용 가능하며, 세션 키(`session_id`)의 타인 양도 및 무단 전재를 금지합니다.
                    </p>
                  </section>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-slate-100 mb-1 text-sm">제3조 (행정 자산 귀속 및 데이터 관리)</h4>
                    <p>
                      본 시스템을 통해 생성된 입지 적격도 점수(ISI), 5각 입지 트레이드오프 레이더, AHP 가중치 모델 및 결재용 보고서(PDF/Word) 등 모든 행정 결과물의 소유권은 지자체 당국에 귀속됩니다.
                    </p>
                  </section>
                </div>
              )}

              {/* Tab 2: AI Disclaimer */}
              {activeTab === 'ai_disclaimer' && (
                <div className="space-y-3">
                  <div className="bg-amber-950/40 p-3 rounded-xl border border-amber-500/30 text-amber-200 text-[11px] leading-normal">
                    ⚠️ <strong>AI 예측 및 생성형 토론 보조적 성격 고지:</strong> 본 플랫폼이 제공하는 머신러닝(XGBoost) 입지 수치 및 3자 생성형 AI(LLM) 모의 심의 토론 결과는 행정 의사결정을 돕는 확률론적 시뮬레이션 지표입니다.
                  </div>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-amber-300 mb-1 text-sm">제1조 (최종 의결권의 행정 당국 귀속)</h4>
                    <p>
                      AI 입지 추천 점수 및 가상 모의 토론 내용은 최종 법적 효력을 갖는 행정 처분을 대신하지 아니하며, 최종 입지 확정 및 조례 지정의 법적 의결 권한은 관할 자치구 행정위원회 및 단체장에 있습니다.
                    </p>
                  </section>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-amber-300 mb-1 text-sm">제2조 (인간 개입 의무화 - HITL Protocol)</h4>
                    <p>
                      AI 감리 요약 및 추천 결과에 대하여 담당 공무원은 2차 정밀 검수(Human-In-The-Loop)를 집행해야 하며, AI의 확률적 오차로 인한 결과에 대해 플랫폼은 최종 법적 책임을 지지 않습니다.
                    </p>
                  </section>
                </div>
              )}

              {/* Tab 3: Data Sources */}
              {activeTab === 'data_sources' && (
                <div className="space-y-3">
                  <div className="bg-sky-950/40 p-3 rounded-xl border border-sky-500/30 text-sky-200 text-[11px] leading-normal">
                    🗺️ <strong>공공 공간 데이터 출처 명시:</strong> OmniSite SDSS는 국토교통부 국가공간정보포털(NSIC) 및 서울시 용산구 공공데이터포털 19종 정품 데이터셋을 기반으로 구동됩니다.
                  </div>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-sky-300 mb-1 text-sm">제1조 (주요 데이터셋 출처)</h4>
                    <ul className="list-disc pl-4 space-y-1 text-slate-300">
                      <li><strong>지적도 & 필지 속성:</strong> 국토교통부 연속지적도(PNU 6,524개 필지)</li>
                      <li><strong>대중교통 & 규제구역:</strong> 서울시 버스정류소/지하철역, 유치원/초중고 200m 정화구역</li>
                      <li><strong>상가 & 건물 데이터:</strong> 용산구 관할 소상공인 상가업소(6,509개) 및 건축물대장</li>
                    </ul>
                  </section>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-sky-300 mb-1 text-sm">제2조 (오픈소스 라이선스)</h4>
                    <p>
                      지도 렌더링 엔진은 OpenStreetMap(OSM) 및 Leaflet.js 오픈소스 라이선스와 카카오맵 API 이용 약관을 준수합니다.
                    </p>
                  </section>
                </div>
              )}

              {/* Tab 4: Audit Log */}
              {activeTab === 'audit_log' && (
                <div className="space-y-3">
                  <div className="bg-emerald-950/40 p-3 rounded-xl border border-emerald-500/30 text-emerald-200 text-[11px] leading-normal">
                    🛡️ <strong>SHA-256 행정 감사 원장 기록:</strong> 행정 처결의 투명성과 책임성을 보장하기 위해 이용자의 모든 주요 행위는 SHA-256 해시 체인으로 불변 기록됩니다.
                  </div>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-emerald-300 mb-1 text-sm">제1조 (감사 원장 이력 추적)</h4>
                    <p>
                      1단계 AI 감리 승인, 2단계 ML 재학습, 4단계 AHP 가중치 락, 5단계 최종 의결 등 모든 조작 이력은 `pipeline_execution_logs` DB 테이블에 SHA-256 암호화 해시로 영구 기록됩니다.
                    </p>
                  </section>
                  <section className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/50">
                    <h4 className="font-bold text-emerald-300 mb-1 text-sm">제2조 (무결성 자동 검증)</h4>
                    <p>
                      감사 원장은 세션별 파티션 체인을 형성하여 데이터의 무단 멸실, 수정, 위·변조 시 0.001초 내로 자동 감지 및 경보 시스템이 작동합니다.
                    </p>
                  </section>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
                제공자: KT Aivle 9기 2반 4조 (대표: 배종현)
              </span>
              <button
                onClick={() => setShowTermsModal(false)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-xl transition-colors cursor-pointer shadow-lg"
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
