import React from 'react';

export default function PipelineStepBar({ currentStep, setPipelineStep }) {
  const steps = [
    { num: 1, label: 'AI 데이터 감리', icon: '🔍' },
    { num: 2, label: '3D 가상 작도', icon: '📐' },
    { num: 3, label: 'AHP 일관성 락', icon: '🔒' },
    { num: 4, label: 'PostGIS/XGB 추천', icon: '🎯' },
    { num: 5, label: 'RAG / AI 모의 토론', icon: '🗣️' },
    { num: 6, label: '공인 PDF 발급', icon: '📄' }
  ];

  return (
    <div className="absolute top-20 left-1/2 -translate-x-1/2 bg-slate-900/95 backdrop-blur-xl border border-slate-800/90 rounded-2xl px-5 py-2 flex items-center justify-center gap-2 z-30 shadow-2xl animate-fade-in">
      {steps.map((s, idx) => {
        const isActive = currentStep === s.num;
        const isDone = currentStep > s.num;
        return (
          <React.Fragment key={s.num}>
            <button
              onClick={() => setPipelineStep && setPipelineStep(s.num)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
                isActive
                  ? 'bg-blue-600 text-white shadow-[0_0_20px_rgba(37,99,235,0.6)] scale-105 border border-blue-400 ring-2 ring-blue-500/40 animate-pulse'
                  : isDone
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 hover:scale-102'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-800 hover:bg-slate-800 hover:scale-102'
              }`}
            >
              <span className="text-sm">{s.icon}</span>
              <span>{s.num}. {s.label}</span>
              {isDone && <span className="text-[10px] text-emerald-400 font-bold ml-0.5">✓</span>}
            </button>
            {idx < steps.length - 1 && <span className="text-slate-700 text-xs font-bold">➔</span>}
          </React.Fragment>
        );
      })}
    </div>
  );
}