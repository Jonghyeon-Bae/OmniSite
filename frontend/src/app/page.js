'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { OMNISITE_VERSION } from '../config/version';

export default function GatewayPage() {
  const router = useRouter();

  // 로그인 상태 및 입력 값
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(true);

  // 최초 로그인 시 패스워드 강제 변경 모달 제어
  const [showResetModal, setShowResetModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [resetLoading, setResetLoading] = useState(false);

  // 1. 이미 로그인된 상태일 경우 백엔드 실시간 토큰 검증 후 지도 페이지로 자동 리다이렉트
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = sessionStorage.getItem('token');
      const savedUser = sessionStorage.getItem('username');
      if (token && savedUser) {
        fetch('/api/v1/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => {
          if (res.ok) {
            router.push('/spatial');
          } else {
            sessionStorage.clear();
            setLoading(false);
          }
        })
        .catch(() => {
          setLoading(false);
        });
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
        
        if (data.require_password_change) {
          // 최초 로그인 패스워드 강제 변경 유도 가동
          alert(`⚠️ 보안 수칙 경고: 최초 로그인(혹은 기본 비밀번호 감출) 상태입니다. 안전을 위해 관리자 인증 비밀번호를 즉시 변경해야 합니다.`);
          setShowResetModal(true);
          setLoading(false);
        } else {
          alert(`✓ ${data.user.username} 실무관님, 행정망 인증 성공. 소속: ${data.user.department}`);
          router.push('/spatial');
        }
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

  // 3. 강제 패스워드 변경 처리 핸들러
  const handleForcePasswordChange = async (e) => {
    e.preventDefault();
    if (!newPassword || !newPasswordConfirm) {
      alert("신규 비밀번호를 입력해 주십시오.");
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      alert("신규 비밀번호와 비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    if (newPassword === "admin1234") {
      alert("보안 정책상 기본 비밀번호('admin1234')는 재사용할 수 없습니다.");
      return;
    }
    const hasLetter = /[A-Za-z]/.test(newPassword);
    const hasDigit = /\d/.test(newPassword);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newPassword);

    if (newPassword.length < 8 || !hasLetter || !hasDigit || !hasSpecial) {
      alert("⚠️ 안전한 행정 구동을 위해 영문, 숫자, 특수문자 조합 8자리 이상의 비밀번호로 셋업하십시오.");
      return;
    }

    setResetLoading(true);
    try {
      const token = sessionStorage.getItem('token');
      const res = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ 
          old_password: password, // 로그인 시 입력한 패스워드
          new_password: newPassword 
        })
      });

      if (res.ok) {
        alert("✓ 보안 비밀번호 변경 완료. 안전한 행정망 세션으로 플랫폼을 기동합니다.");
        router.push('/spatial');
      } else {
        const errData = await res.json();
        alert(errData.detail || "비밀번호 변경에 실패했습니다. 다시 시도하십시오.");
        setResetLoading(false);
      }
    } catch (err) {
      alert("서버 연결 실패. 비밀번호 변경 중 통신 에러가 발생했습니다.");
      setResetLoading(false);
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
          OmniSite SDSS v{OMNISITE_VERSION} | Secure Internal Network Only
        </span>

      </div>

      {/* 최초 로그인 강제 비밀번호 변경 모달 */}
      {showResetModal && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-8 rounded-2xl border border-slate-800 bg-slate-900/60 flex flex-col gap-6 shadow-2xl relative animate-fade-in text-slate-100">
            <div className="text-center">
              <span className="text-[10px] bg-rose-500/15 border border-rose-500/30 text-rose-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider">
                Security Enforce Gate
              </span>
              <h2 className="text-lg font-bold text-white mt-3">🔒 비밀번호 변경 의무화</h2>
              <p className="text-[10px] text-slate-400 mt-1">
                초기 비밀번호를 사용 중인 최고 관리자 또는 최초 로그인 계정입니다.<br />
                행정망 보안 수칙에 따라 신규 패스워드로 변경한 후 로그인을 완료하십시오.
              </p>
            </div>

            <form onSubmit={handleForcePasswordChange} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-semibold">새 비밀번호 입력</label>
                <input 
                  type="password"
                  placeholder="새로운 비밀번호 (영문/숫자/특수문자 8자 이상)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 focus:border-rose-500/80 rounded-lg p-2.5 text-xs text-white outline-none transition-all"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-semibold">새 비밀번호 확인</label>
                <input 
                  type="password"
                  placeholder="새 비밀번호 재입력"
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 focus:border-rose-500/80 rounded-lg p-2.5 text-xs text-white outline-none transition-all"
                />
              </div>

              <button 
                type="submit"
                disabled={resetLoading}
                className="w-full bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-bold py-3 rounded-lg transition-all shadow-lg hover:shadow-rose-500/10 cursor-pointer mt-2"
              >
                {resetLoading ? "비밀번호 변경 처리 중..." : "🔑 보안 비밀번호 변경 및 적용"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
