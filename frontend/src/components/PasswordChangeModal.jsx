import React, { useState } from 'react';

export default function PasswordChangeModal({
  show,
  onClose,
  apiFetch,
  showToast,
  router
}) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const handleSelfPasswordChangeSubmit = async (e) => {
    e.preventDefault();
    if (!oldPassword || !newPassword || !newPasswordConfirm) {
      showToast('⚠️ 모든 항목을 빠짐없이 입력해 주십시오.', 'warning');
      return;
    }

    if (newPassword !== newPasswordConfirm) {
      showToast('⚠️ 새 비밀번호와 새 비밀번호 확인이 일치하지 않습니다.', 'warning');
      return;
    }

    if (newPassword.length < 4) {
      showToast('새 비밀번호는 최소 4자 이상이어야 합니다.', 'warning');
      return;
    }

    setIsChangingPassword(true);
    try {
      const res = await apiFetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          old_password: oldPassword, 
          new_password: newPassword 
        })
      });

      if (res.ok) {
        showToast('✓ 비밀번호 변경이 정상 완료되었습니다. 세션 보안을 위해 다시 로그인해 주십시오.', 'success');
        sessionStorage.clear();
        router.push('/');
        onClose();
      } else {
        const err = await res.json();
        showToast(err.detail || '비밀번호 변경 실패', 'error');
      }
    } catch (err) {
      showToast('비밀번호 변경 중 오류 발생: ' + err.message, 'error');
    } finally {
      setIsChangingPassword(false);
      setOldPassword('');
      setNewPassword('');
      setNewPasswordConfirm('');
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-panel w-full max-w-sm p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100">
        <button 
          onClick={() => {
            onClose();
            setOldPassword('');
            setNewPassword('');
            setNewPasswordConfirm('');
          }}
          className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
        >
          ✕
        </button>
        <div>
          <h3 className="text-sm font-bold text-white mb-1">🔑 비밀번호 자가 변경</h3>
          <p className="text-[10px] text-slate-400">보안 등급 유지를 위해 주기적으로 비밀번호를 변경해 주십시오.</p>
        </div>

        <form onSubmit={handleSelfPasswordChangeSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400">기존 비밀번호</label>
            <input 
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
              placeholder="기존 비밀번호 입력"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400">새 비밀번호</label>
            <input 
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
              placeholder="새 비밀번호 입력 (4자 이상)"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400">새 비밀번호 확인</label>
            <input 
              type="password"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
              placeholder="새 비밀번호 재입력"
            />
          </div>

          <button 
            type="submit"
            disabled={isChangingPassword}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold py-2.5 rounded-lg transition-all mt-2 cursor-pointer"
          >
            {isChangingPassword ? "비밀번호 변경 중..." : "🔑 비밀번호 변경 및 적용"}
          </button>
        </form>
      </div>
    </div>
  );
}
