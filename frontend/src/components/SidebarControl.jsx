import React from 'react';

export default function SidebarControl({
  pipelineStep,
  setPipelineStep,
  handlePipelineReset,
  isAuditComplete,
  triggerFileAudit,
  isUploading,
  isRecommending,
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
  handleAhpLock,
  handleApproveStep1,
  mlStatus,
  fetchMlStatus,
  showToast,
  onOpenGuideModal
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
        <div className="flex items-center gap-2">
          {handlePipelineReset && (
            <button
              onClick={handlePipelineReset}
              className="text-[10px] bg-slate-800/80 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded border border-slate-700 transition-all cursor-pointer"
              title="파이프라인 상태 완전 초기화"
            >
              🔄 리셋
            </button>
          )}
          <span className="text-xs bg-blue-600/20 text-blue-400 px-2.5 py-1 rounded-full font-bold">
            Step {pipelineStep} / 6
          </span>
        </div>
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
          <div className="flex flex-col gap-2">
            <div 
              onClick={triggerFileAudit}
              className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-5 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30"
            >
              <p className="text-xs text-slate-300 font-semibold">📁 공간 데이터 CSV 업로드 (클릭)</p>
              <p className="text-[10px] text-slate-500 mt-1">위경도(lat, lng), PNU, 이격거리 필드 자동 검증</p>
              {isUploading && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">업로드 및 AI 감리 분석 중...</p>}
            </div>
            
            <div className="bg-slate-900/50 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-[10px]">
              <span className="text-slate-400">📜 조례 PDF 추가 시 RAG 교차 준공 감리 가동</span>
            </div>
          </div>
        ) : (
          /* AI 감리 결과 판독 및 실무자 의도 승인 루프 */
          <div className="bg-slate-950/60 p-4 rounded-xl border border-blue-500/30 flex flex-col gap-3">
            {auditMetadata?.hasRegulations === false && (
              <div className="bg-amber-950/45 border border-amber-500/40 text-amber-300 p-3 rounded-lg text-[10px] leading-normal mb-1 flex flex-col gap-1">
                <span className="font-bold flex items-center gap-1 text-[11px] text-amber-200">
                  ⚠️ RAG 법적 근거자료 부재 경고
                </span>
                <span>관련 조례, 시행령 등 법적 근거자료가 존재하지 않아 관련 자료 부재로 인한 정확도가 낮을 수 있습니다.</span>
              </div>
            )}
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
              onClick={handleApproveStep1}
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
      {/* 3. [Step 2] XGBoost ML 모델 재학습 검증 (New) */}
      {/* ========================================================================= */}
      <div className={`flex flex-col gap-4 border-t border-slate-800/80 pt-4 transition-all duration-300 ${pipelineStep !== 2 ? 'hidden' : ''}`}>
        <div className="flex justify-between items-center border-b border-slate-900 pb-2">
          <h3 className="text-xs font-bold text-amber-400">Step 2. 님비 예측 모델 학습 및 신뢰도 검증</h3>
          <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full font-bold">XGBoost</span>
        </div>

        {mlStatus && mlStatus.is_training ? (
          <div className="flex flex-col items-center justify-center py-6 gap-3">
            <span className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-amber-400 font-semibold animate-pulse">신규 감리 데이터 기반 동적 재학습 중...</p>
            <p className="text-[10px] text-slate-500">PostGIS 공간 인자 최단 거리 연산 매핑 중</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
              <div className="flex flex-col text-center">
                <span className="text-[9px] text-slate-400">예측 정확도 (Accuracy)</span>
                <span className="text-sm font-mono font-bold text-amber-400">
                  {mlStatus?.last_trained_at ? (mlStatus.accuracy * 100).toFixed(1) + '%' : '미학습'}
                </span>
              </div>
              <div className="flex flex-col text-center">
                <span className="text-[9px] text-slate-400">조화 평균 (F1-Score)</span>
                <span className="text-sm font-mono font-bold text-amber-400">
                  {mlStatus?.last_trained_at ? mlStatus.f1_score.toFixed(3) : '미학습'}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-2 bg-slate-950/30 p-3 rounded-xl border border-slate-900">
              <span className="text-[10px] font-bold text-slate-300">📊 님비 갈등 피처 기여도 (Feature Importance)</span>
              <div className="flex flex-col gap-2 max-h-40 overflow-y-auto">
                {Object.keys(mlStatus?.feature_importances || {}).length > 0 ? (
                  Object.entries(mlStatus?.feature_importances || {}).map(([feature, val]) => (
                    <div key={feature} className="flex items-center text-[9px]">
                      <span className="w-24 text-slate-400 truncate">{feature}</span>
                      <div className="flex-1 bg-slate-800 h-2 rounded-full overflow-hidden mx-1.5">
                        <div 
                          className="bg-amber-500 h-full rounded-full transition-all" 
                          style={{ width: `${val * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-amber-400 w-8 text-right">{(val * 100).toFixed(1)}%</span>
                    </div>
                  ))
                ) : (
                  <span className="text-[10px] text-slate-500 py-1">가용 피처 기여도 정보가 존재하지 않습니다.</span>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={fetchMlStatus}
              className="w-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold py-1.5 rounded border border-slate-700/60 cursor-pointer transition-all"
            >
              🔄 새로고침 (ML 지표 동기화)
            </button>

            <div className="flex flex-col gap-2 mt-1">
              <button
                type="button"
                onClick={() => {
                  showToast('✓ 신규 예측 가중치를 시뮬레이션 모델에 적용 완료했습니다!', 'success');
                  setPipelineStep(3);
                }}
                className="w-full bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-bold text-xs py-2.5 rounded-lg transition-all shadow-md shadow-amber-500/10 cursor-pointer"
              >
                ✓ 신규 예측 가중치 승인 및 진행
              </button>
              <button
                type="button"
                onClick={() => {
                  showToast('✓ 이전 가중치 버전을 유지한 채 시뮬레이션을 진행합니다.', 'info');
                  setPipelineStep(3);
                }}
                className="w-full bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-300 text-[10px] font-semibold py-2 rounded-lg border border-slate-800 transition-all cursor-pointer"
              >
                이전 가중치 모델 유지 후 진행
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* 4. [Step 4] AHP 슬라이더 컨트롤러 */}
      {/* ========================================================================= */}
      <div className={`flex flex-col gap-4 border-t border-slate-800/80 pt-4 transition-all duration-300 ${pipelineStep < 4 ? 'hidden' : ''} ${pipelineStep > 4 ? 'opacity-40 pointer-events-none' : ''}`}>
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
                disabled={isAhpLocked || pipelineStep !== 4}
                value={ahpWeights[item.key] !== undefined ? ahpWeights[item.key] : 5.0}
                onChange={(e) => handleSliderChange(item.key, e.target.value)}
                className="w-full accent-blue-500 cursor-pointer h-1 bg-slate-800 rounded-lg appearance-none"
              />
            </div>
          ))}
        </div>

        <button
          onClick={handleAhpLock}
          disabled={crValue >= 0.1 || pipelineStep !== 4 || isRecommending}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all disabled:opacity-30 flex items-center justify-center gap-1.5"
        >
          {isRecommending ? (
            <>
              <span className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin shrink-0" />
              AHP 락킹 및 PostGIS 연산 중...
            </>
          ) : (
            '🔒 AHP 가중치 확정 및 추천 입지 연산 (Lock)'
          )}
        </button>
      </div>
    </div>
  );
}
