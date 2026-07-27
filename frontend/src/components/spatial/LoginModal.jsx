import React, { useState } from 'react';

export default function LoginModal({ show, onClose, onLoginSuccess, showToast }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!show) return null;

  const handleSubmit = async (e) => {
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

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-fade-in">
      <div className="glass-panel w-full max-w-md p-8 rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl flex flex-col gap-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white text-xl font-bold cursor-pointer"
        >
          &times;
        </button>
        <div className="text-center">
          <span className="text-[10px] bg-blue-500/15 border border-blue-500/30 text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider">
            B2G SDSS Authentication
          </span>
          <h2 className="text-xl font-extrabold text-white mt-3">공공 세션 로그인</h2>
          <p className="text-xs text-slate-400 mt-1">인프라 분석 권한 승인을 위해 계정 정보를 입력하세요.</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">사용자 계정명</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="username"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-sm py-3 rounded-xl transition-all cursor-pointer shadow-lg shadow-blue-950/50 mt-2"
          >
            {isLoading ? '로그인 처리 중...' : '세션 로그인 승인'}
          </button>
        </form>
      </div>
    </div>
  );
}