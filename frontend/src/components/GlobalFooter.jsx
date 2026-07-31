'use client';
import React, { useState } from 'react';

export default function GlobalFooter() {
  const [showTermsModal, setShowTermsModal] = useState(false);

  return (
    <>
      <footer className="w-full bg-slate-900/90 backdrop-blur-md border-t border-slate-800 text-slate-400 text-xs py-6 px-4 md:px-8 mt-auto z-30">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          {/* 좌측: 프로그램명 & 버전을 명확히 표출 */}
          <div className="flex flex-col gap-1 text-center md:text-left">
            <div className="flex items-center gap-2 justify-center md:justify-start">
              <span className="font-bold text-slate-200 text-sm tracking-wide">
                Omnisite SDSS
              </span>
              <span className="bg-indigo-900/80 text-indigo-300 text-[10px] font-semibold px-2 py-0.5 rounded border border-indigo-700/50">
                v1.5.0 / Root.B
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-300">지자체 공공 입지분석 지원 플랫폼</span>
            </div>
            <p className="text-slate-500 text-[11px]">
              시스템 제공자: <strong className="text-slate-300">KT Aivle 9기 2반 4조</strong> &nbsp;|&nbsp; 
              사업자 및 대표 연락처: <strong className="text-slate-300">KT Aivle 9기 2반 4조 / 배종현</strong>
            </p>
          </div>

          {/* 우측: 이용약관 모달 팝업 및 저작권 */}
          <div className="flex flex-col items-center md:items-end gap-1.5 text-center md:text-right">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowTermsModal(true)}
                className="text-slate-300 hover:text-indigo-400 underline underline-offset-2 transition-colors text-[11px] font-medium cursor-pointer"
              >
                서비스 이용약관
              </button>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400 text-[11px]">개인정보 수집 미해당 공공 플랫폼</span>
            </div>
            <p className="text-slate-500 text-[11px]">
              © 2026 OmniSite SDSS (KT Aivle 9기 2반 4조). All Rights Reserved.
            </p>
          </div>
        </div>
      </footer>

      {/* 서비스 이용약관 모달 */}
      {showTermsModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full p-6 text-slate-200 shadow-2xl flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between border-b border-slate-700 pb-3 mb-4">
              <h3 className="text-lg font-bold text-indigo-400 flex items-center gap-2">
                📜 OmniSite SDSS 서비스 이용약관
              </h3>
              <button
                onClick={() => setShowTermsModal(false)}
                className="text-slate-400 hover:text-white text-xl font-bold px-2 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 text-xs leading-relaxed text-slate-300 pr-2">
              <section className="bg-slate-800/60 p-3 rounded border border-slate-700/50">
                <h4 className="font-bold text-slate-100 mb-1 text-sm">제1조 (목적)</h4>
                <p>
                  본 약관은 KT Aivle 9기 2반 4조(대표자: 배종현)가 제공하는 지능형 다목적 스마트시티 입지 선정 및 공공갈등 예측 플랫폼 『Omnisite SDSS v1.5.0 / Root.B』의 서비스 이용 조건 및 절차를 규정함을 목적으로 합니다.
                </p>
              </section>

              <section className="bg-slate-800/60 p-3 rounded border border-slate-700/50">
                <h4 className="font-bold text-slate-100 mb-1 text-sm">제2조 (개인정보 수집 및 처리 고지)</h4>
                <p>
                  OmniSite SDSS 플랫폼은 공공 공간 지적도, 유동인구, 상가업소 및 지자체 법정 조례 분석을 전담하는 B2G 행정 의사결정 지원 시스템으로서, 일반 개인의 식별 가능한 개인정보(주민등록번호, 금융정보 등)를 일절 수집하거나 저장하지 않습니다.
                </p>
              </section>

              <section className="bg-slate-800/60 p-3 rounded border border-slate-700/50">
                <h4 className="font-bold text-slate-100 mb-1 text-sm">제3조 (서비스 책임의 한계 및 면책)</h4>
                <p>
                  본 플랫폼이 제공하는 5단계 입지 추천, 주민갈등도(CSS), 미래변동 스트레스 테스트(ISI 지수), 및 AI 모의 토론 결과는 과학적 수치 산출에 기반한 행정 참고용 지원 자료입니다. 최종 입지 승인 및 조례 지정의 법적 효력과 행정 집행 책임은 해당 지자체 당국에 있습니다.
                </p>
              </section>

              <section className="bg-slate-800/60 p-3 rounded border border-slate-700/50">
                <h4 className="font-bold text-slate-100 mb-1 text-sm">제4조 (시스템 제공자 정보 및 연락처)</h4>
                <ul className="list-disc pl-4 space-y-1 text-slate-300">
                  <li><strong>프로그램명</strong>: Omnisite SDSS v1.5.0 (Root.B)</li>
                  <li><strong>개발팀 / 제공자</strong>: KT Aivle 9기 2반 4조</li>
                  <li><strong>대표 문의 담당자</strong>: 배종현 (KT Aivle 9기 2반 4조)</li>
                  <li><strong>기술 문의</strong>: 지자체 공공 공간 데이터셋 추가 및 서버 구축 요청 지원</li>
                </ul>
              </section>
            </div>

            <div className="mt-5 pt-3 border-t border-slate-700 flex justify-end">
              <button
                onClick={() => setShowTermsModal(false)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-lg transition-colors cursor-pointer"
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
