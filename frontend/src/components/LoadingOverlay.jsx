import React from 'react';

export default function LoadingOverlay({ isUploading, isRecommending }) {
  if (!isUploading && !isRecommending) return null;

  return (
    <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-md z-[9999] flex flex-col items-center justify-center gap-4 transition-all">
      <div className="relative w-20 h-20">
        {/* 외부 회전 링 */}
        <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-blue-400/30 border-b-blue-300/10 border-l-blue-400/20 animate-spin" />
        {/* 내부 역회전 링 */}
        <div className="absolute inset-2 rounded-full border-4 border-t-amber-500 border-l-amber-400/30 border-b-amber-300/10 border-r-amber-400/20 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        {/* 중앙 코어 */}
        <div className="absolute inset-5 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-full shadow-inner animate-pulse" />
      </div>
      <div className="flex flex-col items-center gap-1.5 mt-2 text-center">
        <span className="text-sm font-bold tracking-wider text-white uppercase animate-pulse">
          {isUploading ? 'AI Ingestion & Semantic Auditing' : 'Optimal Site Spatial Ingress'}
        </span>
        <span className="text-[11px] text-slate-400 font-mono">
          {isUploading ? '조례 RAG 데이터베이스 교차 대칭 검증 및 도메인 규칙 판독 중...' : 'PostGIS 공간 차집합 연산 및 AHP 가중합 댐핑 스케일러 연산 중...'}
        </span>
      </div>
    </div>
  );
}
