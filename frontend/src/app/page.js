'use client';

import React from 'react';
import Link from 'next/link';

export default function GatewayPage() {
  return (
    <div className="relative min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 font-sans px-6 overflow-hidden">
      
      {/* Sleek Abstract Background Gradients */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      
      {/* Outer Border Frame to match Premium Aesthetics */}
      <div className="absolute inset-4 border border-slate-900 pointer-events-none rounded-2xl" />
      
      {/* Main Glass Panel Card */}
      <div className="glass-panel w-full max-w-lg p-8 rounded-2xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-md flex flex-col items-center gap-6 text-center shadow-2xl relative z-10">
        
        {/* Platform Badge */}
        <span className="text-[10px] bg-blue-500/15 border border-blue-500/30 text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider">
          OmniSite 행정 통합 게이트웨이
        </span>

        {/* Title */}
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-white">스마트도시 입지선정지원시스템</h1>
          <p className="text-xs text-slate-400 leading-relaxed">
            도시행정망 실무자 전용 공간지리 정보 분석 및 의사결정 시뮬레이터(SDSS) 포털
          </p>
        </div>

        {/* Informative Grid */}
        <div className="w-full border-t border-b border-slate-800/60 py-5 my-2 flex flex-col gap-3 text-left">
          <div className="flex gap-3 items-start">
            <span className="text-blue-400 text-sm">🔒</span>
            <div className="flex flex-col gap-0.5">
              <span className="text-xs font-semibold text-slate-200">실무자 로그인 인증 체계 도입 예정</span>
              <span className="text-[10px] text-slate-500">인증 2차 모듈 연동 시, 자치구별 행정 ID 권한 검증 및 세션 관리가 적용됩니다.</span>
            </div>
          </div>
          
          <div className="flex gap-3 items-start">
            <span className="text-blue-400 text-sm">🏛️</span>
            <div className="flex flex-col gap-0.5">
              <span className="text-xs font-semibold text-slate-200">B2G 전용 공간 분석 엔진</span>
              <span className="text-[10px] text-slate-500">용산구 관내 국유재산 11,359필지 및 법규 RAG DB 교차 시맨틱 감리가 지원됩니다.</span>
            </div>
          </div>
        </div>

        {/* Action Button - Portal Access */}
        <Link 
          href="/spatial"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs py-3 rounded-xl transition-all shadow-lg hover:shadow-blue-500/10 cursor-pointer flex items-center justify-center gap-2"
        >
          <span>🚀 입지 분석 포털 즉시 접속 (Map)</span>
        </Link>
        
        {/* Footer info */}
        <span className="text-[9px] text-slate-600 font-mono">
          OmniSite SDSS v1.0.0-prototype | Secure Internal Network Only
        </span>

      </div>
    </div>
  );
}
