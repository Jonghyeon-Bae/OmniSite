import React, { useState, useEffect } from 'react';

export default function AuditLogModal({ showModal, setShowModal, apiFetch }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      let res = null;
      if (typeof apiFetch === 'function') {
        try {
          res = await apiFetch('/api/v1/spatial/logs?limit=50');
        } catch (_) {}
      }

      // 2차 직통 우회 폴백 (Nginx/Next.js 500/404 오류 발생 시 공인 IP:8000 포트 직접 통신)
      if (!res || !res.ok) {
        if (typeof window !== 'undefined') {
          const host = window.location.hostname;
          const protocol = window.location.protocol;
          const envApiUrl = (process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_API_URL || '').replace(/\/$/, '');
          const directUrl = envApiUrl ? `${envApiUrl}/api/v1/spatial/logs?limit=50` : `${protocol}//${host}:8000/api/v1/spatial/logs?limit=50`;
          try {
            res = await fetch(directUrl);
          } catch (directErr) {
            console.error("Direct audit log fetch error:", directErr);
          }
        }
      }

      if (res && res.ok) {
        const data = await res.json();
        const rawLogs = data.logs || (Array.isArray(data) ? data : []);
        setLogs(rawLogs);
        if (rawLogs && rawLogs.length > 0) {
          setSelectedLog(rawLogs[0]);
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
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Step 2. ML 학습</span>;
      case 'STEP_3':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Step 3. HITL 보정</span>;
      case 'STEP_4':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">Step 4. AHP 락</span>;
      case 'STEP_5':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Step 5. AI 심의</span>;
      case 'STEP_6':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Step 6. 종합 보고서</span>;
      case 'SYSTEM':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">보안/계정 액션</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-700 text-slate-300">{step}</span>;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-fade-in font-sans">
      <div className="glass-panel w-full max-w-[1360px] h-[720px] max-h-[92vh] p-6 flex flex-col justify-between rounded-2xl border border-slate-800 shadow-2xl">
        
        {/* 헤더 */}
        <div className="flex justify-between items-center border-b border-slate-800 pb-4 gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h3 className="text-lg font-bold text-slate-100 whitespace-nowrap">📜 옴니사이트 5단계 행정 감사 로그 (Audit Trail Logs)</h3>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 whitespace-nowrap shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                🔒 행정 감사 로그 전용 이력 저장소 (Append-Only Ledger)
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              공공 행정 의사결정 프로세스 단계별 적재 내역 및 사용자 행동 이력 종합 관리 시스템
            </p>
          </div>
          
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl border border-slate-700 font-bold transition-all cursor-pointer flex items-center gap-1.5 shrink-0 shadow-md hover:scale-105"
            >
              <span>🔄</span>
              <span>{loading ? "조회 중..." : "새로고침"}</span>
            </button>
            <button
              onClick={() => setShowModal(false)}
              className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-all text-sm font-bold cursor-pointer border border-slate-700"
            >
              ✕
            </button>
          </div>
        </div>

        {/* 바디 레이아웃 (2열 구도: 이력 목록 + 상세 내역) */}
        <div className="grid grid-cols-12 gap-6 my-4 flex-1 min-h-0 overflow-hidden">
          
          {/* 좌측: 로그 타임라인 목록 (5컬럼) */}
          <div className="col-span-5 border border-slate-800/80 rounded-xl bg-slate-950/50 p-4 flex flex-col min-h-0 overflow-hidden">
            <div className="flex justify-between items-center mb-3 pb-2 border-b border-slate-800">
              <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                <span>📑</span>
                <span>최신 실행 감사 이력 ({logs.length}건)</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">최신순 정렬</span>
            </div>

            {loading ? (
              <div className="flex-1 flex items-center justify-center text-xs text-slate-400">
                <span className="animate-pulse">⏳ 감사 로그 데이터를 동기화하는 중...</span>
              </div>
            ) : logs.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
                적재된 감사 이력이 없습니다.
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                {logs.map((log) => {
                  const isSelected = selectedLog?.id === log.id;
                  const stepLabel = log.step_name || log.step_number || log.action_type || 'SYSTEM';
                  const detailsObj = log.details || log.detail_json || {};
                  return (
                    <div
                      key={log.id}
                      onClick={() => setSelectedLog({ ...log, step_name: stepLabel, details: detailsObj })}
                      className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-1.5 ${
                        isSelected 
                          ? 'bg-blue-600/15 border-blue-500/60 shadow-lg text-white' 
                          : 'bg-slate-900/40 hover:bg-slate-800/50 border-slate-800/80 text-slate-300'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold font-mono text-slate-200">Log #{log.id}</span>
                        {getStepBadge(stepLabel)}
                      </div>

                      <div className="flex justify-between items-center text-[11px] text-slate-400">
                        <span className="font-mono">{log.created_at ? new Date(log.created_at).toLocaleString('ko-KR') : '-'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 우측: 선택된 로그 상세 데이터 및 JSON 패널 (7컬럼) */}
          <div className="col-span-7 border border-slate-800/80 rounded-xl bg-slate-950/60 p-5 flex flex-col min-h-0 overflow-hidden">
            {selectedLog ? (
              <div className="flex flex-col h-full overflow-hidden gap-4">
                {/* 상단 썸네일 정보 */}
                <div className="flex justify-between items-center border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-mono font-bold text-sm">
                      #{selectedLog.id}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                        <span>단계 구분:</span>
                        {getStepBadge(selectedLog.step_name)}
                      </h4>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        기록 일시: {selectedLog.created_at ? new Date(selectedLog.created_at).toLocaleString('ko-KR') : '-'}
                      </p>
                    </div>
                  </div>


                </div>

                {/* JSON 세부 데이터 패널 */}
                <div className="flex-1 flex flex-col min-h-0">
                  <span className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                    <span>🔍</span>
                    <span>상세 실행 매개변수 & JSON 메타데이터</span>
                  </span>
                  <div className="flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-y-auto font-mono text-xs text-blue-300 leading-relaxed custom-scrollbar">
                    <pre className="whitespace-pre-wrap break-all">
                      {JSON.stringify(selectedLog.details || selectedLog.detail_json || {}, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
                <span className="text-2xl">📜</span>
                <span>좌측에서 조회할 감사 로그 항목을 선택해 주십시오.</span>
              </div>
            )}
          </div>

        </div>

        {/* 푸터 하단 상태 바 */}
        <div className="flex justify-between items-center pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>행정 감사 로그 수집 시스템 정상 가동 중 (Append-Only Ledger)</span>
          </span>
          <button
            onClick={() => setShowModal(false)}
            className="px-5 py-2 text-xs font-bold bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all cursor-pointer border border-slate-700"
          >
            닫기
          </button>
        </div>

      </div>
    </div>
  );
}
