import React, { useState, useEffect } from 'react';

const STEP_GUIDE_DATA = {
  1: {
    title: 'Step 1. 공간 데이터 수집 & AI 감리 (Ingestion & Audit)',
    subtitle: '분석 대상 지리 데이터 원천 파싱 및 의도 검증 단계',
    icon: '📂',
    badgeColor: 'bg-blue-500/20 border-blue-500/40 text-blue-400',
    description: '분석하고자 하는 스마트 인프라 후보지 데이터셋(CSV)을 업로드하면, AI 감리 엔진이 수초 만에 지표와 수립 목적을 자동 감별합니다.',
    items: [
      {
        head: '📋 업로드 데이터 조건',
        body: '위도/경도(lat, lng) 좌표 또는 PNU(필지고유번호), 면적, 이격거리 관련 실측 컬럼이 포함된 CSV 파일'
      },
      {
        head: '🔍 AI 자동 감리 (HITL)',
        body: 'OpenAI 임베딩 파이프라인이 텍스트 속성을 파악하여 입지선정 목적(예: 스마트 흡연부스, 킥보드 거치대)과 지표 태그를 자동 추론'
      },
      {
        head: '📜 RAG 조례 PDF 연동',
        body: '지자체 자치법규 조례 PDF를 추가 적재하면 [조례명 > 제N조] 파싱 기반의 교차 감리 준비가 완료됩니다.'
      }
    ]
  },
  2: {
    title: 'Step 2. 공간 좌표 보정 & 지도 레이어 검증 (Spatial Alignment)',
    subtitle: '지도 캔버스 상의 실측 미세 좌표 정밀 교정 단계',
    icon: '🗺️',
    badgeColor: 'bg-indigo-500/20 border-indigo-500/40 text-indigo-400',
    description: 'PostGIS GIS 공간 맵 타일 상에 후보 지점들이 정확한 위치에 올려졌는지 시각적으로 검증하고 보정합니다.',
    items: [
      {
        head: '📍 마커 동적 인터랙션',
        body: '지도 상의 드래그 가능 마커를 직접 이동시켜 현장 상황에 맞게 핀 위치를 미세 조정'
      },
      {
        head: '🛡️ 용도제한 보호구역 레이어',
        body: '학교, 유치원 등 보호구역 이격거리 버퍼(50m~200m) 붉은색 링을 실시간 캔버스에 렌더링하여 위배 여부 1차 필터링'
      },
      {
        head: '🚫 금지구역 마커 지정 거부 가드',
        body: '사용자 지정 물리 금지구역 상에 마커가 올려지면 백엔드가 HTTP 400 거부 에러를 발생시켜 오지정을 방지합니다.'
      }
    ]
  },
  3: {
    title: 'Step 3. AHP 가중치 프로필 확정 (AHP Decision Weight Lock)',
    subtitle: '다기준 의사결정 분석기법(AHP) 기반 정책 가중치 부여',
    icon: '⚖️',
    badgeColor: 'bg-amber-500/20 border-amber-500/40 text-amber-400',
    description: '지자체 공무원 및 전문가 그룹의 의사결정 우선순위를 지표별 슬라이더(유동인구, 이격거리, 민원 등)로 조절합니다.',
    items: [
      {
        head: '📊 상대적 비율 설정',
        body: '모든 지표 슬라이더 가중치 합이 100%가 되도록 조정 (자동 정규화 연산 수행)'
      },
      {
        head: '🔒 프로필 잠금 (AHP Lock)',
        body: '가중치 세팅 후 [AHP 프로필 잠금]을 누르면 백엔드 고유값 연산기(Eigenvector Matrix)가 작동하여 지적 필지별 적합도 총점이 새로 재계산됨'
      }
    ]
  },
  4: {
    title: 'Step 4. 최적 입지 추천 & 갈등 예측 (PostGIS & XGBoost CSS)',
    subtitle: '공간 연산 순위 추천 및 주민 갈등 민감도 머신러닝 채점',
    icon: '🎯',
    badgeColor: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400',
    description: 'PostGIS 지리 합산 총점 순위에 따라 최적 1위~10위 입지 필지가 지도 상에 마커로 핀포인팅됩니다.',
    items: [
      {
        head: '🤖 XGBoost 갈등도(CSS) 채점',
        body: '인공지능 머신러닝 두뇌가 주변 학교 거리, 민원 실적, 유동인구를 종합 평가하여 갈등 민감도 점수(0~100점)를 자동 부여'
      },
      {
        head: '📌 필지 잠금 및 안건 이력 수립',
        body: '추천 목록에서 원하는 후보지를 선택하고 [후보지 잠금]을 누르면 백엔드 DB에 심의 안건 이력으로 안전하게 락킹 저장됨'
      }
    ]
  },
  5: {
    title: 'Step 5. RAG 법규 준공 감리 & AI 3자 모의 토론 (Audit & Multi-Agent Debate)',
    subtitle: '조례 자동 교차 검증 및 AI 페르소나 모의 공청회 시뮬레이션',
    icon: '💬',
    badgeColor: 'bg-purple-500/20 border-purple-500/40 text-purple-400',
    description: '선택된 후보지에 대하여 RAG 법령 검증과 AI 페르소나그룹 모의 토론이 순차적으로 집행됩니다.',
    items: [
      {
        head: '📄 pgvector RAG 자동 감리',
        body: '업로드된 자치구 조례 PDF 텍스트와 필지 실측 공간 수치를 AI가 판독하여 [적합/부적합/조건부 적합] 판정 도출'
      },
      {
        head: '💬 3자 AI 모의 공청회 토론',
        body: '상인 대표, 주민 대표, 갈등조정관 3인의 AI가 대화를 주고받으며 민원 갈등을 사전에 예측하고 현실적 상생 중재안 도출'
      },
      {
        head: '💾 ML 자가학습 편입',
        body: '[자가학습 적재] 버튼 클릭 시 준공 성공 데이터가 ML 모델로 적재되어 AI 갈등 예측 정밀도가 자동으로 향상됨'
      }
    ]
  }
};

