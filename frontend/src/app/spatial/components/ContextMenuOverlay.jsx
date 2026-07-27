import React from 'react';

export default function ContextMenuOverlay({ contextMenu, onClose, onAddExclusionZone, onInspectParcel }) {
  if (!contextMenu || !contextMenu.visible) return null;

  return (
    <div
      style={{ top: contextMenu.y, left: contextMenu.x }}
      className="fixed z-50 bg-slate-900/95 backdrop-blur-md border border-slate-800 shadow-2xl rounded-xl p-1.5 min-w-[180px] font-mono text-xs flex flex-col gap-1 animate-fade-in"
    >
      <div className="px-2 py-1 border-b border-slate-800 text-[10px] text-slate-400 font-semibold">
        📍 {contextMenu.lat?.toFixed(5)}, {contextMenu.lng?.toFixed(5)}
      </div>
      <button
        onClick={() => { onAddExclusionZone && onAddExclusionZone(contextMenu); onClose(); }}
        className="w-full text-left px-2.5 py-1.5 rounded-lg text-slate-200 hover:bg-slate-800 hover:text-white transition-all cursor-pointer flex items-center gap-2"
      >
        <span>📐 3D 가상 금지구역 추가</span>
      </button>
      <button
        onClick={() => { onInspectParcel && onInspectParcel(contextMenu); onClose(); }}
        className="w-full text-left px-2.5 py-1.5 rounded-lg text-slate-200 hover:bg-slate-800 hover:text-white transition-all cursor-pointer flex items-center gap-2"
      >
        <span>🔍 인근 PNU 및 속성 정밀 감리</span>
      </button>
    </div>
  );
}