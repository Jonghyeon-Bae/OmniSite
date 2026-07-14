'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function GatewayPage() {
  const router = useRouter();

  // 로그인 상태 및 입력 값
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(true);

  // 1. 이미 로그인된 상태일 경우 자동 지도 페이지로 리다이렉트
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = sessionStorage.getItem('token');
      const savedUser = sessionStorage.getItem('username');
      if (token && savedUser) {
        router.push('/spatial');
      } else {
        setLoading(false);
      }
    }
  }, [router]);

  // 2. 로그인 처리 핸들러
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      alert("아이디와 비밀번호를 모두 입력해 주십시오.");
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (res.ok) {
        const data = await res.json();
        sessionStorage.setItem('token', data.access_token);
        sessionStorage.setItem('username', data.user.username);
        sessionStorage.setItem('role', data.user.role);
        sessionStorage.setItem('department', data.user.department);
        sessionStorage.setItem('district_id', data.user.district_id);
        
        alert(`✓ ${data.user.username} 실무관님, 행정망 인증 성공. 소속: ${data.user.department}`);
        router.push('/spatial');
      } else {
        const errData = await res.json();
        alert(errData.detail || "로그인 인증에 실패했습니다. 정보를 재검토하십시오.");
        setLoading(false);
      }
    } catch (err) {
      alert("서버 연결에 실패했습니다. 백엔드 기동 여부를 확인해 주십시오.");
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400">
        <div className="animate-spin text-2xl mb-2">🔄</div>
        <p className="text-xs font-semibold">행정망 인증 세션 복구 및 권한 분석 중...</p>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 font-sans px-6 overflow-hidden">
      
      {/* Sleek Background Gradients */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      
      {/* Frame border */}
      <div className="absolute inset-4 border border-slate-900 pointer-events-none rounded-2xl" />
      
      {/* Main Container Card */}
      <div className="glass-panel w-full max-w-md p-8 rounded-2xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-md flex flex-col gap-6 shadow-2xl relative z-10 animate-fade-in">
        
        <div className="text-center">
          <span className="text-[10px] bg-blue-500/15 border border-blue-500/30 text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider">
            OmniSite SDSS Portal Gate
          </span>
          <h1 className="text-xl font-bold text-white mt-3">도시행정 입지선정지원 플랫폼</h1>
          <p className="text-[10px] text-slate-400 mt-1">
            소속 자치구 및 승인된 직위에 따라 공간 시뮬레이션 및 데이터 적재 기능이 조율됩니다.
          </p>
        </div>

        {/* 로그인 폼 */}
        <form onSubmit={handleLoginSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400 font-semibold">행정망 사용자 ID</label>
            <input 
              type="text"
              placeholder="ID 입력 (예: admin, officer)"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="bg-slate-950/60 border border-slate-800 focus:border-blue-500/80 rounded-lg p-2.5 text-xs text-white outline-none transition-all"
            />
          </div>
          
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400 font-semibold">인증 비밀번호</label>
            <input 
              type="password"
              placeholder="Password 입력"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-slate-950/60 border border-slate-800 focus:border-blue-500/80 rounded-lg p-2.5 text-xs text-white outline-none transition-all"
            />
          </div>

          <button 
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-3 rounded-lg transition-all shadow-lg hover:shadow-blue-500/10 cursor-pointer mt-2"
          >
            🔒 행정망 로그인 인증
          </button>
        </form>
        
        <span className="text-[9px] text-slate-600 text-center font-mono">
          OmniSite SDSS v1.0.0-prototype | Secure Internal Network Only
        </span>

      </div>
    </div>
  );
}
