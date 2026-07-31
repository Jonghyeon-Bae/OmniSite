'use client';
import React, { useState } from 'react';

export default function LoginModal({ show, onClose, onLoginSuccess, showToast, apiFetch }) {
  const [tab, setTab] = useState('login'); // login | register
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 회원가입 폼 상태
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regDepartment, setRegDepartment] = useState('스마트도시과');
  const [regRole, setRegRole] = useState('user');
  const [regDistrictId, setRegDistrictId] = useState(1);

  if (!show) return null;

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!password) {
      if (showToast) showToast('비밀번호를 입력하세요.', 'error');
      return;
    }
    setIsLoading(true);
    try {
      if (onLoginSuccess) await onLoginSuccess(username, password);
      onClose();
    } catch (err) {
      if (showToast) showToast('로그인 실패: ' + err.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (!regUsername || !regPassword) {
      if (showToast) showToast('아이디와 비밀번호를 모두 입력하세요.', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const fetchFn = apiFetch || fetch;
      const res = await fetchFn('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: regUsername,
          password: regPassword,
          department: regDepartment,
          role: regRole,
          district_id: Number(regDistrictId)
        })
      });

      if (res.ok) {
        if (showToast) showToast('공무원 계정 등록 신청이 완공되었습니다! 생성된 계정으로 로그인하세요.', 'success');
        setUsername(regUsername);
        setPassword(regPassword);
        setTab('login');
      } else {
        const errData = await res.json();
        if (showToast) showToast(errData.detail || '계정 신청 실패', 'error');
      }
    } catch (err) {
      console.error('[Register Error]', err);
      if (showToast) showToast('계정 신청 중 오류가 발생했습니다.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-fade-in">
      <div className="glass-panel w-full max-w-md p-8 rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl flex flex-col gap-5 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white text-xl font-bold cursor-pointer"
        >
          &times;
        </button>

        <div className="text-center">
          <span className="text-[10px] bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider">
            B2G SDSS Authentication
          </span>
          <h2 className="text-xl font-extrabold text-white mt-3">
            {tab === 'login' ? '공공 세션 로그인' : '공무원 계정 신청 등록'}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {tab === 'login'
              ? '인프라 분석 권한 승인을 위해 계정 정보를 입력하세요.'
              : '신규 지자체 공무원 사용 승인을 위한 계정 정보를 입력하세요.'}
          </p>
        </div>

        {/* 탭 버튼 */}
        <div className="flex border-b border-slate-800 pb-2 gap-2">
          <button
            onClick={() => setTab('login')}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-colors ${
              tab === 'login'
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            🔑 세션 로그인
          </button>
          <button
            onClick={() => setTab('register')}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-colors ${
              tab === 'register'
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            📝 공무원 계정 신청
          </button>
        </div>

        {/* 1. 로그인 폼 */}
        {tab === 'login' && (
          <form onSubmit={handleLoginSubmit} className="flex flex-col gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">사용자 계정명</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="username"
                required
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">비밀번호</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-sm py-3 rounded-xl transition-all cursor-pointer shadow-lg shadow-indigo-950/50 mt-2"
            >
              {isLoading ? '로그인 처리 중...' : '세션 로그인 승인'}
            </button>
          </form>
        )}

        {/* 2. 계정 신청 폼 */}
        {tab === 'register' && (
          <form onSubmit={handleRegisterSubmit} className="flex flex-col gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">신청 아이디</label>
              <input
                type="text"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                placeholder="영문/숫자 사용자 아이디"
                required
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">비밀번호 (영문+숫자+특수문자 8자 이상)</label>
              <input
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                placeholder="Admin1234!"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">소속 부서</label>
                <input
                  type="text"
                  value={regDepartment}
                  onChange={(e) => setRegDepartment(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">권한 구분</label>
                <select
                  value={regRole}
                  onChange={(e) => setRegRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="user">일반 공무원 (User)</option>
                  <option value="admin">시스템 관리자 (Admin)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-sm py-3 rounded-xl transition-all cursor-pointer shadow-lg shadow-indigo-950/50 mt-2"
            >
              {isLoading ? '신청 처리 중...' : '공무원 계정 신청 등록'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}