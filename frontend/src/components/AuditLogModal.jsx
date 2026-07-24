import React, { useState, useEffect } from 'react';

export default function AuditLogModal({ showModal, setShowModal, apiFetch }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/spatial/logs?limit=50');
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
        if (data.logs && data.logs.length > 0) {
          setSelectedLog(data.logs[0]);
        }
      }
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (showModal) {
      fetchLogs();
    }
  }, [showModal]);

  if (!showModal) return null;

  const getStepBadge = (step) => {
    switch (step) {
      case 'STEP_1':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">Step 1. AI 감리</span>;
      case 'STEP_2':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Step 2. HITL 보정</span>;
      case 'STEP_3':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">Step 3. AHP 락</span>;
      case 'STEP_4':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Step 4. ISI 추천</span>;
      case 'STEP_5':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Step 5. AI 심의</span>;
      case 'SYSTEM':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">보안/계정 액션</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-700 text-slate-300">{step}</span>;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-fade-in">
      <div className="glass-panel w-full max-w-[1000px] h-[680px] max-h-[90vh] p-6 flex flex-col justify-between rounded-2xl border border-slate-800 shadow-2xl">
        {/* 헤더 */}
        <div className="flex justify-between items-center border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <span>📜 옴니사이트 5단계 행정 감사 로그 (Audit Trail Logs)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              공공 행정 의사결정 프로세스 단계별 적재 내역 및 무결성 추적성 보장 이력
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchLogs}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition-all cursor-pointer"
            >
              🔄 새로고침
            </button>
            <button
              onClick={() => setShowModal(false)}
              className="text-slate-400 hover:text-white text-xl font-bold cursor-pointer transition-all p-1 hover:bg-slate-800/60 rounded-lg"
              title="닫기"
            >
              &times;
            </button>
          </div>
        </div>

        {/* 본문 2컬럼 레이아웃 */}
        <div className="flex-1 my-4 grid grid-cols-12 gap-4 min-h-0">
          {/* 좌측: 감사 로그 타임라인 리스트 */}
          <div className="col-span-5 bg-slate-950/80 rounded-xl p-3.5 border border-slate-800/80 overflow-y-auto flex flex-col gap-2">
            {loading ? (
              <div className="text-center py-10 text-xs text-slate-400 animate-pulse">감사 로그 로딩 중...</div>
            ) : logs.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-500">기록된 행정 감사 로그가 없습니다.</div>
            ) : (
              logs.map((log) => {
                const isSelected = selectedLog?.id === log.id;
                return (
                  <div
                    key={log.id}
                    onClick={() => setSelectedLog(log)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer text-xs flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-indigo-950/50 border-indigo-500/80 shadow-md'
                        : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      {getStepBadge(log.step_number)}
                      <span className="text-[10px] text-slate-400 font-mono">
                        {log.created_at ? new Date(log.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : ''}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-200 mt-0.5">
                      {log.action_type}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* 우측: 선택된 감사 로그 세부 정보 (JSON Viewer) */}
          <div className="col-span-7 bg-slate-950/90 rounded-xl p-4 border border-slate-800 flex flex-col justify-between overflow-hidden">
            {selectedLog ? (
              <div className="flex flex-col h-full">
                <div className="border-b border-slate-800/80 pb-3 mb-3 flex justify-between items-center">
                  <div>
                    <span className="text-xs font-bold text-indigo-400">Log ID #{selectedLog.id}</span>
                    <h4 className="text-sm font-bold text-slate-100 mt-0.5">{selectedLog.action_type} 상세 내역</h4>
                  </div>
                  <span className="text-xs text-slate-400 font-mono bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
                    Session: {selectedLog.session_id}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {JSON.stringify(selectedLog.detail_json, null, 2)}
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-xs text-slate-500">
                좌측 타임라인에서 로그 항목을 선택해 상세 내역을 조회하십시오.
              </div>
            )}
          </div>
        </div>

        {/* 하단 푸터 */}
        <div className="flex justify-between items-center border-t border-slate-800 pt-3 text-[11px] text-slate-500">
          <span>✓ PostgreSQL `pipeline_execution_logs` 행정 무결성 검증 완료</span>
          <button
            onClick={() => setShowModal(false)}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-4 py-2 rounded-lg transition-all cursor-pointer"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
