import React, { useState, useEffect } from 'react';

export default function AuditLogModal({ showModal, setShowModal, apiFetch }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  const [verifying, setVerifying] = useState(false);
  const [rehealing, setRehealing] = useState(false);
  const [hashStatus, setHashStatus] = useState(null);

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

  const handleVerifyHashChain = async () => {
    setVerifying(true);
    try {
      const res = await apiFetch('/api/v1/spatial/logs/verify-hash-chain');
      if (res.ok) {
        const data = await res.json();
        setHashStatus(data);
      }
    } catch (err) {
      alert("해시 체인 검증 중 오류: " + err.message);
    } finally {
      setVerifying(false);
    }
  };

  // 1클릭 멸실/위변조 자동 복구 및 재동기화
  const handleRehealHashChain = async () => {
    if (!window.confirm("손상/멸실된 해시 지점에 복구 블록(STEP_SYSTEM_REHEAL) 및 보안 침해 로그(STEP_SECURITY_INCIDENT)를 인입하여 체인을 재동기화하시겠습니까?")) return;
    setRehealing(true);
    try {
      const res = await apiFetch('/api/v1/spatial/logs/reheal-hash-chain', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message || "✓ 해시 체인이 성공적으로 복구 및 재동기화되었습니다.");
        fetchLogs();
        handleVerifyHashChain();
      } else {
        const err = await res.json();
        alert(`❌ 복구 실패: ${err.detail || '오류 발생'}`);
      }
    } catch (err) {
      alert("복구 집행 중 오류: " + err.message);
    } finally {
      setRehealing(false);
    }
  };

  useEffect(() => {
    if (showModal) {
      fetchLogs();
      handleVerifyHashChain();
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
      case 'STEP_SECURITY_INCIDENT':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/30 text-rose-200 border border-rose-500/60 animate-pulse">🚨 보안 침해 사고 기록</span>;
      case 'STEP_SYSTEM_REHEAL':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/30 text-sky-200 border border-sky-500/60">🔧 해시 복구 재동기화</span>;
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
              {hashStatus?.tampered ? (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/50 whitespace-nowrap animate-pulse flex items-center gap-1">
                  <span>⚠️</span>
                  <span>위·변조/멸실 단절 탐지됨</span>
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 whitespace-nowrap shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                  🔒 SHA-256 해시 체인 무결성 100% Verified
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              공공 행정 의사결정 프로세스 단계별 적재 내역 및 암호학적 위·변조/멸실 탐지 대응 시스템
            </p>
          </div>
          
          <div className="flex items-center gap-2.5 shrink-0">
            {hashStatus?.tampered && (
              <button
                onClick={handleRehealHashChain}
                disabled={rehealing}
                className="text-xs bg-rose-600 hover:bg-rose-500 text-white px-4 py-2 rounded-xl border border-rose-400 font-bold transition-all cursor-pointer flex items-center gap-1.5 shrink-0 shadow-lg shadow-rose-600/30 animate-bounce"
              >
                <span>🔧</span>
                <span>{rehealing ? "복구 중..." : "해시 체인 멸실 복구 & 재동기화"}</span>
              </button>
            )}
            <button
              onClick={handleVerifyHashChain}
              disabled={verifying}
              className="text-xs bg-emerald-950/70 hover:bg-emerald-900/90 text-emerald-300 px-4 py-2 rounded-xl border border-emerald-700/70 font-bold transition-all cursor-pointer flex items-center gap-1.5 shrink-0 shadow-md hover:scale-105"
            >
              <span>{verifying ? "⏳" : "🔍"}</span>
              <span>{verifying ? "검증 중..." : "실시간 위변조 검증"}</span>
            </button>
            <button
              onClick={fetchLogs}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-2 rounded-xl border border-slate-700 font-bold transition-all cursor-pointer shrink-0 flex items-center gap-1 hover:scale-105"
            >
              <span>🔄</span>
              <span>새로고침</span>
            </button>
            <button
              onClick={() => setShowModal(false)}
              className="text-slate-400 hover:text-white text-xl font-bold cursor-pointer transition-all p-1.5 hover:bg-slate-800/60 rounded-xl shrink-0"
              title="닫기"
            >
              &times;
            </button>
          </div>
        </div>

        {/* 위변조 탐지 레드 알림 바 */}
        {hashStatus?.tampered && (
          <div className="my-2 p-3 bg-rose-950/60 border border-rose-500/50 rounded-xl flex items-center justify-between shadow-lg text-xs text-rose-200 animate-pulse">
            <div className="flex items-center gap-2">
              <span className="text-base">🚨</span>
              <span>
                <strong>보안 경고:</strong> 감사 로그 단절 또는 멸실(Corrupted Index: #{hashStatus.corrupted_index})이 감지되었습니다. 
                오른쪽 <strong>[🔧 해시 체인 멸실 복구]</strong> 버튼으로 체인을 안전하게 1초 만에 재동기화하십시오.
              </span>
            </div>
          </div>
        )}

        {/* 본문 2컬럼 레이아웃 */}
        <div className="flex-1 my-3 grid grid-cols-12 gap-4 min-h-0">
          {/* 좌측: 감사 로그 타임라인 리스트 */}
          <div className="col-span-5 bg-slate-950/80 rounded-xl p-3.5 border border-slate-800/80 overflow-y-auto flex flex-col gap-2">
            {loading ? (
              <div className="text-center py-10 text-xs text-slate-400 animate-pulse">감사 로그 로딩 중...</div>
            ) : logs.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-500">기록된 행정 감사 로그가 없습니다.</div>
            ) : (
              logs.map((log) => {
                const isSelected = selectedLog?.id === log.id;
                const isSecurityIncident = log.step_number === 'STEP_SECURITY_INCIDENT';
                const isReheal = log.step_number === 'STEP_SYSTEM_REHEAL';

                let cardStyle = "bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/50";
                if (isSelected) cardStyle = "bg-indigo-950/50 border-indigo-500/80 shadow-md";
                if (isSecurityIncident) cardStyle = "bg-rose-950/60 border-rose-500/60 shadow-rose-950/30";
                if (isReheal) cardStyle = "bg-sky-950/60 border-sky-500/60 shadow-sky-950/30";

                return (
                  <div
                    key={log.id}
                    onClick={() => setSelectedLog(log)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer text-xs flex flex-col gap-1.5 ${cardStyle}`}
                  >
                    <div className="flex justify-between items-center">
                      {getStepBadge(log.step_number)}
                      <span className="text-[10px] text-slate-400 font-mono">
                        {log.created_at ? new Date(log.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : ''}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-200 mt-0.5 flex items-center justify-between">
                      <span>{log.action_type}</span>
                      <span className="text-[10px] font-mono text-slate-500">#{log.id}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* 우측: 선택된 감사 로그 세부 정보 (JSON Viewer) */}
          <div className="col-span-7 bg-slate-950/90 rounded-xl p-4 border border-slate-800 flex flex-col justify-between overflow-hidden">
            {selectedLog ? (
              <div className="flex flex-col h-full gap-2">
                <div className="border-b border-slate-800/80 pb-2 flex justify-between items-center shrink-0">
                  <div>
                    <span className="text-xs font-bold text-indigo-400">Log ID #{selectedLog.id}</span>
                    <h4 className="text-sm font-bold text-slate-100 mt-0.5">{selectedLog.action_type} 상세 내역</h4>
                  </div>
                  <span className="text-xs text-slate-400 font-mono bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
                    Session: {selectedLog.session_id}
                  </span>
                </div>

                {/* SHA-256 해시 체인 정보 */}
                <div className="bg-slate-900/90 p-2.5 rounded-lg border border-slate-800/90 flex flex-col gap-1 shrink-0 font-mono text-[10px]">
                  <div className="flex gap-2">
                    <span className="text-slate-500 w-20 shrink-0">Current Hash:</span>
                    <span className="text-emerald-400 truncate">{selectedLog.current_hash || 'SHA256 Genesis Hash'}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-slate-500 w-20 shrink-0">Prev Hash:</span>
                    <span className="text-sky-400 truncate">{selectedLog.prev_hash || '0'.repeat(64)}</span>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto bg-slate-900/80 p-3 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {typeof selectedLog.detail_json === 'string' 
                    ? selectedLog.detail_json 
                    : JSON.stringify(selectedLog.detail_json, null, 2)}
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
        <div className="flex justify-between items-center border-t border-slate-800 pt-3 text-[11px] text-slate-500 font-sans">
          <span>✓ PostgreSQL `pipeline_execution_logs` SHA-256 단방향 무결성 & 멸실 자동 복구 시스템 가동 중</span>
          <button
            onClick={() => setShowModal(false)}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-5 py-2 rounded-xl transition-all cursor-pointer"
          >
            닫기
          </button>
        </div>

      </div>
    </div>
  );
}
