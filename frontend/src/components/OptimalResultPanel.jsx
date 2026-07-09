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
  simStep
}) {
  const currentParcel = selectedParcel[activeTab] || {};

  return (
    <div className="floating-overlay right-6 top-20 w-96 glass-panel p-6 flex flex-col gap-5 max-h-[82vh] overflow-y-auto">
      {/* ========================================================================= */}
      {/* 1. [Step 2] 비주얼 HITL 좌표 보정 영역 */}
      {/* ========================================================================= */}
      {pipelineStep === 2 && (
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
                <div className="flex flex-col gap-2.5 p-3 bg-slate-900/35 rounded-lg border border-slate-800/80 animate-fade-in">
                  <div className="flex flex-col gap-1 text-[10px]">
                    <span className="text-slate-400 font-medium">위도(Lat) 컬럼 매핑</span>
                    <select
                      value={(columnMapping && columnMapping.lat) || ''}
                      onChange={(e) => setColumnMapping(prev => ({ ...prev, lat: e.target.value }))}
                      className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white text-xs outline-none focus:border-amber-500"
                    >
                      <option value="">-- 위도 컬럼 선택 --</option>
                      {csvHeaders.map(h => (
                        <option key={h} value={h}>{h}</option>
                      ))}
                    </select>
                  </div>

                  <div className="flex flex-col gap-1 text-[10px]">
                    <span className="text-slate-400 font-medium">경도(Lng) 컬럼 매핑</span>
                    <select
                      value={(columnMapping && columnMapping.lng) || ''}
                      onChange={(e) => setColumnMapping(prev => ({ ...prev, lng: e.target.value }))}
                      className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white text-xs outline-none focus:border-amber-500"
                    >
                      <option value="">-- 경도 컬럼 선택 --</option>
                      {csvHeaders.map(h => (
                        <option key={h} value={h}>{h}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-2 w-full">
              <div className="flex-1 min-w-0 flex flex-col gap-1 text-[11px]">
                <span className="text-slate-400">경도(Lng) 좌표 보정</span>
                <input 
                  type="number" 
                  step="0.000001" 
                  value={isNaN(hitlLng) ? '' : hitlLng} 
                  onChange={(e) => setHitlLng(parseFloat(e.target.value))} 
                  className="w-full min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs outline-none font-mono" 
                />
              </div>
              <div className="flex-1 min-w-0 flex flex-col gap-1 text-[11px]">
                <span className="text-slate-400">위도(Lat) 좌표 보정</span>
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
      {/* 2. [Step 4 & 5] 최적 추천 후보지 탭 및 속성 카드 */}
      {/* ========================================================================= */}
      {pipelineStep >= 4 ? (
        <div className="flex flex-col gap-5">
          {/* Top 1 ~ Top 5 동적 탭 렌더링 */}
          <div className="flex bg-slate-950/60 p-1 rounded-lg border border-slate-800/80">
            {Object.keys(selectedParcel)
              .filter(tab => selectedParcel[tab] && Object.keys(selectedParcel[tab]).length > 0 && selectedParcel[tab].id)
              .map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 text-center py-1.5 text-[10px] font-semibold rounded-md cursor-pointer transition-all ${activeTab === tab ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  {tab.toUpperCase()}
                </button>
              ))}
          </div>

          {/* 필지 속성 카드 */}
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold text-slate-300">Step 4. 추천지 속성 정보</h3>
            <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 flex flex-col gap-2.5 animate-fade-in">
              {/* 일반 부지 vs 차선책 부지 구분 뱃지 [v4.7.0] */}
              <div className="flex justify-between items-center pb-2 border-b border-slate-900/60">
                <span className="text-[10px] text-slate-400 font-semibold">입지 성격 구분</span>
                {currentParcel.is_fallback ? (
                  <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse">
                    ⚠️ 법정 규제 완화 차선책
                  </span>
                ) : (
                  <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    🟢 일반 규제 준수 부지
                  </span>
                )}
              </div>

              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400 font-semibold">지번 / 소유 구분</span>
                <div className="flex items-center gap-1">
                  <span className="text-white font-semibold max-w-[160px] truncate" title={currentParcel.jibun}>{currentParcel.jibun || '지정한 동 내 미확정 필지'}</span>
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

          {/* 갈등 민감도 카드 */}
          <div className="flex flex-col gap-3">
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

          {/* 세부 평가 지표 스펙 */}
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
                      <span className="font-mono text-slate-300 font-semibold">{typeof val === 'number' ? val.toLocaleString(undefined, {maximumFractionDigits: 1}) : val}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 3. [Step 5] AI 모의 토론 기동 패널 */}
          {/* ========================================================================= */}
          <div className="border-t border-slate-800/80 pt-4 flex flex-col gap-2.5">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-300">Step 5. 의사결정 시뮬레이션</span>
              <span className="text-[10px] text-slate-400 font-mono">갈등 조율 시뮬레이터</span>
            </div>
            
            {/* 갈등 강도 선택 라디오 버튼 그룹 */}
            <div className="flex flex-col gap-1.5">
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

            <button 
              onClick={() => {
                setPipelineStep(5);
                runSimulation();
              }}
              disabled={simStep > 0 && simStep < 6}
              className="w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs py-3 rounded-xl transition-all cursor-pointer shadow-lg shadow-rose-900/30 flex items-center justify-center gap-1.5 disabled:opacity-60"
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
      ) : (
        pipelineStep !== 2 && (
          <div className="text-center py-20 text-slate-500 text-xs">
            [Step 1] 데이터 적재 및 <br />
            [Step 3] AHP 가중치 잠금을 진행하시면<br />
            이곳에 공간 차집합 추천 결과가 출력됩니다.
          </div>
        )
      )}
    </div>
  );
}
