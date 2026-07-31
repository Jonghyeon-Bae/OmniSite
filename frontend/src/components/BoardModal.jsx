'use client';
import React, { useState, useEffect } from 'react';

export default function BoardModal({ show, onClose, apiFetch, showToast }) {
  const [activeTab, setActiveTab] = useState('notices'); // notices | community | faqs
  const [notices, setNotices] = useState([]);
  const [communityPosts, setCommunityPosts] = useState([]);
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userRole, setUserRole] = useState('user');

  // 공지사항 작성/수정 폼 상태 (관리자 전용)
  const [showNoticeForm, setShowNoticeForm] = useState(false);
  const [editingNoticeId, setEditingNoticeId] = useState(null);
  const [noticeTitle, setNoticeTitle] = useState('');
  const [noticeContent, setNoticeContent] = useState('');
  const [noticePinned, setNoticePinned] = useState(false);
  const [noticeSubmitting, setNoticeSubmitting] = useState(false);

  // FAQ 작성/수정 폼 상태 (관리자 전용)
  const [showFaqForm, setShowFaqForm] = useState(false);
  const [editingFaqId, setEditingFaqId] = useState(null);
  const [faqCategoryInput, setFaqCategoryInput] = useState('📄 데이터 업로드 & 감리');
  const [faqQuestionInput, setFaqQuestionInput] = useState('');
  const [faqAnswerInput, setFaqAnswerInput] = useState('');
  const [faqSubmitting, setFaqSubmitting] = useState(false);

  // 자유게시판 신규 글쓰기 폼 상태
  const [showWriteForm, setShowWriteForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newAuthor, setNewAuthor] = useState('김주무관');
  const [newDept, setNewDept] = useState('스마트도시과');
  const [posting, setPosting] = useState(false);

  // FAQ 카테고리 필터 및 검색 상태
  const [faqCategory, setFaqCategory] = useState('ALL');
  const [faqSearch, setFaqSearch] = useState('');
  const [openFaqId, setOpenFaqId] = useState(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const role = sessionStorage.getItem('role') || 'user';
      setUserRole(role);
    }
  }, [show]);

  useEffect(() => {
    if (show) {
      fetchBoardData(activeTab);
    }
  }, [show, activeTab]);

  const fetchBoardData = async (tab) => {
    setLoading(true);
    try {
      const fetchFn = apiFetch || fetch;
      if (tab === 'notices') {
        const res = await fetchFn('/api/v1/board/notices');
        if (res.ok) {
          const data = await res.json();
          setNotices(data);
        }
      } else if (tab === 'community') {
        const res = await fetchFn('/api/v1/board/community');
        if (res.ok) {
          const data = await res.json();
          setCommunityPosts(data);
        }
      } else if (tab === 'faqs') {
        const res = await fetchFn('/api/v1/board/faqs');
        if (res.ok) {
          const data = await res.json();
          setFaqs(data);
        }
      }
    } catch (err) {
      console.error('[Board Modal Fetch Error]', err);
    } finally {
      setLoading(false);
    }
  };

  // 1. 공지사항 CRUD (Admin 전용)
  const handleSaveNotice = async (e) => {
    e.preventDefault();
    if (!noticeTitle.trim() || !noticeContent.trim()) {
      if (showToast) showToast('제목과 본문을 모두 입력해 주세요.', 'warning');
      return;
    }
    setNoticeSubmitting(true);
    try {
      const fetchFn = apiFetch || fetch;
      const url = editingNoticeId 
        ? `/api/v1/board/notices/${editingNoticeId}`
        : '/api/v1/board/notices';
      const method = editingNoticeId ? 'PUT' : 'POST';

      const res = await fetchFn(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: noticeTitle,
          content: noticeContent,
          is_pinned: noticePinned
        })
      });

      if (res.ok) {
        if (showToast) showToast(editingNoticeId ? '공지사항이 수정되었습니다.' : '신규 공지사항이 등록되었습니다.', 'success');
        setNoticeTitle('');
        setNoticeContent('');
        setNoticePinned(false);
        setEditingNoticeId(null);
        setShowNoticeForm(false);
        fetchBoardData('notices');
      } else {
        if (showToast) showToast('공지사항 저장에 실패했습니다.', 'error');
      }
    } catch (err) {
      console.error('[Save Notice Error]', err);
      if (showToast) showToast('공지사항 저장 중 오류가 발생했습니다.', 'error');
    } finally {
      setNoticeSubmitting(false);
    }
  };

  const handleEditNotice = (n) => {
    setEditingNoticeId(n.id);
    setNoticeTitle(n.title);
    setNoticeContent(n.content);
    setNoticePinned(n.is_pinned);
    setShowNoticeForm(true);
  };

  const handleDeleteNotice = async (noticeId) => {
    if (!window.confirm('정말 이 공지사항을 삭제하시겠습니까?')) return;
    try {
      const fetchFn = apiFetch || fetch;
      const res = await fetchFn(`/api/v1/board/notices/${noticeId}`, { method: 'DELETE' });
      if (res.ok) {
        if (showToast) showToast('공지사항이 삭제되었습니다.', 'success');
        fetchBoardData('notices');
      } else {
        if (showToast) showToast('공지사항 삭제에 실패했습니다.', 'error');
      }
    } catch (err) {
      console.error('[Delete Notice Error]', err);
    }
  };

  // 2. FAQ CRUD (Admin 전용 DB 테이블 CRUD)
  const handleSaveFaq = async (e) => {
    e.preventDefault();
    if (!faqQuestionInput.trim() || !faqAnswerInput.trim()) {
      if (showToast) showToast('질문과 답변을 모두 입력해 주세요.', 'warning');
      return;
    }
    setFaqSubmitting(true);
    try {
      const fetchFn = apiFetch || fetch;
      const url = editingFaqId 
        ? `/api/v1/board/faqs/${editingFaqId}`
        : '/api/v1/board/faqs';
      const method = editingFaqId ? 'PUT' : 'POST';

      const res = await fetchFn(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: faqCategoryInput,
          question: faqQuestionInput,
          answer: faqAnswerInput
        })
      });

      if (res.ok) {
        if (showToast) showToast(editingFaqId ? 'FAQ 지식 항목이 수정되었습니다.' : '신규 FAQ 지식 항목이 등록되었습니다.', 'success');
        setFaqQuestionInput('');
        setFaqAnswerInput('');
        setEditingFaqId(null);
        setShowFaqForm(false);
        fetchBoardData('faqs');
      } else {
        if (showToast) showToast('FAQ 저장에 실패했습니다.', 'error');
      }
    } catch (err) {
      console.error('[Save FAQ Error]', err);
      if (showToast) showToast('FAQ 저장 중 오류가 발생했습니다.', 'error');
    } finally {
      setFaqSubmitting(false);
    }
  };

  const handleEditFaq = (f) => {
    setEditingFaqId(f.id);
    setFaqCategoryInput(f.category || '📄 데이터 업로드 & 감리');
    setFaqQuestionInput(f.question);
    setFaqAnswerInput(f.answer);
    setShowFaqForm(true);
  };

  const handleDeleteFaq = async (faqId) => {
    if (!window.confirm('정말 이 FAQ 항목을 삭제하시겠습니까?')) return;
    try {
      const fetchFn = apiFetch || fetch;
      const res = await fetchFn(`/api/v1/board/faqs/${faqId}`, { method: 'DELETE' });
      if (res.ok) {
        if (showToast) showToast('FAQ 항목이 삭제되었습니다.', 'success');
        fetchBoardData('faqs');
      } else {
        if (showToast) showToast('FAQ 삭제에 실패했습니다.', 'error');
      }
    } catch (err) {
      console.error('[Delete FAQ Error]', err);
    }
  };

  // 3. 자유게시판 CRUD
  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) {
      if (showToast) showToast('제목과 본문을 모두 입력해 주세요.', 'warning');
      return;
    }
    setPosting(true);
    try {
      const fetchFn = apiFetch || fetch;
      const res = await fetchFn('/api/v1/board/community', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle,
          content: newContent,
          author_name: newAuthor,
          department: newDept
        })
      });
      if (res.ok) {
        if (showToast) showToast('게시글이 정상 등록되었습니다.', 'success');
        setNewTitle('');
        setNewContent('');
        setShowWriteForm(false);
        fetchBoardData('community');
      } else {
        if (showToast) showToast('게시글 등록에 실패했습니다.', 'error');
      }
    } catch (err) {
      console.error('[Create Post Error]', err);
      if (showToast) showToast('게시글 등록 오류가 발생했습니다.', 'error');
    } finally {
      setPosting(false);
    }
  };

  const handleDeletePost = async (postId) => {
    if (!window.confirm('이 게시글을 삭제하시겠습니까?')) return;
    try {
      const fetchFn = apiFetch || fetch;
      const res = await fetchFn(`/api/v1/board/community/${postId}`, { method: 'DELETE' });
      if (res.ok) {
        if (showToast) showToast('게시글이 삭제되었습니다.', 'success');
        fetchBoardData('community');
      } else {
        if (showToast) showToast('게시글 삭제에 실패했습니다.', 'error');
      }
    } catch (err) {
      console.error('[Delete Post Error]', err);
    }
  };

  if (!show) return null;

  const isAdmin = userRole === 'admin';

  const filteredFaqs = faqs.filter(f => {
    const matchCat = faqCategory === 'ALL' || f.category === faqCategory;
    const matchSearch = !faqSearch || 
      (f.question || '').toLowerCase().includes(faqSearch.toLowerCase()) || 
      (f.answer || '').toLowerCase().includes(faqSearch.toLowerCase()) ||
      (f.category || '').toLowerCase().includes(faqSearch.toLowerCase());
    return matchCat && matchSearch;
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      {/* 프리미엄 모달 카드: max-w-6xl w-full h-[90vh] */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-6xl w-full p-8 text-slate-100 shadow-2xl flex flex-col h-[90vh] relative">
        
        {/* 상단 헤더 */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 text-2xl shadow-inner">
              📋
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-extrabold text-slate-100 tracking-tight">OmniSite 행정 통합 게시판</h2>
                <span className="bg-indigo-900/80 text-indigo-300 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-indigo-700/60">
                  v1.5.0 Public SDSS Suite
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                PostgreSQL DB 테이블 동적 연동 (공지사항 CRUD / 자유게시판 / Admin 전용 FAQ CRUD 지식베이스)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-all font-bold cursor-pointer border border-slate-700"
          >
            ✕
          </button>
        </div>

        {/* 3대 탭 네비게이션 */}
        <div className="flex items-center border-b border-slate-800 mb-5 gap-2">
          <button
            onClick={() => { setActiveTab('notices'); setShowWriteForm(false); setShowNoticeForm(false); setShowFaqForm(false); }}
            className={`px-5 py-3 text-xs font-bold rounded-t-xl transition-all flex items-center gap-2 border-b-2 cursor-pointer ${
              activeTab === 'notices'
                ? 'border-indigo-500 bg-indigo-600/15 text-indigo-300 shadow-md'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <span className="text-base">📢</span> 공지사항 {isAdmin && <span className="text-[10px] bg-rose-950 text-rose-300 px-1.5 py-0.5 rounded border border-rose-700/50">Admin CRUD</span>}
          </button>
          <button
            onClick={() => { setActiveTab('community'); setShowWriteForm(false); setShowNoticeForm(false); setShowFaqForm(false); }}
            className={`px-5 py-3 text-xs font-bold rounded-t-xl transition-all flex items-center gap-2 border-b-2 cursor-pointer ${
              activeTab === 'community'
                ? 'border-indigo-500 bg-indigo-600/15 text-indigo-300 shadow-md'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <span className="text-base">💬</span> 자유게시판
          </button>
          <button
            onClick={() => { setActiveTab('faqs'); setShowWriteForm(false); setShowNoticeForm(false); setShowFaqForm(false); }}
            className={`px-5 py-3 text-xs font-bold rounded-t-xl transition-all flex items-center gap-2 border-b-2 cursor-pointer ${
              activeTab === 'faqs'
                ? 'border-indigo-500 bg-indigo-600/15 text-indigo-300 shadow-md'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <span className="text-base">❓</span> DB 연동 FAQ 지식베이스 ({faqs.length}) {isAdmin && <span className="text-[10px] bg-indigo-950 text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-700/50">Admin CRUD</span>}
          </button>
        </div>

        {/* 본문 콘텐츠 영역 */}
        <div className="flex-1 overflow-y-auto pr-2">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-28 gap-3">
              <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs text-slate-400 font-semibold">DB 지식 데이터를 불러오는 중...</span>
            </div>
          ) : (
            <>
              {/* 1. 공지사항 탭 */}
              {activeTab === 'notices' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                    <span className="text-xs text-slate-400">
                      전체 공지사항 <strong className="text-slate-200">{notices.length}</strong>건
                      {isAdmin ? ' (최고 관리자 CRUD 권한 승인됨)' : ' (일반 공무원 읽기 전용)'}
                    </span>
                    {isAdmin && (
                      <button
                        onClick={() => {
                          setEditingNoticeId(null);
                          setNoticeTitle('');
                          setNoticeContent('');
                          setNoticePinned(false);
                          setShowNoticeForm(!showNoticeForm);
                        }}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-md"
                      >
                        {showNoticeForm ? '✕ 작성 취소' : '📢 새 공지사항 등록'}
                      </button>
                    )}
                  </div>

                  {/* 관리자 공지사항 작성/수정 폼 */}
                  {isAdmin && showNoticeForm && (
                    <form onSubmit={handleSaveNotice} className="bg-slate-800/90 border border-indigo-500/40 rounded-xl p-5 shadow-xl space-y-3">
                      <h4 className="font-bold text-sm text-indigo-300 flex items-center gap-2">
                        <span>{editingNoticeId ? '✏️ 공지사항 수정' : '📢 신규 공지사항 등록'}</span>
                      </h4>
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <label className="block text-[11px] text-slate-400 mb-1 font-semibold">공지 제목</label>
                          <input
                            type="text"
                            value={noticeTitle}
                            onChange={(e) => setNoticeTitle(e.target.value)}
                            placeholder="공지사항 제목을 입력하세요."
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                            required
                          />
                        </div>
                        <div className="flex items-center gap-2 pt-5">
                          <input
                            type="checkbox"
                            id="noticePinnedCheck"
                            checked={noticePinned}
                            onChange={(e) => setNoticePinned(e.target.checked)}
                            className="w-4 h-4 accent-indigo-500 cursor-pointer"
                          />
                          <label htmlFor="noticePinnedCheck" className="text-xs text-indigo-300 font-bold cursor-pointer">
                            📌 상단 고정 (필독)
                          </label>
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1 font-semibold">공지 본문 내용</label>
                        <textarea
                          rows={5}
                          value={noticeContent}
                          onChange={(e) => setNoticeContent(e.target.value)}
                          placeholder="공지사항 세부 내용을 상세히 등록하세요."
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 leading-relaxed"
                          required
                        />
                      </div>
                      <div className="flex justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setShowNoticeForm(false)}
                          className="bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs px-4 py-2 rounded-lg cursor-pointer"
                        >
                          취소
                        </button>
                        <button
                          type="submit"
                          disabled={noticeSubmitting}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2 rounded-lg disabled:opacity-50 cursor-pointer shadow-md"
                        >
                          {noticeSubmitting ? '저장 중...' : (editingNoticeId ? '수정 완료' : '공지 등록')}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* 공지사항 목록 */}
                  <div className="space-y-3">
                    {notices.map((n) => (
                      <div
                        key={`notice-${n.id}`}
                        className={`p-5 rounded-xl border transition-all ${
                          n.is_pinned
                            ? 'bg-indigo-950/40 border-indigo-700/60 shadow-lg'
                            : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/70'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            {n.is_pinned && (
                              <span className="bg-indigo-600 text-white text-[10px] font-extrabold px-2.5 py-0.5 rounded-full shadow">
                                📌 필독
                              </span>
                            )}
                            <h4 className="font-bold text-base text-slate-100">{n.title}</h4>
                          </div>
                          <span className="text-xs text-slate-500 font-mono">{n.created_at}</span>
                        </div>
                        <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed my-3 bg-slate-950/40 p-3.5 rounded-lg border border-slate-800">
                          {n.content}
                        </p>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-700/40 pt-2">
                          <span>발행 명의: <strong className="text-slate-200">{n.author}</strong></span>
                          {isAdmin && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleEditNotice(n)}
                                className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded text-[11px] font-bold border border-slate-700 cursor-pointer"
                              >
                                ✏️ 수정
                              </button>
                              <button
                                onClick={() => handleDeleteNotice(n.id)}
                                className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 px-2.5 py-1 rounded text-[11px] font-bold border border-rose-800/40 cursor-pointer"
                              >
                                🗑️ 삭제
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. 자유게시판 탭 */}
              {activeTab === 'community' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                    <span className="text-xs text-slate-400">
                      총 <strong className="text-slate-200">{communityPosts.length}</strong>건의 부서 간 소통 게시글
                    </span>
                    <button
                      onClick={() => setShowWriteForm(!showWriteForm)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-md"
                    >
                      {showWriteForm ? '✕ 작성 취소' : '✍️ 새 글 작성'}
                    </button>
                  </div>

                  {/* 글쓰기 폼 */}
                  {showWriteForm && (
                    <form onSubmit={handleCreatePost} className="bg-slate-800/90 border border-slate-700 rounded-xl p-5 shadow-xl space-y-3">
                      <h4 className="font-bold text-xs text-indigo-300">신규 소통 게시글 작성</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[10px] text-slate-400 mb-1">작성자 성명</label>
                          <input
                            type="text"
                            value={newAuthor}
                            onChange={(e) => setNewAuthor(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-slate-400 mb-1">소속 부서</label>
                          <input
                            type="text"
                            value={newDept}
                            onChange={(e) => setNewDept(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                            required
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 mb-1">제목</label>
                        <input
                          type="text"
                          value={newTitle}
                          onChange={(e) => setNewTitle(e.target.value)}
                          placeholder="게시글 제목을 입력하세요"
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 mb-1">본문 내용</label>
                        <textarea
                          rows={4}
                          value={newContent}
                          onChange={(e) => setNewContent(e.target.value)}
                          placeholder="부서 간 입지 의견이나 건의 사항을 자유롭게 작성하세요."
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed"
                          required
                        />
                      </div>
                      <div className="flex justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setShowWriteForm(false)}
                          className="bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs px-4 py-2 rounded-lg cursor-pointer"
                        >
                          취소
                        </button>
                        <button
                          type="submit"
                          disabled={posting}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2 rounded-lg disabled:opacity-50 cursor-pointer shadow-md"
                        >
                          {posting ? '등록 중...' : '게시글 등록'}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* 게시글 목록 */}
                  <div className="space-y-3">
                    {communityPosts.map((p) => (
                      <div key={`community-${p.id}`} className="bg-slate-800/40 border border-slate-700/50 hover:bg-slate-800/70 p-5 rounded-xl transition-all">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-bold text-base text-slate-100">{p.title}</h4>
                          <span className="text-xs text-slate-500 font-mono">{p.created_at}</span>
                        </div>
                        <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed my-3 bg-slate-950/40 p-3.5 rounded-lg border border-slate-800">
                          {p.content}
                        </p>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-700/40 pt-2">
                          <span>작성자: <strong className="text-slate-200">{p.author_name}</strong> ({p.department})</span>
                          <div className="flex items-center gap-3">
                            <span>조회수 {p.views_count}</span>
                            {(isAdmin || p.author_name === '김주무관') && (
                              <button
                                onClick={() => handleDeletePost(p.id)}
                                className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 px-2 py-0.5 rounded text-[10px] font-bold border border-rose-800/40 cursor-pointer"
                              >
                                🗑️ 삭제
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. FAQ 탭 (PostgreSQL DB 테이블 동적 연동 & Admin CRUD 가능) */}
              {activeTab === 'faqs' && (
                <div className="space-y-4">
                  {/* 상단 액션바 & 필터 */}
                  <div className="flex flex-col md:flex-row gap-3 items-center justify-between bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                    <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
                      {[
                        'ALL',
                        '📄 데이터 업로드 & 감리',
                        '🗺️ AHP & 공간 추천',
                        '⚖️ AI 심의 & 보고서',
                        '📜 RAG 조례 & 이력'
                      ].map(cat => (
                        <button
                          key={`cat-filter-${cat}`}
                          onClick={() => setFaqCategory(cat)}
                          className={`text-xs px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer border ${
                            faqCategory === cat
                              ? 'bg-indigo-600 text-white border-indigo-500 shadow-md'
                              : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:text-slate-200'
                          }`}
                        >
                          {cat === 'ALL' ? `전체 FAQ (${faqs.length})` : cat}
                        </button>
                      ))}
                    </div>

                    <div className="flex items-center gap-2 w-full md:w-auto">
                      <div className="relative w-full md:w-64">
                        <input
                          type="text"
                          value={faqSearch}
                          onChange={(e) => setFaqSearch(e.target.value)}
                          placeholder="🔍 FAQ 키워드 검색..."
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 shadow-inner"
                        />
                        {faqSearch && (
                          <button
                            onClick={() => setFaqSearch('')}
                            className="absolute right-3 top-2 text-slate-400 hover:text-white text-xs font-bold cursor-pointer"
                          >
                            ✕
                          </button>
                        )}
                      </div>

                      {isAdmin && (
                        <button
                          onClick={() => {
                            setEditingFaqId(null);
                            setFaqQuestionInput('');
                            setFaqAnswerInput('');
                            setFaqCategoryInput('📄 데이터 업로드 & 감리');
                            setShowFaqForm(!showFaqForm);
                          }}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-all cursor-pointer flex items-center gap-1.5 shrink-0 shadow-md"
                        >
                          {showFaqForm ? '✕ 취소' : '➕ 새 FAQ 등록'}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Admin 전용 FAQ 신규 작성/수정 폼 */}
                  {isAdmin && showFaqForm && (
                    <form onSubmit={handleSaveFaq} className="bg-slate-800/90 border border-indigo-500/40 rounded-xl p-5 shadow-xl space-y-3">
                      <h4 className="font-bold text-sm text-indigo-300 flex items-center gap-2">
                        <span>{editingFaqId ? '✏️ FAQ 지식 항목 수정' : '➕ 신규 FAQ 지식 항목 등록'}</span>
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="block text-[11px] text-slate-400 mb-1 font-semibold">FAQ 범주 카테고리</label>
                          <select
                            value={faqCategoryInput}
                            onChange={(e) => setFaqCategoryInput(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 cursor-pointer"
                          >
                            <option value="📄 데이터 업로드 & 감리">📄 데이터 업로드 & 감리</option>
                            <option value="🗺️ AHP & 공간 추천">🗺️ AHP & 공간 추천</option>
                            <option value="⚖️ AI 심의 & 보고서">⚖️ AI 심의 & 보고서</option>
                            <option value="📜 RAG 조례 & 이력">📜 RAG 조례 & 이력</option>
                            <option value="💡 일반 시스템 이용">💡 일반 시스템 이용</option>
                          </select>
                        </div>
                        <div className="md:col-span-2">
                          <label className="block text-[11px] text-slate-400 mb-1 font-semibold">FAQ 질문 제목</label>
                          <input
                            type="text"
                            value={faqQuestionInput}
                            onChange={(e) => setFaqQuestionInput(e.target.value)}
                            placeholder="예: [Step 1] 공간 CSV 업로드 시 필수 항목은 무엇인가요?"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                            required
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1 font-semibold">FAQ 답변 및 가이드라인</label>
                        <textarea
                          rows={4}
                          value={faqAnswerInput}
                          onChange={(e) => setFaqAnswerInput(e.target.value)}
                          placeholder="상세 처리 가이드라인 및 시스템 조작법을 작성하세요."
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 leading-relaxed"
                          required
                        />
                      </div>
                      <div className="flex justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setShowFaqForm(false)}
                          className="bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs px-4 py-2 rounded-lg cursor-pointer"
                        >
                          취소
                        </button>
                        <button
                          type="submit"
                          disabled={faqSubmitting}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2 rounded-lg disabled:opacity-50 cursor-pointer shadow-md"
                        >
                          {faqSubmitting ? '저장 중...' : (editingFaqId ? '수정 완료' : 'FAQ 저장')}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* FAQ 아코디언 목록 (100% DB primary key=f.id 적용) */}
                  <div className="space-y-3">
                    {filteredFaqs.map((f) => (
                      <div
                        key={`faq-${f.id}`}
                        className="bg-slate-800/40 border border-slate-700/60 rounded-xl overflow-hidden shadow-sm hover:border-indigo-500/50 transition-all"
                      >
                        <div className="p-4 flex items-center justify-between text-xs font-bold text-slate-100 hover:bg-slate-800/60 transition-all">
                          <button
                            onClick={() => setOpenFaqId(openFaqId === f.id ? null : f.id)}
                            className="flex-1 text-left flex items-center gap-3 cursor-pointer"
                          >
                            <span className="bg-indigo-900/80 text-indigo-300 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full border border-indigo-700/60 shrink-0">
                              {f.category}
                            </span>
                            <span className="text-sm font-bold text-slate-100">
                              Q. {f.question}
                            </span>
                          </button>

                          <div className="flex items-center gap-3 shrink-0 ml-3">
                            {isAdmin && (
                              <div className="flex items-center gap-1.5 mr-2">
                                <button
                                  onClick={() => handleEditFaq(f)}
                                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold px-2 py-1 rounded border border-slate-700 cursor-pointer"
                                >
                                  ✏️ 수정
                                </button>
                                <button
                                  onClick={() => handleDeleteFaq(f.id)}
                                  className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 text-[10px] font-bold px-2 py-1 rounded border border-rose-800/40 cursor-pointer"
                                >
                                  🗑️ 삭제
                                </button>
                              </div>
                            )}
                            <button
                              onClick={() => setOpenFaqId(openFaqId === f.id ? null : f.id)}
                              className="text-slate-400 hover:text-white font-mono text-xs cursor-pointer"
                            >
                              {openFaqId === f.id ? '▲ 접기' : '▼ 펼치기'}
                            </button>
                          </div>
                        </div>

                        {openFaqId === f.id && (
                          <div className="p-4 bg-slate-950/80 border-t border-slate-800/80 text-xs text-slate-300 leading-relaxed animate-fade-in">
                            <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800/80 text-indigo-200">
                              <strong className="text-indigo-400 block mb-1">💡 실무 처리 가이드라인:</strong>
                              {f.answer}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}

                    {filteredFaqs.length === 0 && (
                      <div className="py-12 text-center text-slate-500 text-xs bg-slate-950/40 rounded-xl border border-slate-800/50">
                        검색 조건에 해당되는 FAQ 지식 항목이 없습니다.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* 하단 닫기 푸터 */}
        <div className="mt-5 pt-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold px-6 py-2.5 rounded-xl transition-all cursor-pointer border border-slate-700"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
