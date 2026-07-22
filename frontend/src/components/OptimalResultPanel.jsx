import React from 'react';

export default function OptimalResultPanel({
  pipelineStep,
  setPipelineStep,
  showManualMapping,
  setShowManualMapping,
  columnMapping,
  setColumnMapping,
  csvHeaders,
  hitlLng,
  setHitlLng,
  hitlLat,
  setHitlLat,
  handleHitlCommit,
  isCommitting,
  selectedParcel,
  activeTab,
  setActiveTab,
  criteriaList,
  intensityLevel,
  setIntensityLevel,
  runSimulation,
  simStep,
  addressAnalysis,
  isAnalyzingAddress,
  onOpenGuideModal
}) {
  const currentParcel = selectedParcel[activeTab] || {};

  return (
    <div className="floating-overlay right-6 top-20 w-96 glass-panel p-6 flex flex-col gap-5 max-h-[82vh] overflow-y-auto">
      {/* ========================================================================= */}
      {/* 1. [Step 2] 비주얼 HITL 좌표 보정 영역 */}
      {/* ========================================================================= */}
      {pipelineStep === 3 && (
        <div className="flex flex-col gap-3">
          <div className="border-b border-slate-800 pb-2">
            <h2 className="text-xs font-bold text-amber-500">Step 2. 비주얼 HITL 좌표 보정 중</h2>
            <p className="text-[10px] text-slate-400 font-medium">지도의 주황색 핀을 드래그하거나 아래 좌표를 보정하세요</p>
          </div>

          <div className="bg-slate-950/40 p-4 rounded-xl border border-amber-500/30 flex flex-col gap-3">
            {/* 수동 컬럼 매핑 아코디언 토글 */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between bg-slate-900/50 p-2 rounded border border-slate-800">
                {columnMapping && columnMapping.lat && columnMapping.lng ? (
                  <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                    🟢 위경도 열 자동 매핑 완료
                  </span>
                ) : (
                  <span className="text-[10px] text-rose-400 font-semibold flex items-center gap-1">
                    ⚠️ 위경도 열 탐지 실패 (수동 매핑 필요)
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => setShowManualMapping(!showManualMapping)}
                  className="text-[9px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded border border-slate-700/60 transition-all font-sans cursor-pointer"
                >
                  {showManualMapping ? '접기 ▲' : '열기 ▼'}
                </button>
              </div>

              {showManualMapping && (
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850 flex flex-col gap-2.5">
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] text-slate-400 font-semibold">위도(Latitude) 열 지정</label>
                    <select
                      value={columnMapping?.lat || ''}
                      onChange={(e) => setColumnMapping({ ...columnMapping, lat: e.target.value })}
                      className="bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-1.5 rounded outline-none"
                    >
                      <option value="">-- 위도 컬럼 선택 --</option>
                      {csvHeaders.map(h => <option key={h} value={h}>{h}</option>)}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] text-slate-400 font-semibold">경도(Longitude) 열 지정</label>
                    <select
                      value={columnMapping?.lng || ''}
                      onChange={(e) => setColumnMapping({ ...columnMapping, lng: e.target.value })}
                      className="bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-1.5 rounded outline-none"
                    >
                      <option value="">-- 경도 컬럼 선택 --</option>
                      {csvHeaders.map(h => <option key={h} value={h}>{h}</option>)}
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* 수동 좌표 입력 필드 */}
            <div className="grid grid-cols-2 gap-3 mt-1">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-slate-400 font-medium">경도 (Longitude)</span>
                <input
                  type="number"
                  step="0.000001"
                  value={isNaN(hitlLng) ? '' : hitlLng}
                  onChange={(e) => setHitlLng(parseFloat(e.target.value))}
                  className="w-full min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs outline-none font-mono"
                />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-slate-400 font-medium">위도 (Latitude)</span>
                <input
                  type="number"
                  step="0.000001"
                  value={isNaN(hitlLat) ? '' : hitlLat}
                  onChange={(e) => setHitlLat(parseFloat(e.target.value))}
                  className="w-full min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs outline-none font-mono"
                />
              </div>
            </div>
            <button
              onClick={handleHitlCommit}
              disabled={isCommitting}
              className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs py-2 rounded-lg transition-all flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer"
            >
              {isCommitting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin shrink-0" />
                  보정 공간 데이터 확정 중...
                </>
              ) : (
                '보정 완료 및 데이터 확정 (Commit)'
              )}
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. [Step 5] 최적 추천 후보지 속성 카드 및 리포트 */}
      {/* ========================================================================= */}
      {pipelineStep === 5 && (
        Object.keys(selectedParcel).filter(k => selectedParcel[k] && selectedParcel[k].id).length === 0 ? (
          <div className="flex flex-col gap-4 bg-slate-950/40 p-5 rounded-2xl border border-rose-500/20 text-center">
            <span className="text-[32px] text-rose-500 animate-pulse">📍</span>
            <h3 className="text-xs font-bold text-rose-400">적격 입지 후보 부지 없음</h3>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              조례 이격거리 필터 및 고가/지하차도 가드를 통과한 적격 국공유지가 지정 기준점 반경 300m 이내에 존재하지 않습니다.
            </p>
            <div className="flex flex-col gap-2 mt-2">

              <button
                type="button"
                onClick={() => {
                  window.location.reload();
                }}
                className="w-full bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold text-[10px] py-2.5 rounded-lg transition-all cursor-pointer border border-slate-800"
              >
                처음부터 다시 분석 시작(초기화)
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
          {/* Top 1 ~ Top 5 동적 탭 바 */}
          <div className="flex bg-slate-950/60 p-1 rounded-lg border border-slate-800/80">
            {Object.keys(selectedParcel)
              .filter(tab => selectedParcel[tab] && Object.keys(selectedParcel[tab]).length > 0 && selectedParcel[tab].id)
              .map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 text-center py-1.5 text-[10px] font-semibold rounded-md cursor-pointer transition-all ${
                    activeTab === tab 
                      ? 'bg-blue-600 text-white shadow-md' 
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab.toUpperCase()}
                </button>
              ))}
          </div>

          {/* 필지 속성 카드 */}
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold text-slate-300">Step 5. 추천지 속성 정보</h3>
            <div className="bg-slate-950/40 rounded-xl p-4.5 flex flex-col gap-3 border border-slate-900">
              <div className="flex justify-between items-start gap-1">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] text-slate-500 font-semibold">지번 주소 (PNU 연계)</span>
                  <span className="text-xs text-white font-medium break-all">{currentParcel.jibun}</span>
                </div>
                {currentParcel.jibun && (
                  <button
                    onClick={() => {
                      const cleanAddr = currentParcel.jibun.split('(')[0].trim();
                      navigator.clipboard.writeText(cleanAddr);
                      alert(`📋 주소가 복사되었습니다: ${cleanAddr}`);
                    }}
                    className="text-[9px] bg-slate-900 hover:bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-800 transition-all font-sans cursor-pointer flex items-center gap-1 shrink-0 ml-1.5"
                  >
                    <span>📋 주소 복사</span>
                  </button>
                )}
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">면적(㎡)</span>
                <span className="font-mono text-white">{currentParcel.area || 0} ㎡</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">공시지가</span>
                <span className="font-mono text-emerald-400">₩ {(currentParcel.price || 0).toLocaleString()} / ㎡</span>
              </div>
              <div className="flex justify-between items-center text-[11px] border-t border-slate-900 pt-2 text-slate-500">
                <span>위도/경도 좌표</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono">{currentParcel.lat || 0.0}, {currentParcel.lng || 0.0}</span>
                  {currentParcel.lat && currentParcel.lng && (
                    <button
                      onClick={() => {
                        const url = `https://map.kakao.com/link/roadview/${currentParcel.lat},${currentParcel.lng}`;
                        window.open(url, '_blank');
                      }}
                      className="text-[9px] bg-slate-900 hover:bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-800 transition-all cursor-pointer"
                    >
                      🗺️ 로드뷰 보기
                    </button>
                  )}
                </div>
              </div>
              {currentParcel.reason && (
                <div className="flex flex-col gap-1 mt-1 border-t border-slate-900/60 pt-2">
                  <span className="text-[10px] text-emerald-500 font-semibold">입지 선정 사유 및 주변 환경 조언</span>
                  <span className="text-[11px] text-slate-300 leading-relaxed bg-slate-950/30 p-2 rounded-lg border border-slate-900/50">
                    {currentParcel.reason}
                  </span>
                </div>
              )}
            </div>
          </div>



          {/* 세부 평가 지표 수치 리스트 */}
          {currentParcel.criteria_scores && (
            <div className="flex flex-col gap-2 border-t border-slate-900/60 pt-3">
              <span className="text-[11px] font-semibold text-slate-400">세부 평가 지표 수치 (Spatial Detail)</span>
              <div className="bg-slate-950/20 rounded-lg p-2.5 flex flex-col gap-1.5 border border-slate-800/30">
                {Object.entries(currentParcel.criteria_scores).map(([k, val]) => {
                  const matchedCriteria = criteriaList.find(c => c.key === k);
                  const label = matchedCriteria ? matchedCriteria.label : k;
                  return (
                    <div key={k} className="flex justify-between text-[11px]">
                      <span className="text-slate-500">{label}</span>
                      <span className="font-mono text-slate-300 font-semibold">
                        {typeof val === 'number' 
                          ? val.toLocaleString(undefined, {maximumFractionDigits: 1}) 
                          : val}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 6 이동 네비게이션 버튼 */}
          <button
            onClick={() => setPipelineStep(6)}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs py-3.5 rounded-xl transition-all cursor-pointer shadow-lg shadow-blue-900/30 flex items-center justify-center gap-1.5"
          >
            Step 6. 의사결정 갈등 심의 이동 ➔
          </button>
        </div>
      ))/* [v4.9.20] End of step 4 conditional ternary mapping */ }

      {/* ========================================================================= */}
      {/* 3. [Step 6] 의사결정 시뮬레이션 및 토론 (독립 격리) */}
      {/* ========================================================================= */}
      {pipelineStep === 6 && (
        <div className="flex flex-col gap-5">
          {/* Step 5 롤백 뒤로가기 버튼 */}
          <button
            onClick={() => setPipelineStep(5)}
            className="w-fit text-[10px] text-slate-400 hover:text-slate-200 transition-all cursor-pointer font-semibold flex items-center gap-1 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800"
          >
            ◀ Step 5. 입지 정보로 돌아가기
          </button>

          {/* 갈등 민감도 카드 */}
          <div className="flex flex-col gap-3 bg-slate-950/40 p-4 rounded-xl border border-slate-900/50">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-slate-300">지역 갈등 민감도 (CSS)</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                currentParcel.cssGrade === '상' ? 'bg-rose-500/20 text-rose-400' :
                currentParcel.cssGrade === '중' ? 'bg-amber-500/20 text-amber-400' :
                'bg-emerald-500/20 text-emerald-400'
              }`}>
                등급: {currentParcel.cssGrade || '하'} ({currentParcel.css || 0}점)
              </span>
            </div>

            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className={`h-full transition-all duration-500 ${
                currentParcel.cssGrade === '상' ? 'bg-rose-500' :
                currentParcel.cssGrade === '중' ? 'bg-amber-500' :
                'bg-emerald-500'
              }`} style={{ width: `${currentParcel.css || 0}%` }} />
            </div>
          </div>

          <div className="border-t border-slate-850 pt-4 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-300">Step 6. 의사결정 시뮬레이션</span>
              <span className="text-[10px] text-slate-400 font-mono">갈등 조율 시뮬레이터</span>
            </div>

            {/* 갈등 강도 선택 라디오 버튼 그룹 */}
            <div className="flex flex-col gap-1.5 bg-slate-950/30 p-3 rounded-xl border border-slate-900/60">
              <span className="text-[10px] text-slate-500 font-semibold">모의 토론 갈등 강도 설정</span>
              <div className="grid grid-cols-3 gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800/50">
                <button
                  type="button"
                  onClick={() => setIntensityLevel("normal")}
                  className={`text-[10px] font-semibold py-1.5 rounded-md transition-all cursor-pointer ${
                    intensityLevel === "normal"
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  보통 🟢
                </button>
                <button
                  type="button"
                  onClick={() => setIntensityLevel("dangerous")}
                  className={`text-[10px] font-semibold py-1.5 rounded-md transition-all cursor-pointer ${
                    intensityLevel === "dangerous"
                      ? "bg-amber-600/20 text-amber-400 border border-amber-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  위험 🟡
                </button>
                <button
                  type="button"
                  onClick={() => setIntensityLevel("extreme")}
                  className={`text-[10px] font-semibold py-1.5 rounded-md transition-all cursor-pointer ${
                    intensityLevel === "extreme"
                      ? "bg-rose-600/20 text-rose-400 border border-rose-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  매우 위험 🔴
                </button>
              </div>
            </div>

            {/* 시뮬레이션 개시 버튼 */}
            <button
              onClick={runSimulation}
              disabled={simStep > 0 && simStep < 6}
              className="w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs py-3.5 rounded-xl transition-all cursor-pointer shadow-lg shadow-rose-900/30 flex items-center justify-center gap-1.5 disabled:opacity-60"
            >
              {simStep > 0 && simStep < 6 ? (
                <>
                  <span className="w-4 h-4 border-2 border-t-transparent border-white rounded-full animate-spin shrink-0" />
                  심의 토론 에이전트 스트리밍 중...
                </>
              ) : (
                `${activeTab.toUpperCase()} 갈등 심의 시뮬레이터 실행 (GPT-4o)`
              )}
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. [기타] Step 1, 2, 3 및 4 진행 중 가이드 */}
      {/* ========================================================================= */}
      {pipelineStep !== 3 && pipelineStep < 5 && (
        <div className="text-center py-20 text-slate-500 text-xs">
          [Step 1] 데이터 적재 및 <br />
          [Step 2] ML 예측 신뢰도 검증 및 <br />
          [Step 4] AHP 가중치 잠금을 진행하시면<br />
          이곳에 공간 차집합 추천 결과가 출력됩니다.
        </div>
      )}
    </div>
  );
}
