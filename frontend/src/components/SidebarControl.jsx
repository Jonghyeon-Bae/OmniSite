import React from 'react';

export default function SidebarControl({
  pipelineStep,
  setPipelineStep,
  isAuditComplete,
  triggerFileAudit,
  isUploading,
  auditMetadata,
  inferredPurpose,
  setInferredPurpose,
  inferredReasoning,
  hitlQuestion,
  userPurpose,
  setUserPurpose,
  inferredDomainTag,
  setInferredDomainTag,
  handleFileChange,
  crValue,
  criteriaList,
  ahpWeights,
  isAhpLocked,
  handleSliderChange,
  handleAhpLock
}) {
  return (
    <div className="floating-overlay left-6 top-20 w-96 glass-panel p-6 flex flex-col gap-6 max-h-[82vh] overflow-y-auto">
      {/* ========================================================================= */}
      {/* 1. 사이드바 헤더 및 글로벌 파이프라인 단계 출력 */}
      {/* ========================================================================= */}
      <div className="flex justify-between items-center border-b border-slate-800/60 pb-3">
        <div>
          <h2 className="text-sm font-bold text-white mb-0.5">입지선정 기준 설정</h2>
          <p className="text-[10px] text-slate-400">데이터 적재 및 가중치 의사결정 수립</p>
        </div>
        <span className="text-xs bg-blue-600/20 text-blue-400 px-2.5 py-1 rounded-full font-bold">
          Step {pipelineStep} / 5
        </span>
      </div>

      {/* ========================================================================= */}
      {/* 2. [Step 1] 공간 데이터 업로드 및 AI 감리 의도 검증 */}
      {/* ========================================================================= */}
      <div className={`flex flex-col gap-3 transition-all duration-300 ${pipelineStep !== 1 ? 'opacity-40 pointer-events-none' : ''}`}>
        <div className="flex justify-between items-center">
          <label className="text-xs font-semibold text-slate-300">Step 1. 공간 데이터 수집 & AI 감리</label>
          <span className="text-[10px] text-blue-400 font-mono">CSV 전용 (분석용)</span>
        </div>

        {!isAuditComplete ? (
          <div 
            onClick={triggerFileAudit}
            className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-5 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30"
          >
            <p className="text-xs text-slate-300 font-semibold">📁 공간 데이터 CSV 업로드 (클릭)</p>
            <p className="text-[10px] text-slate-500 mt-1">컬럼명 및 위치 결측 검증 가동</p>
            {isUploading && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">업로드 및 AI 감리 분석 중...</p>}
          </div>
        ) : (
          /* AI 감리 결과 판독 및 실무자 의도 승인 루프 */
          <div className="bg-slate-950/60 p-4 rounded-xl border border-blue-500/30 flex flex-col gap-3">
            <div className="flex justify-between items-center border-b border-slate-900 pb-1.5">
              <span className="text-[11px] text-blue-400 font-bold">✓ AI 감리 결과 분석 완료</span>
              <span className="text-[10px] text-slate-500">인프라 목적 판독</span>
            </div>
            <div className="text-[11px] flex flex-col gap-2.5 text-slate-300 leading-relaxed">
              <p><strong className="text-slate-400">분석 의도 판독:</strong> {inferredPurpose}</p>
              {inferredReasoning && (
                <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800 text-[10px] text-slate-400 leading-normal font-mono">
                  <strong className="text-slate-300 block mb-1">🔍 AI 감리 추론 근거 (Reasoning):</strong>
                  {inferredReasoning}
                </div>
              )}
              {hitlQuestion && (
                <div className="bg-blue-950/40 p-2.5 rounded border border-blue-500/20 text-blue-300 font-medium">
                  ❓ {hitlQuestion}
                </div>
              )}
              <div className="flex flex-col gap-1 my-1">
                <span className="text-slate-400">분석 목적 보정 (HITL)</span>
                <input
                  type="text"
                  value={userPurpose}
                  onChange={(e) => {
                    setUserPurpose(e.target.value);
                    setInferredPurpose(e.target.value);
                  }}
                  className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white text-[11px] outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-slate-400">시맨틱 도메인 태그 지정</span>
                <select
                  value={inferredDomainTag}
                  onChange={(e) => setInferredDomainTag(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-[11px] outline-none focus:border-blue-500"
                >
                  <option value="smoking_zone">실외 흡연구역 입지 (smoking_zone)</option>
                  <option value="ev_charging">전기차 충전소 입지 (ev_charging)</option>
                  <option value="yellow_carpet">어린이 보호구역 옐로카펫 (yellow_carpet)</option>
                  <option value="city_feature">일반 스마트시티 시설물 (city_feature)</option>
                </select>
              </div>
            </div>
            <button
              onClick={() => setPipelineStep(2)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold py-2.5 rounded-lg transition-all"
            >
              의도 일치 확인 및 공간 매핑 승인 (Approve)
            </button>
          </div>
        )}
        <input 
          type="file" 
          multiple 
          accept=".csv" 
          id="file-uploader" 
          className="hidden" 
          onChange={handleFileChange} 
        />
      </div>

      {/* ========================================================================= */}
      {/* 3. [Step 3] AHP 슬라이더 컨트롤러 */}
      {/* ========================================================================= */}
      <div className={`flex flex-col gap-4 border-t border-slate-800/80 pt-4 transition-all duration-300 ${pipelineStep < 3 ? 'hidden' : ''} ${pipelineStep > 3 ? 'opacity-40 pointer-events-none' : ''}`}>
        <div className="flex justify-between items-center">
          <label className="text-xs font-semibold text-slate-300">Step 3. AHP 인자별 상대 가중치</label>
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold transition-all ${crValue < 0.1 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
            C.R. = {crValue} ({crValue < 0.1 ? '만족' : '위배'})
          </span>
        </div>

        <div className="flex flex-col gap-3">
          {criteriaList.map(item => (
            <div key={item.key} className="flex flex-col gap-1">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>{item.label}</span>
                <span className="font-mono text-white">{ahpWeights[item.key] !== undefined ? parseFloat(ahpWeights[item.key]).toFixed(1) : '5.0'}</span>
              </div>
              <input
                type="range"
                min="1"
                max="9"
                step="0.1"
                disabled={isAhpLocked || pipelineStep !== 3}
                value={ahpWeights[item.key] !== undefined ? ahpWeights[item.key] : 5.0}
                onChange={(e) => handleSliderChange(item.key, e.target.value)}
                className="w-full accent-blue-500 cursor-pointer h-1 bg-slate-800 rounded-lg appearance-none"
              />
            </div>
          ))}
        </div>

        {/* AHP 잠금 버튼 -> 입지 분석 트리거 */}
        <button
          onClick={handleAhpLock}
          disabled={crValue >= 0.1 || pipelineStep !== 3}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all disabled:opacity-30"
        >
          🔒 AHP 가중치 확정 및 추천 입지 연산 (Lock)
        </button>
      </div>
    </div>
  );
}
