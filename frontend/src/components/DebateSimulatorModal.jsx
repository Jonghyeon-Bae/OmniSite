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
  apiFetch,
  districtId
}) {
  if (!showSimModal) return null;

  const currentParcel = selectedParcel[activeTab] || {};

  const handlePdfDownload = async () => {
    try {
      const payload = {
        district_id: districtId || 1,
        facility_type: inferredDomainTag || "city_feature",
        inferred_purpose: inferredPurpose || "입지 분석",
        candidate_pnu: currentParcel.pnu || currentParcel.PNU || "",
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
        status: "토론 완료",
        audit_state: "대기 중",
        audit_opinion: "공식 심의 완료 보고서 발급됨. 준공 고시 공문 감리 대기 중.",
        inferred_purpose: payload.inferred_purpose,
        ahp_weights: payload.ahp_weights,
        selected_parcel_jibun: payload.candidate_jibun,
        selected_parcel_pnu: currentParcel.pnu || currentParcel.PNU || null,
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
      
      let filename = `OmniSite_Report_${(payload.candidate_jibun || '용산구').replace(/ /g, '_')}.pdf`;
      const cd = res.headers.get('Content-Disposition');
      if (cd) {
        const match = cd.match(/filename\*=UTF-8''(.+)$/i) || cd.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]);
        }
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('⚠️ PDF 보고서 발급 중 오류가 발생했습니다: ' + err.message);
    }
  };

  const handleDocxDownload = async () => {
    try {
      const payload = {
        district_id: 1,
        facility_type: currentParcel.facility_type || "공공 시설",
        inferred_purpose: inferredPurpose || inferredDomainTag || "지능형 스마트시티 시설물",
        candidate_pnu: currentParcel.pnu || currentParcel.PNU || "",
        candidate_jibun: currentParcel.jibun || "용산구 미지정 부지",
        candidate_css: currentParcel.css || 50,
        candidate_lat: currentParcel.lat || 37.53,
        candidate_lng: currentParcel.lng || 126.97,
        candidate_reason: currentParcel.reason || "",
        ahp_weights: ahpWeights || {},
        debate_logs: simLogs.map(log => ({ sender: log.sender, text: log.text }))
      };

      const res = await apiFetch('/api/v1/spatial/report/download-docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('DOCX 다운로드 실패');
      
      let filename = `OmniSite_Report_${(payload.candidate_jibun || '용산구').replace(/ /g, '_')}.docx`;
      const cd = res.headers.get('Content-Disposition');
      if (cd) {
        const match = cd.match(/filename\*=UTF-8''(.+)$/i) || cd.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]);
        }
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('⚠️ 워드 보고서 발급 중 오류가 발생했습니다: ' + err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-fade-in">
      <div className="glass-panel w-full max-w-[1050px] h-[680px] max-h-[90vh] p-8 flex flex-col justify-between rounded-2xl border border-slate-800 shadow-2xl">
        <div className="flex justify-between items-center border-b border-slate-800/80 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
              <span>⚡ [{inferredPurpose || inferredDomainTag || '공공 인프라'}] 실시간 3자 AI 모의 심의 토론</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">Target PNU: <span className="font-mono text-amber-400 font-semibold">{currentParcel.pnu || 'PNU 미지정'}</span></p>
          </div>
          <button 
            onClick={() => setShowSimModal(false)}
            className="text-slate-400 hover:text-white text-xl font-bold cursor-pointer transition-all p-1 hover:bg-slate-800/60 rounded-lg"
            title="닫기"
          >
            &times;
          </button>
        </div>

        {/* 터미널 대화 스크롤 */}
        <div className="flex-1 my-5 bg-slate-950/80 rounded-xl p-5 overflow-y-auto font-mono text-xs flex flex-col gap-3.5 border border-slate-800/80 shadow-inner">
          {simLogs.map((log, index) => {
            const sender = log.sender || '';
            let badgeStyle = 'bg-slate-800 text-slate-300 border-slate-700';
            
            if (sender.includes('보건') || sender.includes('구청') || sender.includes('공무원') || sender.includes('정부')) {
              badgeStyle = 'bg-sky-500/20 text-sky-300 border-sky-500/40';
            } else if (sender.includes('상인') || sender.includes('소상공인') || sender.includes('찬성') || sender.includes('번영회')) {
              badgeStyle = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
            } else if (sender.includes('주민') || sender.includes('시민') || sender.includes('반대') || sender.includes('학부모')) {
              badgeStyle = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
            } else if (sender.includes('시스템') || sender.includes('조정') || sender.includes('중재') || sender.includes('심의')) {
              badgeStyle = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
            }

            const formattedText = log.text
              ? log.text.replace(/([.!?])\s+(?=[가-힣A-Za-z0-9])/g, (m, p1) => `${p1}\n\n`)
              : '';
            
            return (
              <div key={index} className="flex gap-3 leading-relaxed text-xs items-start bg-slate-900/40 p-3.5 rounded-xl border border-slate-800/60 shadow-sm">
                <span className={`font-bold shrink-0 px-2.5 py-1 rounded-lg text-[11px] self-start flex items-center justify-center border shadow-sm ${badgeStyle}`}>
                  [{sender}]
                </span>
                <div className="text-slate-200 whitespace-pre-line leading-relaxed flex-1 font-sans text-xs space-y-2">
                  {formattedText}
                </div>
              </div>
            );
          })}
          {simStep < 6 ? (
            <div className="text-slate-500 animate-pulse font-mono text-xs my-2">... AI 멀티에이전트 심의 분석 및 전문가 토론 진행 중 ...</div>
          ) : (
            <div className="text-emerald-400 font-bold animate-pulse text-xs border-t border-slate-800/60 pt-3 flex items-center gap-1.5">
              <span>✓ AI 멀티에이전트 모의 심의 토론 완료 (공통 합의안 도달 & 보고서 발급 가능)</span>
            </div>
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
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-semibold text-xs px-3.5 py-2.5 rounded-lg transition-all cursor-pointer"
            >
              📝 PDF 보고서
            </button>
            <button
              onClick={handleDocxDownload}
              disabled={simStep < 6}
              className="bg-sky-600 hover:bg-sky-700 disabled:opacity-40 text-white font-semibold text-xs px-3.5 py-2.5 rounded-lg transition-all cursor-pointer"
            >
              📄 워드(.docx) 보고서
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
