import React from 'react';

export default function ExclusionZoneControl({
  pipelineStep,
  panelPosition,
  handleMouseDown,
  isDrawingExclusion,
  setIsDrawingExclusion,
  finishDrawingExclusion
}) {
  if (pipelineStep !== 2) return null;

  return (
    <div 
      style={{ 
        position: 'fixed', 
        left: `${panelPosition.x}px`, 
        top: `${panelPosition.y}px`,
        width: '260px'
      }}
      className="z-[1000] glass-panel p-4 flex flex-col gap-3 shadow-xl select-none"
    >
      {/* 드래그용 핸들 헤더 (cursor-move) */}
      <div 
        onMouseDown={handleMouseDown}
        className="border-b border-slate-800 pb-2 cursor-move flex flex-col gap-0.5 active:cursor-grabbing"
        title="마우스로 잡고 드래그하여 위치를 조절할 수 있습니다."
      >
        <h3 className="text-xs font-bold text-white mb-0.5 flex items-center gap-1.5">
          🚨 공간 통제 영역 설정
        </h3>
        <p className="text-[9px] text-slate-400">가상 구역 작도 및 실시간 DB 적재</p>
      </div>
      
      {/* 가상 금지구역 그리기 제어 */}
      <div className="flex flex-col gap-1.5">
        <button
          onClick={() => {
            if (isDrawingExclusion) {
              finishDrawingExclusion();
            } else {
              setIsDrawingExclusion(true);
            }
          }}
          className={`text-xs py-2 px-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
            isDrawingExclusion 
              ? 'bg-orange-600 hover:bg-orange-700 text-white animate-pulse' 
              : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
          }`}
        >
          {isDrawingExclusion ? '⏹️ 그리기 완료 및 저장' : '✏️ 가상 금지구역 그리기'}
        </button>
        {isDrawingExclusion && (
          <p className="text-[9px] text-orange-400 font-medium text-center animate-bounce leading-relaxed">
            ※ 지도 위 꼭짓점들을 좌클릭하고, <br/>마우스 <b>우클릭</b> 또는 <b>이 버튼을 재클릭</b>하면 <br/>명칭/메모 등록 창이 열립니다.
          </p>
        )}
      </div>
    </div>
  );
}
