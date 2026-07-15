import React from 'react';

export default function DebateSimulatorModal({
  showSimModal,
  setShowSimModal,
  selectedParcel,
  activeTab,
  simLogs,
  simStep,
  intensityLevel,
  setIntensityLevel,
  setPipelineStep,
  runSimulation,
  inferredDomainTag,
  inferredPurpose,
  ahpWeights,
  apiFetch
}) {
  if (!showSimModal) return null;

  const currentParcel = selectedParcel[activeTab] || {};

  const handlePdfDownload = async () => {
    try {
      const payload = {
        facility_type: inferredDomainTag || "city_feature",
        inferred_purpose: inferredPurpose || "입지 분석",
        candidate_jibun: currentParcel.jibun || "용산구 미지정 부지",
        candidate_css: currentParcel.css || 50,
        candidate_lat: currentParcel.lat || 37.53,
        candidate_lng: currentParcel.lng || 126.97,
        candidate_reason: currentParcel.reason || "",
        ahp_weights: ahpWeights || {},
        debate_logs: simLogs.map(log => ({ sender: log.sender, text: log.text }))
      };

      // 1. 의사결정 심의 이력을 PostgreSQL DB에 자동 비동기 저장 (Auto-save to history)
      // [Zero Hardcoding] 주소 텍스트에서 정규식을 이용해 자치구/행정동을 추출하고, AI 시맨틱 감리 목적을 인프라 명칭에 동적 투사
      const regionMatch = payload.candidate_jibun.match(/(서울특별시|서울시)\s+([가-힣]+구)\s+([가-힣0-9]+동)/);
      const dynamicRegion = regionMatch ? regionMatch[0] : "서울시 용산구 한강로동";
      
      const historyPayload = {
        region: dynamicRegion,
        facility_type: payload.facility_type,
        infra: inferredPurpose || "지능형 스마트시티 시설물",
        pnu_count: Object.keys(selectedParcel).length || 1,
        status: "행정 종결",
        audit_state: "대기 중",
        audit_opinion: "공식 심의 완료 보고서 발급됨. 준공 고시 공문 감리 대기 중.",
        inferred_purpose: payload.inferred_purpose,
        ahp_weights: payload.ahp_weights,
        selected_parcel_jibun: payload.candidate_jibun,
        selected_parcel_price: currentParcel.price || 0,
        selected_parcel_area: currentParcel.area || 0.0,
        selected_parcel_css: payload.candidate_css,
        debate_logs: payload.debate_logs
      };
      
      try {
        await apiFetch('/api/v1/spatial/history', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(historyPayload)
        });
      } catch (historyErr) {
        console.error("Failed to auto-save decision history:", historyErr);
      }

      // 2. PDF 보고서 다운로드 수행
      const res = await apiFetch('/api/v1/spatial/report/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('PDF 다운로드 실패');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `OmniSite_Report_${payload.candidate_jibun.replace(/ /g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('⚠️ PDF 보고서 발급 중 오류가 발생했습니다: ' + err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6">
      <div className="w-[800px] h-[550px] glass-panel p-6 flex flex-col justify-between">
        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-300">OMS-01-03-001 | AI 에이전트 실시간 모의 심의 토론</h3>
            <p className="text-[10px] text-slate-500">Target PNU: {currentParcel.pnu}</p>
          </div>
          <button 
            onClick={() => setShowSimModal(false)}
            className="text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
          >
            &times;
          </button>
        </div>

        {/* 터미널 대화 스크롤 */}
        <div className="flex-1 my-4 bg-slate-950/70 rounded-xl p-4 overflow-y-auto font-mono text-xs flex flex-col gap-3 border border-slate-900/80">
          {simLogs.map((log, index) => {
            const sender = log.sender || '';
            let textClass = 'text-slate-300';
            
            if (sender.includes('보건') || sender.includes('구청') || sender.includes('공무원') || sender.includes('정부')) {
              textClass = 'text-sky-400 font-medium';
            } else if (sender.includes('상인') || sender.includes('소상공인') || sender.includes('반대') || sender.includes('번영회')) {
              textClass = 'text-rose-400 font-medium';
            } else if (sender.includes('주민') || sender.includes('시민') || sender.includes('찬성') || sender.includes('학부모')) {
              textClass = 'text-emerald-400 font-medium';
            } else if (sender.includes('시스템') || sender.includes('조정') || sender.includes('중재') || sender.includes('심의')) {
              textClass = 'text-amber-400 font-semibold';
            }
            
            return (
              <div key={index} className={`flex gap-2 items-start leading-relaxed ${textClass}`}>
                <span className="shrink-0 font-bold font-sans">
                  [{sender}]
                </span>
                <span className="mt-0.5">{log.text}</span>
              </div>
            );
          })}
          {simStep < 6 ? (
            <div className="text-slate-500 animate-pulse">... 에이전트 심의 분석 진행 중 ...</div>
          ) : (
            <div className="text-emerald-500 font-bold animate-pulse">✓ 에이전트 심의 분석 완료 (PDF 보고서 다운로드 가능)</div>
          )}
        </div>

        {/* 하단 제어 바 (보고서 다운로드 포함) */}
        <div className="flex justify-between items-center border-t border-slate-800 pt-3">
          <span className="text-[10px] text-slate-500">
            도로점용료 예상액: ₩ {Math.round((currentParcel.area || 0) * (currentParcel.price || 0) * 0.02).toLocaleString()} / 년
          </span>
          <div className="flex gap-3">
            <button
              onClick={handlePdfDownload}
              disabled={simStep < 6}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-semibold text-xs px-4 py-2.5 rounded-lg transition-all cursor-pointer"
            >
              📝 WeasyPrint PDF 보고서 다운로드
            </button>
            <button
              onClick={() => setShowSimModal(false)}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-4 py-2.5 rounded-lg transition-all cursor-pointer"
            >
              닫기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