export default function StepGuideModal({ show, onClose, initialStep = 1 }) {
  const [activeTab, setActiveTab] = useState(initialStep);

  useEffect(() => {
    if (initialStep) {
      setActiveTab(initialStep);
    }
  }, [initialStep, show]);

  if (!show) return null;

  const guide = STEP_GUIDE_DATA[activeTab] || STEP_GUIDE_DATA[1];

  return (
    <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-[80] flex items-center justify-center p-4">
      <div className="glass-panel w-full max-w-2xl p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100 border border-slate-700/80 shadow-2xl">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer text-sm"
        >
          ✕
        </button>

        {/* 모달 상단 탭 바 (Step 1 ~ Step 5 통합 탐색) */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-amber-400">💡 공간 의사결정 파이프라인 실무 가이드</span>
          </div>
          <span className="text-[10px] text-slate-400">단계 탭을 클릭하여 전체 가이드를 둘러보세요</span>
        </div>

        <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
          {[1, 2, 3, 4, 5].map(stepNum => (
            <button
              key={stepNum}
              onClick={() => setActiveTab(stepNum)}
              className={`flex-1 py-2 text-center text-xs font-bold rounded-lg cursor-pointer transition-all ${
                activeTab === stepNum 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              Step {stepNum}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
          <span className="text-2xl">{guide.icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-[9.5px] px-2 py-0.5 rounded-full font-bold border ${guide.badgeColor}`}>
                Step {activeTab} 가이드
              </span>
            </div>
            <h3 className="text-sm font-bold text-white mt-1">{guide.title}</h3>
            <p className="text-[10px] text-slate-400">{guide.subtitle}</p>
          </div>
        </div>

        <p className="text-[11px] text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-900">
          {guide.description}
        </p>

        <div className="flex flex-col gap-2.5 my-1">
          {guide.items.map((item, idx) => (
            <div key={idx} className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80 flex flex-col gap-1">
              <span className="text-[10.5px] font-bold text-amber-400">{item.head}</span>
              <p className="text-[10px] text-slate-300 leading-relaxed">{item.body}</p>
            </div>
          ))}
        </div>

        <button
          onClick={onClose}
          className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-2.5 text-xs rounded-xl transition-all cursor-pointer border border-slate-700 mt-1 shadow-md"
        >
          확인 및 가이드 닫기
        </button>
      </div>
    </div>
  );
}
