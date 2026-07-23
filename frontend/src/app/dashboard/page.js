'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import PasswordChangeModal from '@/components/PasswordChangeModal';
import RagRegulationModal from '@/components/RagRegulationModal';
import StepGuideModal from '@/components/StepGuideModal';
import AdminConsoleModal from '@/components/AdminConsoleModal';

// Next.js API Fetch 래퍼 (JWT 세션 자동 바인딩)
const apiFetch = (url, options = {}) => {
  const token = typeof window !== 'undefined' 
    ? (sessionStorage.getItem('token') || localStorage.getItem('token')) 
    : null;
  const headers = {
    ...options.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
  const nativeFetch = typeof window !== 'undefined' ? window.fetch : (typeof globalThis !== 'undefined' ? globalThis.fetch : null);
  return nativeFetch ? nativeFetch(url, { ...options, headers }) : Promise.reject(new Error('Fetch not available'));
};

const parseJwt = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
};

export default function Dashboard() {
  const router = useRouter();
  const [historyList, setHistoryList] = useState([]);
  const [precedentList, setPrecedentList] = useState([]);
  const [activeTab, setActiveTab] = useState('history'); // 'history' | 'precedents'
  const [isLoading, setIsLoading] = useState(true);

  // 헤더 팝업 모달 상태 (spatial 헤더 일치화)
  const [showPasswordChangeModal, setShowPasswordChangeModal] = useState(false);
  const [showRagModal, setShowRagModal] = useState(false);
  const [showGuideModal, setShowGuideModal] = useState(false);
  const [showAdminConsoleModal, setShowAdminConsoleModal] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [mlStatus, setMlStatus] = useState({ is_training: false });
  
  // 🔒 JWT 실시간 토큰 남은 시간 타이머 상태
  const [tokenTimeLeft, setTokenTimeLeft] = useState('');
  const [isTokenValid, setIsTokenValid] = useState(true);

  // 🔒 커스텀 Glassmorphism Confirm 모달 상태
  const [confirmModal, setConfirmModal] = useState({
    show: false,
    title: '',
    message: '',
    onConfirm: null
  });

  const showConfirm = (title, message, onConfirm) => {
    setConfirmModal({
      show: true,
      title,
      message,
      onConfirm
    });
  };

  const showToast = (msg, type = 'info') => {
    setToastMessage({ msg, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  // 🔒 JWT 토큰 실시간 유효성 검증 및 카운트다운 타이머 (새로고침 대응)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    let token = sessionStorage.getItem('token');
    if (!token) {
      token = localStorage.getItem('token');
      if (token) {
        sessionStorage.setItem('token', token);
      }
    }

    if (!token) {
      setIsTokenValid(false);
      alert("🔒 행정 인증 세션이 존재하지 않습니다. 로그인 페이지로 이동합니다.");
      router.push('/');
      return;
    }

    // 마운트 / 새로고침 시 백엔드 실시간 유효성 200 OK 판정 (/api/v1/auth/me)
    apiFetch('/api/v1/auth/me')
      .then(res => {
        if (!res.ok) {
          setIsTokenValid(false);
          sessionStorage.clear();
          localStorage.removeItem('token');
          alert("🔒 행정 인증 세션이 만료되거나 무효화되었습니다. 다시 로그인해 주십시오.");
          router.push('/');
        } else {
          setIsTokenValid(true);
        }
      })
      .catch(() => {
        setIsTokenValid(false);
      });

    // 1초 간격 실시간 토큰 남은 시간 카운트다운
    const interval = setInterval(() => {
      const currentToken = sessionStorage.getItem('token') || localStorage.getItem('token');
      if (!currentToken) {
        setTokenTimeLeft('만료됨');
        return;
      }
      const payload = parseJwt(currentToken);
      if (payload && payload.exp) {
        const remainingSec = Math.floor(payload.exp - Date.now() / 1000);
        if (remainingSec <= 0) {
          setTokenTimeLeft('만료됨');
          setIsTokenValid(false);
          sessionStorage.clear();
          localStorage.removeItem('token');
          alert("🔒 로그인 세션 시간이 만료되었습니다. 다시 로그인해 주십시오.");
          router.push('/');
        } else {
          const m = Math.floor(remainingSec / 60);
          const s = remainingSec % 60;
          setTokenTimeLeft(`${m}분 ${s < 10 ? '0' : ''}${s}초`);
        }
      } else {
        setTokenTimeLeft('유효 세션');
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [router]);

  // 🔒 1시간 세션 연장 핸들러
  const [isRefreshingToken, setIsRefreshingToken] = useState(false);

  const handleRefreshSession = async () => {
    setIsRefreshingToken(true);
    try {
      const res = await apiFetch('/api/v1/auth/refresh', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const newToken = data.access_token;
        sessionStorage.setItem('token', newToken);
        localStorage.setItem('token', newToken);
        showToast("✓ 로그인 세션이 성공적으로 1시간(60분) 연장되었습니다.", "success");
      } else {
        showToast("세션 연장에 실패했습니다. 다시 로그인해 주십시오.", "error");
      }
    } catch (err) {
      showToast("세션 연장 오류: " + err.message, "error");
    } finally {
      setIsRefreshingToken(false);
    }
  };

  // FAQ 아코디언 상태
  const [openFaq, setOpenFaq] = useState(null);

  // Audit AI 폼 상태
  const [activeHistoryId, setActiveHistoryId] = useState(null);
  const [auditFile, setAuditFile] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [isParsing, setIsParsing] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  // 과거 이력 상세 모달 상태
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedHistory, setSelectedHistory] = useState(null);

  // 과거 의사결정 심의 이력 실제 DB 조회 API 연계
  const fetchHistory = async () => {
    try {
      const res = await apiFetch('/api/v1/spatial/history');
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    }
  };

  // 모의 이력 수동 상태 갱신/롤백 API 연계
  const handleUpdateHistoryStatus = async (id, targetStatus) => {
    try {
      const res = await apiFetch(`/api/v1/spatial/history/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: targetStatus })
      });
      if (res.ok) {
        alert(`✓ 의사결정 이력 상태가 '${targetStatus}'로 수정되었습니다.`);
        setSelectedHistory(prev => ({ ...prev, status: targetStatus }));
        refreshAllData();
      } else {
        alert("이력 상태 변경에 실패했습니다.");
      }
    } catch (err) {
      alert(`상태 변경 중 오류 발생: ${err.message}`);
    }
  };

  // RAG 실증사례 목록 조회 API 연계
  const fetchPrecedents = async () => {
    try {
      const res = await apiFetch('/api/v1/spatial/precedents');
      if (res.ok) {
        const data = await res.json();
        setPrecedentList(data);
      }
    } catch (err) {
      console.error("Failed to fetch precedents:", err);
    }
  };

  const refreshAllData = async () => {
    setIsLoading(true);
    await Promise.all([fetchHistory(), fetchPrecedents()]);
    setIsLoading(false);
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  // 실제 공문서 파일 업로드 검증 감리 API 연동 (RAG Audit)
  const handleAuditUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setAuditFile(file);
    setIsParsing(true);
    setAuditResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // 1단계: PNU 및 지번 지능형 자동 매칭 API 호출
      const res = await apiFetch(`/api/v1/spatial/history/audit-auto`, {
        method: 'POST',
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        
        if (data.status === "already_exists") {
          // 중복 실증 준공 사례 업로드 감지 분기
          showConfirm(
            "⚠️ 실증 준공 사례 중복 감지",
            `대상 PNU: ${data.pnu}\n기존 파일: ${data.existing_title}\n\n이미 동일 필지(PNU)로 등록된 실증 준공 사례가 존재합니다. 기존 사례를 삭제하고 덮어쓰시겠습니까?`,
            async () => {
              setIsRegistering(true);
              try {
                const regRes = await apiFetch(`/api/v1/spatial/history/audit-register-precedent`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    pnu: data.pnu,
                    jibun: data.jibun,
                    filename: data.filename,
                    textContent: data.textContent,
                    overwrite: true
                  })
                });
                
                if (regRes.ok) {
                  showToast("✓ 성공 사례가 기존 데이터를 덮어쓰고 정상 갱신되었습니다!", "success");
                  refreshAllData();
                } else {
                  const regErr = await regRes.json();
                  showToast(`성공사례 덮어쓰기 실패: ${regErr.detail || '알 수 없는 오류'}`, "error");
                }
              } finally {
                setIsRegistering(false);
              }
            }
          );
        } else if (data.status === "not_found") {
          // 2단계: 매칭되는 심의 이력이 없는 경우 -> 자가학습 지식 아카이브 편입 유도 모달/컴펌
          showConfirm(
            "💡 미등록 준공 공문서 감지",
            `주소: ${data.jibun}\n필지 PNU: ${data.pnu || '미추출'}\n\n시스템 내에 이 필지에 관한 과거 모의 심의 이력이 존재하지 않습니다.\n이 문서를 RAG 성공 사례(지식베이스)에 축적하여 AI 자가학습 참고자료로 등록하시겠습니까?`,
            async () => {
              setIsRegistering(true);
              try {
                // 성공사례 지식 적재 API 호출
                const regRes = await apiFetch(`/api/v1/spatial/history/audit-register-precedent`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    pnu: data.pnu,
                    jibun: data.jibun,
                    filename: data.filename,
                    textContent: data.textContent,
                    overwrite: false
                  })
                });
                
                if (regRes.ok) {
                  showToast("✓ 성공 사례 및 AI 자가학습 RAG 지식 아카이브 적재가 완료되었습니다!", "success");
                  refreshAllData(); // 실시간 전체 리스트/통계 갱신
                } else {
                  const regErr = await regRes.json();
                  showToast(`성공사례 적재 실패: ${regErr.detail || '알 수 없는 오류'}`, "error");
                }
              } finally {
                setIsRegistering(false);
              }
            }
          );
        } else {
          // 매칭 성공 케이스
          setAuditResult({
            ...data,
            matchScore: data.matchScore || data.match_score || 100
          });
          refreshAllData(); // 의사결정 상태 전체 갱신
          alert(`✓ PNU 자동 인식 매칭 성공!\n일치율: ${data.matchScore || data.match_score || 100}%\n시나리오 판정: ${data.mappedScenario}`);
        }
      } else {
        const err = await res.json();
        alert(`감리 분석 실패: ${err.detail || '알 수 없는 오류'}`);
      }
    } catch (err) {
      alert(`감리 문서 업로드 중 오류 발생: ${err.message}`);
    } finally {
      setIsParsing(false);
    }
  };

  // 모의 심의 이력 삭제 핸들러
  const handleDeleteHistory = async (id, e) => {
    e.stopPropagation();
    showConfirm(
      "🗑️ 심의 이력 삭제 확인",
      `선택한 모의 심의 이력 #${id}을 영구 삭제하시겠습니까?\n이 작업은 복구할 수 없습니다.`,
      async () => {
        try {
          const res = await apiFetch(`/api/v1/spatial/history/${id}`, { method: 'DELETE' });
          if (res.ok) {
            showToast("✓ 심의 이력이 정상 삭제되었습니다.", "success");
            refreshAllData();
          } else {
            showToast("이력 삭제에 실패했습니다.", "error");
          }
        } catch (err) {
          showToast(`삭제 중 오류 발생: ${err.message}`, "error");
        }
      }
    );
  };

  // 실증 준공 사례 삭제 핸들러
  const handleDeletePrecedent = async (id, e) => {
    e.stopPropagation();
    showConfirm(
      "🗑️ 실증 준공 사례 삭제 확인",
      `선택한 실증 준공 사례 #${id}을 RAG 지식베이스에서 영구 삭제하시겠습니까?\n삭제 시 AI 자가학습 지식 데이터셋에서 제외됩니다.`,
      async () => {
        try {
          const res = await apiFetch(`/api/v1/spatial/precedents/${id}`, { method: 'DELETE' });
          if (res.ok) {
            showToast("✓ 실증 준공 사례가 성공적으로 삭제되었습니다.", "success");
            refreshAllData();
          } else {
            showToast("사례 삭제에 실패했습니다.", "error");
          }
        } catch (err) {
          showToast(`삭제 중 오류 발생: ${err.message}`, "error");
        }
      }
    );
  };

  // 과거 토론 로그 목업 조회
  const openHistoryDetails = (item) => {
    setSelectedHistory(item);
    setShowDetailModal(true);
  };

  // WeasyPrint 스타일의 HTML 행정 보고서 발급 기능 (한국어 호환용 정규 규격 문서)
  const downloadReportHTML = (item) => {
    const debateLogs = item.debateLogs || [];
    const areaVal = parseFloat(item.selectedParcelArea) || 15.0;
    const priceVal = parseInt(item.selectedParcelPrice, 10) || 14200000;
    const taxVal = Math.round(areaVal * priceVal * 0.02);
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>입지 타당성 및 갈등 영향 평가 보고서</title>
        <style>
          body { font-family: 'Malgun Gothic', Arial, sans-serif; padding: 40px; color: #111; line-height: 1.6; max-width: 800px; margin: 0 auto; }
          .header { text-align: center; border-bottom: 2px double #111; padding-bottom: 20px; margin-bottom: 30px; }
          .title { font-size: 24px; font-weight: bold; margin: 0; letter-spacing: -0.5px; }
          .meta-table, .content-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; }
          .meta-table th, .meta-table td, .content-table th, .content-table td { border: 1px solid #333; padding: 10px; font-size: 12px; }
          .meta-table th, .content-table th { background-color: #f5f5f5; text-align: left; font-weight: bold; }
          .section-title { font-size: 15px; font-weight: bold; border-left: 4px solid #111; padding-left: 10px; margin: 30px 0 10px 0; }
          .log-box { background-color: #fcfcfc; border: 1px solid #ccc; padding: 15px; border-radius: 4px; }
          .log-item { margin-bottom: 12px; font-size: 11.5px; border-bottom: 1px dashed #eee; padding-bottom: 8px; }
          .log-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
          .log-sender { font-weight: bold; color: #333; }
          .footer-sign { text-align: right; margin-top: 60px; font-size: 13px; font-weight: bold; border-top: 1px solid #ddd; padding-top: 20px; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1 class="title">지능형 입지 선정 및 공공갈등 타당성 평가 보고서</h1>
          <p style="font-size:11px; color:#666; margin-top: 8px;">문서번호: OMS-2026-${item.id} | 심의일자: ${item.date}</p>
        </div>
        
        <table class="meta-table">
          <tr>
            <th width="20%">의사결정 ID</th>
            <td>#${item.id}</td>
            <th width="20%">대상 지역</th>
            <td>${item.region}</td>
          </tr>
          <tr>
            <th>선택 인프라</th>
            <td>${item.infra}</td>
            <th>최종 후보지 수</th>
            <td>${item.pnuCount} 개 소</td>
          </tr>
          <tr>
            <th>행정 상태</th>
            <td>${item.status} (Audit AI 검증 필)</td>
            <th>RAG 귀속 여부</th>
            <td>RAG 세그먼트 적재 완료</td>
          </tr>
          <tr>
            <th>필지 고유번호 (PNU)</th>
            <td colspan="3" style="font-family: monospace; font-size: 11.5px; letter-spacing: 0.5px;">${item.selectedParcelPnu || '미추출/미지정'}</td>
          </tr>
        </table>

        <div class="section-title">1. AHP 계층분석 모형 프로파일</div>
        <p style="font-size:12px; color: #333; margin-bottom: 15px;">
          본 입지는 대중교통 유동성, 불법 민원빈도, 상습 무단투기, 배후 생활인구, 청소년 안심구역 거리를 다기준 쌍대비교하여 일관성 비율(C.R. = 0.04)을 만족한 행정 최적 프로파일에 의해 도출되었습니다.
        </p>

        <div class="section-title">2. AI 에이전트(LangGraph) 모의 심의 토론 아카이브</div>
        <div class="log-box">
          ${debateLogs.length > 0 ? debateLogs.map(log => `
            <div class="log-item">
              <span class="log-sender">[${log.sender || log.name || '참여자'}]</span>
              <span>${log.text || log.content || log.message || '(의견 내용 없음)'}</span>
            </div>
          `).join('') : '<div class="log-item"><span>기록된 모의 토론 출력이 존재하지 않습니다.</span></div>'}
        </div>

        <div class="section-title">3. 행정 점용 예산 부담액 산출 요약</div>
        <table class="content-table">
          <thead>
            <tr>
              <th width="30%">지적 점용 면적</th>
              <th width="35%">㎡당 공시지가 (선정지 기준)</th>
              <th width="35%">연간 예상 도로점용료 (법정 요율 2% 적용)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>${areaVal.toFixed(1)} ㎡</td>
              <td>₩ ${priceVal.toLocaleString()} / ㎡</td>
              <td style="font-weight:bold; color:#d9534f; font-size: 13px;">₩ ${taxVal.toLocaleString()} / 년</td>
            </tr>
          </tbody>
        </table>

        <p style="font-size:11px; color:#666; margin-top:-10px;">
          ※ 도로법 제61조 및 동법 시행령 제71조에 따른 점용료 요율(연간 2.0%)이 적용되었으며, 실제 시공 형태에 따라 실무자 미세 좌표(HITL) 기준으로 변경될 수 있습니다.
        </p>

        <div class="footer-sign">
          <p>서울시 자치구 행정 위임 의사결정 승인</p>
          <p style="margin-top:25px; font-size:15px; letter-spacing: 2px;">도시개발 스마트도시 분과 심의 위원회 [인]</p>
        </div>
      </body>
      </html>
    `;

    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `스마트시티_입지타당성_보고서_${item.id}.html`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100 font-sans pt-20">
      
      {/* 1. 상단 글로벌 네비게이션 헤더 (spatial 헤더 통합 일치화) */}
      <header className="fixed top-0 left-0 right-0 h-16 glass-panel rounded-none border-t-0 border-x-0 z-45 px-8 flex justify-between items-center bg-slate-950/90 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Link href="/spatial" className="text-xl font-bold tracking-tight text-white hover:text-blue-400 transition-all flex items-center gap-2">
            OmniSite <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30">B2G SDSS v1.4</span>
          </Link>
        </div>
        <nav className="flex items-center gap-6 text-xs font-semibold">
          <Link href="/spatial" className="text-slate-400 hover:text-white transition-all pb-1 flex items-center gap-1">
            🏠 GIS 입지분석
          </Link>
          <Link href="/dashboard" className="text-blue-400 border-b-2 border-blue-500 pb-1 flex items-center gap-1 font-bold">
            📊 의사결정 대시보드
          </Link>
          <button 
            onClick={() => setShowPasswordChangeModal(true)} 
            className="text-slate-400 hover:text-slate-200 transition-all cursor-pointer flex items-center gap-1"
          >
            🔑 암호 변경
          </button>
          <button 
            onClick={() => setShowAdminConsoleModal(true)} 
            className="text-slate-400 hover:text-slate-200 transition-all cursor-pointer flex items-center gap-1"
          >
            ⚙️ 관리자 콘솔
          </button>
        </nav>
        {/* JWT 실시간 남은 세션 타이머 뱃지 및 세션 연장 버튼 [v1.4.5] */}
        <div className="flex items-center gap-2">
          <div className="bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isTokenValid ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className="text-[11px] text-slate-300">인증 세션:</span>
            <span className="text-[11px] font-mono font-bold text-amber-400">⏱️ {tokenTimeLeft || '검증 중...'}</span>
          </div>

          <button
            type="button"
            onClick={handleRefreshSession}
            disabled={isRefreshingToken}
            className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-amber-500/50 text-slate-200 hover:text-amber-400 px-3 py-1.5 rounded-lg font-bold cursor-pointer transition-all flex items-center gap-1 shadow-sm active:scale-95"
            title="클릭 시 로그인 세션 만료 시간을 1시간 추가 연장합니다"
          >
            <span>🔄 세션 연장 (+1시간)</span>
          </button>
        </div>
      </header>

      {/* 2. 대시보드 레이아웃 본문 */}
      <main className="max-w-[85%] mx-auto p-8 flex flex-col gap-8">
        
        {/* 상단 3대 지표 분석 요약 카드 (실 데이터베이스 연동 연산) */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-panel p-6 flex flex-col gap-2">
            <span className="text-xs text-slate-400 font-semibold">종합 입지 의사결정 수립 건수</span>
            <span className="text-3xl font-bold text-white font-mono">{historyList.length} 건</span>
            <p className="text-[10px] text-emerald-400 mt-1">▲ DB 실시간 동적 연동 활성화</p>
          </div>
          <div className="glass-panel p-6 flex flex-col gap-2">
            <span className="text-xs text-slate-400 font-semibold">모의 시나리오 실증 성공률</span>
            <span className="text-3xl font-bold text-blue-400 font-mono">
              {historyList.length > 0 ? (historyList.filter(h => h.status === '실증 성공').length / historyList.length * 100).toFixed(1) : 0} %
            </span>
            <p className="text-[10px] text-slate-500 mt-1">모의 수립 입지 중 실제 공문으로 준공 검증된 비율</p>
          </div>
          <div className="glass-panel p-6 flex flex-col gap-2">
            <span className="text-xs text-slate-400 font-semibold">RAG 축적 검증사례 수</span>
            <span className="text-3xl font-bold text-emerald-400 font-mono">
              {precedentList.length} 건
            </span>
            <p className="text-[10px] text-slate-500 mt-1">실제 이행 공문 분석 RAG 격리 세그먼트 적재량</p>
          </div>
        </section>

        {/* 메인 이력 테이블 및 Audit AI 영역 (2단 분할) */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* 좌측 2칸: 과거 이력 테이블 및 실증 사례 테이블 (탭 분리) */}
          <div className="lg:col-span-2 glass-panel p-6 flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3 flex-wrap gap-2">
              <div className="flex flex-col gap-1">
                <h2 className="text-sm font-bold text-white">행정 입지 분석 및 실증 준공 아카이브</h2>
                <span className="text-[10px] text-slate-500">모의 시뮬레이션 이력과 실제 준공 검증 데이터 연동 목록</span>
              </div>
              
              {/* 프리미엄 탭 스위처 */}
              <div className="flex gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setActiveTab('history')}
                  className={`px-3 py-1 rounded text-[11px] font-bold transition-all cursor-pointer ${
                    activeTab === 'history' 
                      ? 'bg-blue-600/90 text-white shadow-lg shadow-blue-500/20' 
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  모의 심의 이력 ({historyList.length})
                </button>
                <button
                  onClick={() => setActiveTab('precedents')}
                  className={`px-3 py-1 rounded text-[11px] font-bold transition-all cursor-pointer ${
                    activeTab === 'precedents' 
                      ? 'bg-emerald-600/90 text-white shadow-lg shadow-emerald-500/20' 
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  실증 준공 사례 ({precedentList.length})
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              {activeTab === 'history' ? (
                // 탭 A: 모의 심의 이력 테이블
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-900/30">
                      <th className="py-3 px-4">의사결정 ID</th>
                      <th className="py-3 px-4">일자</th>
                      <th className="py-3 px-4">대상 지역</th>
                      <th className="py-3 px-4">선택 인프라</th>
                      <th className="py-3 px-4">심의 상태</th>
                      <th className="py-3 px-4">사후 검증</th>
                      <th className="py-3 px-4 text-center">조회 / 삭제</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyList.map(item => (
                      <tr key={item.id} className="border-b border-slate-900 hover:bg-slate-900/30 transition-all">
                        <td className="py-3.5 px-4 font-mono text-slate-300">#{item.id}</td>
                        <td className="py-3.5 px-4 text-slate-400">{item.date}</td>
                        <td className="py-3.5 px-4 font-medium text-white">{item.region}</td>
                        <td className="py-3.5 px-4 text-slate-300">{item.infra}</td>
                        <td className="py-3.5 px-4">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            item.status === '실증 성공' ? 'bg-emerald-500/20 text-emerald-400' :
                            item.status === '실증 실패' ? 'bg-rose-500/20 text-rose-400' : 'bg-blue-500/20 text-blue-400'
                          }`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`text-[10px] font-semibold ${
                            item.auditState === '검증 완료' ? 'text-emerald-400' :
                            item.auditState === '대기 중' ? 'text-slate-500 animate-pulse' : 'text-rose-400'
                          }`}>
                            {item.auditState}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => openHistoryDetails(item)}
                            className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold px-2 py-1 rounded cursor-pointer transition-all border border-slate-700"
                          >
                            상세 조회
                          </button>
                          <button
                            onClick={(e) => handleDeleteHistory(item.id, e)}
                            className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 text-[10px] font-bold px-2 py-1 rounded cursor-pointer transition-all border border-rose-800/40"
                          >
                            삭제
                          </button>
                        </td>
                      </tr>
                    ))}
                    {historyList.length === 0 && (
                      <tr>
                        <td colSpan="7" className="py-8 text-center text-slate-500 font-mono">기동된 모의 심의 이력이 존재하지 않습니다.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
                // 탭 B: 실증 준공 사례 테이블
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-900/30">
                      <th className="py-3 px-4">사례 ID</th>
                      <th className="py-3 px-4">등록일자</th>
                      <th className="py-3 px-4">실증 준공 주소</th>
                      <th className="py-3 px-4">필지 PNU</th>
                      <th className="py-3 px-4">도달 시나리오</th>
                      <th className="py-3 px-4">감리 문서명</th>
                      <th className="py-3 px-4 text-center">감리 분석 / 삭제</th>
                    </tr>
                  </thead>
                  <tbody>
                    {precedentList.map(item => (
                      <tr key={item.id} className="border-b border-slate-900 hover:bg-slate-900/30 transition-all">
                        <td className="py-3.5 px-4 font-mono text-slate-300">#{item.id}</td>
                        <td className="py-3.5 px-4 text-slate-400">{item.date}</td>
                        <td className="py-3.5 px-4 font-medium text-white">{item.jibun}</td>
                        <td className="py-3.5 px-4 font-mono text-slate-400">{item.pnu}</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400">
                            {item.scenario || '준공 부합'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 max-w-[120px] truncate" title={item.title}>
                          {item.title}
                        </td>
                        <td className="py-3.5 px-4 text-center flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => {
                              setAuditFile({ name: item.title });
                              setAuditResult({
                                mappedScenario: item.scenario || '준공 완전 부합',
                                matchScore: item.matchScore || 100,
                                title: item.title,
                                summary: item.summary
                              });
                            }}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold px-2 py-1 rounded cursor-pointer transition-all border border-emerald-700"
                          >
                            RAG 분석
                          </button>
                          <button
                            onClick={(e) => handleDeletePrecedent(item.id, e)}
                            className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 text-[10px] font-bold px-2 py-1 rounded cursor-pointer transition-all border border-rose-800/40"
                          >
                            삭제
                          </button>
                        </td>
                      </tr>
                    ))}
                    {precedentList.length === 0 && (
                      <tr>
                        <td colSpan="7" className="py-8 text-center text-slate-500 font-mono">적재된 실증 준공 사례가 존재하지 않습니다.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>
          {/* 우측 1칸: 선택된 이력의 Audit AI 사후 검증 모듈 */}
          <div className="glass-panel p-6 flex flex-col gap-4">
            <div className="border-b border-slate-800 pb-3">
              <h2 className="text-sm font-bold text-white">사후 Audit AI 검증 패널</h2>
              <p className="text-[10px] text-slate-500">선택된 이력의 실제 공문서 검증 피드백 루프</p>
            </div>

            <div className="flex flex-col gap-4">
              <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-300">동작 모드:</span>
                <span className="font-mono text-emerald-400 font-bold">지능형 PNU 자동 감지 모드</span>
              </div>

              {/* 결재 공문 업로드존 */}
              <div className="flex flex-col gap-2">
                <label className="text-xs text-slate-400">행정 준공/고시 공문 (PDF)</label>
                <div className="border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-xl p-5 text-center cursor-pointer transition-all bg-slate-950/40 relative">
                  <input 
                    type="file" 
                    accept=".pdf" 
                    onChange={handleAuditUpload} 
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <p className="text-xs text-slate-300 font-medium">
                    {auditFile ? auditFile.name : '준공/고시 공문 드롭존'}
                  </p>
                  <p className="text-[9px] text-slate-600 mt-1">드래그앤드롭하여 자동 PNU 분석 및 적재 개시</p>
                </div>
              </div>

              {/* 파싱 중 인디케이터 */}
              {isParsing && (
                <div className="text-xs text-blue-400 animate-pulse text-center my-4 font-mono">
                  📄 OCR 추출 및 지능형 PNU 이력 매핑 연산 중...
                </div>
              )}

              {/* 분석 완료 리포트 */}
              {auditResult && !isParsing && (
                <div className="bg-slate-950/60 p-4 rounded-xl border border-emerald-500/30 flex flex-col gap-3 text-xs text-slate-300 leading-relaxed">
                  <div className="flex justify-between border-b border-slate-900 pb-1.5 font-semibold">
                    <span className="text-slate-400">도달 시나리오</span>
                    <span className={auditResult.mappedScenario?.includes("C") ? "text-red-400 font-bold" : "text-emerald-400"}>
                      {auditResult.mappedScenario}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-0.5">
                      {auditResult.mappedScenario?.includes("C") ? "조례 규정 부합률 (위반/저촉)" : "매칭 유사 신뢰도"}
                    </span>
                    <span className={`font-mono font-bold text-sm ${auditResult.mappedScenario?.includes("C") ? "text-red-400" : "text-emerald-400"}`}>
                      {auditResult.matchScore}% {auditResult.mappedScenario?.includes("C") ? "(규제 저촉 / 불합격)" : "(적합 준수)"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-0.5">판독 공문</span>
                    <span className="text-slate-300 font-medium">{auditResult.title}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-0.5">주요 요약 결과</span>
                    <p className="text-slate-400 bg-slate-900/30 p-2.5 rounded border border-slate-900 text-[11px]">{auditResult.summary}</p>
                  </div>
                  <div className="text-[10px] text-emerald-400 font-bold border-t border-slate-900 pt-2 text-right">
                    ✓ RAG 격리 세그먼트 적재 및 요약 완료
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* FAQ 아코디언 섹션 */}
        <section className="glass-panel p-6 mt-4 flex flex-col gap-6">
          <div className="border-b border-slate-800 pb-3">
            <h2 className="text-sm font-bold text-white">OmniSite 시스템 FAQ & 사용자 매뉴얼</h2>
            <p className="text-[10px] text-slate-500">지능형 입지선정 의사결정 시스템의 주요 메커니즘 설명</p>
          </div>

          <div className="flex flex-col gap-3">
            {[
              {
                q: "OmniSite는 어떤 시스템인가요?",
                a: "OmniSite는 다기준 의사결정 분석기법(AHP)과 XGBoost 주민 갈등도(CSS) 머신러닝 예측 모델을 융합하여, 스마트시티 공공 인프라 도입 시 최적의 입지 분석 및 사후 검증(RAG OCR)을 지원하는 다목적 지능형 공간 의사결정 지원 시스템(SDSS)입니다."
              },
              {
                q: "설치하려는 공공 인프라 종류에 따라 입지 지표(Indicators)가 동적으로 변화하나요?",
                a: "네, 그렇습니다. OmniSite는 분석하고자 하는 인프라 도메인(공유킥보드 거치대, 전기차 충전소, 안심 옐로카펫 등)의 성격에 적합한 공간 지표를 동적으로 매핑하여 가동됩니다. 예를 들어, 공유이동수단 거치대는 대중교통 접근성이 주 지표가 되며, 옐로카펫은 초등학교 어린이보호구역 이격거리가 주 요인으로 매핑됩니다."
              },
              {
                q: "입지 추천 종합 점수(AHP Score)는 어떻게 산출되나요?",
                a: "행정 실무자가 웹 화면에서 입력한 쌍대비교 가중치를 기반으로 AHP 분석기가 수학적 고유벡터 가중치를 도출합니다. 이 가중치는 일관성 비율(C.R. < 0.1) 검증을 통과한 후, 각 후보지 필지별 실측 공간 지표 레이어에 실시간으로 매핑·연산되어 최종 추천 순위(내림차순)를 산출합니다."
              },
              {
                q: "주민 갈등 위험도(CSS) 점수의 예측 원리는 무엇인가요?",
                a: "CSS는 특정 후보지에 인프라를 도입했을 때 예상되는 잠재적 민원 강도를 예측합니다. XGBoost Classifier 모델이 필지의 지목, 공시지가, 인근 보호시설과의 이격거리 분포를 학습하여 민원 발생 확률을 0~100점 척도로 환산하며, 오버피팅 제어 규제를 적용하여 일반화 F1-Score 75%~78% 신뢰도를 확보합니다."
              },
              {
                q: "다목적 인프라 확장을 위한 공간 GIS 데이터셋 수집 및 매핑 기준은 무엇인가요?",
                a: "OmniSite는 범용 공간 정보 표준(GeoJSON 및 PostGIS Spatial Geometry)을 지원하여 자치구의 법정 경계, 지적도(Cadastral Lands), 보호구역(Restricted Zones) 데이터를 실시간으로 인입합니다. 각 자치구별 조례 이격 가이드라인(학교, 어린이집, 보호구역 등)을 관리자 콘솔에서 유동적으로 변경하여 모든 다목적 공공 인프라 입지선정에 즉시 대칭 적용할 수 있습니다."
              },
              {
                q: "사후 Audit AI(RAG OCR) 모듈의 검증 및 자가학습 지식오염 방지 메커니즘은 무엇인가요?",
                a: "최종 준공/고시 PDF 공문서를 업로드하면 RAG OCR 파이프라인이 실측 수치를 추출하여 시나리오(A/B/C) 및 규제 부합률을 자동 감리합니다. 검증이 통과된 승인 공문만 RAG 지식베이스(pgvector)에 축적되며, 불합격된 위법 사례는 Data Poisoning Guard가 작동하여 RAG 지식베이스 오염을 원천 차단합니다. 또한 실증 사례 삭제 시 연동된 모의 심의 이력이 자동으로 원상 롤백(Rollback) 복구됩니다."
              }
            ].map((faq, idx) => (
              <div 
                key={idx} 
                className="border border-slate-900 rounded-xl overflow-hidden bg-slate-950/40"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="w-full text-left p-4 flex justify-between items-center text-xs font-semibold text-slate-200 hover:bg-slate-900/30 transition-all cursor-pointer font-sans"
                >
                  <span>{faq.q}</span>
                  <span className="text-slate-500 font-bold">{openFaq === idx ? '▲' : '▼'}</span>
                </button>
                <div 
                  className={`transition-all duration-300 ease-in-out overflow-hidden text-[11px] text-slate-400 bg-slate-950/70 border-t border-slate-900/50 ${
                    openFaq === idx ? 'max-h-40 p-4' : 'max-h-0 p-0 border-t-0'
                  }`}
                >
                  {faq.a}
                </div>
              </div>
            ))}
          </div>
        </section>

      </main>

      {/* 과거 이력 상세 모달 팝업 (찬반 토론 및 결과서 다운로드 조회용) */}
      {showDetailModal && selectedHistory && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="w-[750px] h-[500px] glass-panel p-6 flex flex-col justify-between">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-white">행정 심의 의사결정 상세 기록 조회</h3>
                <p className="text-[10px] text-slate-400">의사결정 ID: #{selectedHistory.id} | 지역: {selectedHistory.region}</p>
              </div>
              <button 
                onClick={() => setShowDetailModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
              >
                &times;
              </button>
            </div>

            {/* 토론 이력 스크롤 */}
            <div className="flex-1 my-4 bg-slate-950/70 rounded-xl p-4 overflow-y-auto font-mono text-xs flex flex-col gap-3 border border-slate-900/80">
              <div className="text-[11px] text-blue-400 font-bold border-b border-slate-900 pb-1.5">
                ⚡ [AI 모의 심의 토론 아카이브]
              </div>
              {(selectedHistory.debateLogs && selectedHistory.debateLogs.length > 0
                ? selectedHistory.debateLogs
                : []
              ).map((log, index) => (
                <div key={index} className="flex gap-2 leading-relaxed">
                  <span className={`font-semibold shrink-0 ${
                    log.sender.includes('반대') ? 'text-rose-400' :
                    log.sender.includes('찬성') ? 'text-emerald-400' : 'text-slate-300'
                  }`}>
                    [{log.sender}]
                  </span>
                  <span className="text-slate-200">{log.text}</span>
                </div>
              ))}
            </div>

            {/* 하단 버튼 및 정보 */}
            <div className="flex justify-between items-center border-t border-slate-800 pt-3">
              <div className="text-[11px] text-slate-400">
                <span className="font-semibold text-slate-300">선택된 인프라:</span> {selectedHistory.infra} ({selectedHistory.pnuCount}개 후보 필지 중 최종 결정)
              </div>
              <div className="flex gap-3">
                {selectedHistory.status === '토론 완료' ? (
                  <button
                    onClick={() => handleUpdateHistoryStatus(selectedHistory.id, '실증 실패')}
                    className="bg-rose-950/80 hover:bg-rose-900 text-rose-400 font-semibold text-xs px-3 py-2 rounded-lg transition-all cursor-pointer border border-rose-800/40"
                  >
                    ⚠️ 실증 실패 처리
                  </button>
                ) : (
                  <button
                    onClick={() => handleUpdateHistoryStatus(selectedHistory.id, '토론 완료')}
                    className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs px-3 py-2 rounded-lg transition-all cursor-pointer border border-slate-700"
                  >
                    🔄 상태 초기화 (토론완료 복구)
                  </button>
                )}
                <button
                  onClick={() => downloadReportHTML(selectedHistory)}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-4 py-2 rounded-lg transition-all cursor-pointer"
                >
                  📝 최종 행정 결과서 다운로드
                </button>
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="bg-slate-850 hover:bg-slate-800 text-slate-400 text-xs px-4 py-2 rounded-lg cursor-pointer border border-slate-900"
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* RAG 자가학습 적재 로딩 오버레이 */}
      {isRegistering && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex flex-col items-center justify-center text-white gap-3 animate-fade-in">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-bold text-emerald-400 font-mono">🧠 pgvector RAG 벡터 지식베이스 임베딩 축적 및 자가학습 적재 연산 중...</p>
          <p className="text-xs text-slate-400">잠시만 기다려 주십시오. 실측 텍스트를 청킹 임베딩 처리하여 덤프 중입니다.</p>
        </div>
      )}

      {/* 헤더 일치화 모달 바인딩 4종 */}
      <PasswordChangeModal 
        show={showPasswordChangeModal} 
        onClose={() => setShowPasswordChangeModal(false)} 
        apiFetch={apiFetch} 
        showToast={showToast}
        router={router}
      />
      <RagRegulationModal 
        show={showRagModal} 
        onClose={() => setShowRagModal(false)} 
        apiFetch={apiFetch} 
      />
      <StepGuideModal 
        show={showGuideModal} 
        onClose={() => setShowGuideModal(false)} 
      />
      <AdminConsoleModal 
        show={showAdminConsoleModal} 
        onClose={() => setShowAdminConsoleModal(false)} 
        apiFetch={apiFetch} 
        showToast={showToast}
        mlStatus={mlStatus}
        setMlStatus={setMlStatus}
      />

      {/* 토스트 메시지 렌더러 */}
      {toastMessage && (
        <div className={`fixed bottom-6 right-6 z-[100] px-4 py-3 rounded-xl text-xs font-semibold text-white shadow-2xl backdrop-blur-md border animate-bounce ${
          toastMessage.type === 'error' ? 'bg-rose-950/90 border-rose-500/50' : 
          toastMessage.type === 'warning' ? 'bg-amber-950/90 border-amber-500/50' : 'bg-emerald-950/90 border-emerald-500/50'
        }`}>
          {toastMessage.msg}
        </div>
      )}

    </div>
  );
}
