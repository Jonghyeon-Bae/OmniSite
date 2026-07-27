import React from 'react';

export default function DashboardHistoryTable({ historyList, onSelectHistory, onDeleteHistory }) {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col gap-4">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span>📜 용산구 스마트 인프라 의사결정 심의 이력</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">PostgreSQL decision_histories 테이블 실시간 연동</p>
        </div>
        <span className="text-xs text-slate-400 font-mono">총 {(historyList || []).length} 건 조회됨</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
            <tr>
              <th className="p-3">ID</th>
              <th className="p-3">자치구 / 행정동</th>
              <th className="p-3">시설 유형</th>
              <th className="p-3">심의 상태</th>
              <th className="p-3">갈등도 (CSS)</th>
              <th className="p-3">심의 일자</th>
              <th className="p-3 text-right">작업</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {(historyList || []).length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-500 font-sans">
                  등록된 의사결정 심의 이력이 없습니다.
                </td>
              </tr>
            ) : (
              historyList.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/50 transition-all">
                  <td className="p-3 text-slate-400">#{item.id}</td>
                  <td className="p-3 font-sans font-medium text-white">{item.region || '용산구'}</td>
                  <td className="p-3 text-blue-400 font-semibold">{item.infra || item.facility_type}</td>
                  <td className="p-3">
                    <span className="bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 px-2 py-0.5 rounded-md text-[11px] font-sans font-bold">
                      {item.status || '토론 완료'}
                    </span>
                  </td>
                  <td className="p-3 text-amber-400 font-bold">{item.selected_parcel_css || 50}%</td>
                  <td className="p-3 text-slate-400 text-[11px]">{item.created_at?.slice(0, 10) || '2026-07-27'}</td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => onSelectHistory && onSelectHistory(item)}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg text-[11px] font-sans mr-2 cursor-pointer"
                    >
                      상세보기
                    </button>
                    {onDeleteHistory && (
                      <button
                        onClick={() => onDeleteHistory(item.id)}
                        className="bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 px-2 py-1 rounded-lg text-[11px] font-sans cursor-pointer"
                      >
                        삭제
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}