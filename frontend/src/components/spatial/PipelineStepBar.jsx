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
    <div className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 py-2 flex items-center justify-center gap-2 z-20 shrink-0">
      {steps.map((s, idx) => {
        const isActive = currentStep === s.num;
        const isDone = currentStep > s.num;
        return (
          <React.Fragment key={s.num}>
            <button
              onClick={() => setPipelineStep && setPipelineStep(s.num)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-900/50 scale-105 border border-blue-400'
                  : isDone
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              <span>{s.icon}</span>
              <span>{s.num}. {s.label}</span>
              {isDone && <span className="text-[10px]">✓</span>}
            </button>
            {idx < steps.length - 1 && <span className="text-slate-700 text-xs">➔</span>}
          </React.Fragment>
        );
      })}
    </div>
  );
}