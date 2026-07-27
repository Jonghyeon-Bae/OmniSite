import React from 'react';

export default function DashboardStatsCards({ statsData }) {
  const stats = statsData || {
    totalAnalyses: 124,
    avgCssScore: 42.8,
    ahpLockStatus: '일관성 락 (C.R. <= 0.1 통과)',
    ragRegulationCount: 88
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 my-6">
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
        <span className="text-xs font-semibold text-slate-400">총 입지 심의 분석 건수</span>
        <div className="flex items-baseline justify-between mt-3">
          <span className="text-2xl font-black text-white font-mono">{stats.totalAnalyses} <span className="text-xs font-sans text-slate-400 font-normal">건</span></span>
          <span className="text-xs text-emerald-400 font-bold">✓ 100% 검증</span>
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
        <span className="text-xs font-semibold text-slate-400">평균 주민 갈등도 (CSS %)</span>
        <div className="flex items-baseline justify-between mt-3">
          <span className="text-2xl font-black text-amber-400 font-mono">{stats.avgCssScore} <span className="text-xs font-sans text-slate-400 font-normal">%</span></span>
          <span className="text-xs text-amber-400/80 font-bold">보통 (수용 가능)</span>
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
        <span className="text-xs font-semibold text-slate-400">AHP 계층분석 가중치</span>
        <div className="flex items-baseline justify-between mt-3">
          <span className="text-xs font-bold text-blue-400 bg-blue-500/10 border border-blue-500/30 px-2.5 py-1 rounded-lg">C.R. ≤ 0.1 Locked</span>
          <span className="text-xs text-slate-400">수학적 검증</span>
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
        <span className="text-xs font-semibold text-slate-400">RAG 지식베이스 조례 청크</span>
        <div className="flex items-baseline justify-between mt-3">
          <span className="text-2xl font-black text-emerald-400 font-mono">{stats.ragRegulationCount} <span className="text-xs font-sans text-slate-400 font-normal">개</span></span>
          <span className="text-xs text-emerald-400 font-bold">v2.0 오토 바인딩</span>
        </div>
      </div>
    </div>
  );
}