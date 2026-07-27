import React from 'react';

export default function DashboardHeader({
  districtId,
  setDistrictId,
  tokenTimeLeft,
  isTokenValid,
  username,
  kstTimeStr,
  onOpenAuditLog,
  onOpenAdminConsole,
  onOpenPasswordChange,
  onLogout
}) {
  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between z-30 shrink-0 shadow-lg">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">📊</span>
          <h1 className="font-extrabold text-base tracking-tight text-white flex items-center gap-2">
            <span>OmniSite</span>
            <span className="text-[10px] bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 px-2 py-0.5 rounded-full font-mono">Executive Dashboard v2.3.2</span>
          </h1>
        </div>
        <div className="h-4 w-px bg-slate-800 mx-2" />
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">관할 자치구:</span>
          <select
            value={districtId || 1}
            onChange={(e) => setDistrictId && setDistrictId(Number(e.target.value))}
            className="bg-slate-800 text-slate-200 text-xs px-2.5 py-1 rounded-lg border border-slate-700 font-semibold focus:outline-none focus:border-blue-500"
          >
            <option value={1}>서울특별시 용산구</option>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
          <span>남은 세션: <strong className="text-amber-400">{tokenTimeLeft || '유효 세션'}</strong></span>
        </div>

        <div className="flex items-center gap-2 border-l border-slate-800 pl-4">
          <button
            onClick={onOpenAuditLog}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg font-semibold transition-all cursor-pointer flex items-center gap-1"
          >
            📜 행정 감사 로그
          </button>

          {onOpenAdminConsole && (
            <button
              onClick={onOpenAdminConsole}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer shadow-md shadow-blue-950/50 flex items-center gap-1"
            >
              ⚙️ 관리자 콘솔
            </button>
          )}

          <button
            onClick={onOpenPasswordChange}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1.5 rounded-lg font-medium transition-all cursor-pointer"
            title="비밀번호 변경"
          >
            🔑
          </button>

          <button
            onClick={onLogout}
            className="bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 px-3 py-1.5 rounded-lg font-semibold transition-all cursor-pointer"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>
  );
}