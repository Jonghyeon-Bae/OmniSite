import React, { useState, useEffect } from 'react';

export default function RagRegulationModal({
  show,
  showUpload,
  showList,
  onClose,
  onCloseUpload,
  onCloseList,
  apiFetch,
  showToast,
  regulationList,
  fetchRegulations
}) {
  const [isRegulationUploading, setIsRegulationUploading] = useState(false);
  const [lastAutoBinding, setLastAutoBinding] = useState(null);
  const [internalList, setInternalList] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [deletingFile, setDeletingFile] = useState(null);

  // 통합 프롭스 호환 리졸버
  const isUploadVisible = showUpload || (show && !showList);
  const isListVisible = showList || (show && !showUpload);
  const handleCloseUpload = onCloseUpload || onClose;
  const handleCloseList = onCloseList || onClose;

  // 실제 업로드된 PDF 파일 목록 조회 함수 (가짜/더미 데이터 100% 없음)
  const loadRegulationList = async () => {
    setLoadingList(true);
    try {
      if (apiFetch) {
        const res = await apiFetch('/api/v1/upload/regulations');
        if (res.ok) {
          const data = await res.json();
          const fetched = data.regulations || data.files || [];
          setInternalList(fetched.map((f, i) => ({
            filename: f.filename || f.title || `regulation_${i}.pdf`,
            title: f.title || f.filename || "자치법규 조례 문서",
            size_formatted: f.size_formatted || (f.size_bytes ? `${round(f.size_bytes / 1024, 1)} KB` : 'PDF 문서'),
            version_tag: f.version_tag || "v1.0",
            category: f.category || "health_sanitation",
            content: f.content || `등록된 자치법규 PDF 문서 (${f.filename})`
          })));
        } else {
          setInternalList([]);
        }
      } else {
        setInternalList([]);
      }
    } catch (err) {
      console.warn("[RagRegulationModal Load Error]", err);
      setInternalList([]);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    if (isListVisible || isUploadVisible) {
      loadRegulationList();
    }
  }, [isListVisible, isUploadVisible]);

  const [userRole, setUserRole] = useState('user');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const role = sessionStorage.getItem('role') || 'user';
      setUserRole(role);
    }
  }, [show, showUpload, showList]);

  // 조례 PDF 파일 삭제 핸들러 (🗑️ - 물리 파일 & DB 100% 삭제 / Admin 전용)
  const handleDeleteRegulation = async (regItem) => {
    if (userRole !== 'admin') {
      if (showToast) showToast('🔒 자치법규 조례 PDF 삭제는 최고관리자(Admin)만 수행할 수 있습니다.', 'warning');
      return;
    }

    const filename = regItem.filename || regItem.title;
    if (!filename) return;

    if (!confirm(`[RAG ALERT] 등록된 자치법규 조례 PDF 파일\n'${filename}'을 영구 삭제하시겠습니까?`)) {
      return;
    }

    setDeletingFile(filename);

    // 1. 프론트엔드 화면 즉시 제거 (Optimistic UI Purging)
    setInternalList(prev => prev.filter(item => item.filename !== filename && item.title !== filename));

    // 2. 백엔드 파일 & DB 삭제
    try {
      const encodedFname = encodeURIComponent(filename);
      const res = await apiFetch(`/api/v1/upload/regulations/${encodedFname}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        const data = await res.json();
        if (showToast) showToast(data.message || `✓ 조례 파일 '${filename}' 삭제가 완료되었습니다.`, 'success');
        if (fetchRegulations) fetchRegulations();
        loadRegulationList();
      } else {
        const err = await res.json();
        if (showToast) showToast(`❌ 삭제 실패: ${err.detail || '오류 발생'}`, 'error');
        loadRegulationList();
      }
    } catch (err) {
      if (showToast) showToast(`❌ 삭제 처리 중 오류: ${err.message}`, 'error');
      loadRegulationList();
    } finally {
      setDeletingFile(null);
    }
  };

  // RAG 조례 PDF 파일 업로드 핸들러
  const handleRegulationFileChange = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    setIsRegulationUploading(true);
    setLastAutoBinding(null);
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('version_tag', 'v1.0');
    
    try {
      const res = await apiFetch('/api/v1/upload/regulation', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        const firstFile = (data.files || [])[0] || {};
        if (firstFile.is_auto_matched) {
          setLastAutoBinding({
            title: firstFile.matched_title,
            similarity: firstFile.similarity,
            version: firstFile.version_tag
          });
        }
        if (showToast) showToast(data.message || `✓ RAG 법규 조례 PDF가 성공적으로 적재 처리되었습니다.`, 'success');
        if (fetchRegulations) fetchRegulations();
        loadRegulationList();
      } else {
        const err = await res.json();
        if (showToast) showToast(`❌ 업로드 실패: ${err.detail || '오류 발생'}`, 'error');
      }
    } catch (err) {
      if (showToast) showToast(`❌ 네트워크 오류: ${err.message}`, 'error');
    } finally {
      setIsRegulationUploading(false);
    }
  };

  if (!isUploadVisible && !isListVisible) return null;

  return (
    <>
      {/* ⚖️ 1. RAG 조례 PDF 업로드 모달 */}
      {isUploadVisible && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100 border border-blue-500/30 rounded-2xl shadow-2xl">
            <button 
              onClick={handleCloseUpload}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>

            <div>
              <span className="text-[10px] bg-blue-500/10 border border-blue-500/30 text-blue-400 px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                RAG Legal Vector Engine
              </span>
              <h3 className="text-base font-bold text-white mt-2 flex items-center gap-2">
                <span>⚖️</span>
                <span>RAG 자치법규 조례 PDF 파일 적재</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                지자체 자치법규 PDF 조례 문서를 등록하여 pgvector 1,536차원 벡터 DB로 적재합니다.
              </p>
            </div>

            <div className="flex flex-col gap-2 my-2">
              <div 
                onClick={() => document.getElementById('rag-pdf-uploader-modal').click()}
                className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30 flex flex-col items-center justify-center gap-2"
              >
                <span className="text-3xl">📄</span>
                <p className="text-xs text-slate-200 font-semibold">클릭하여 조례 PDF 파일 등록</p>
                <p className="text-[10px] text-slate-500">PDF 텍스트 청킹 및 pgvector 벡터화를 자동 진행합니다.</p>
                {isRegulationUploading && <p className="text-xs text-amber-400 mt-1 animate-pulse font-bold">⚖️ RAG 적재 및 벡터 캐싱 중...</p>}
              </div>

              <input 
                type="file" 
                multiple 
                accept=".pdf" 
                id="rag-pdf-uploader-modal" 
                className="hidden" 
                onChange={handleRegulationFileChange} 
              />
            </div>

            {lastAutoBinding && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 p-3 rounded-xl text-xs text-emerald-300 flex items-start gap-2">
                <span className="text-base">✓</span>
                <div>
                  <strong className="block text-emerald-200">자동 매칭 및 바인딩 완공</strong>
                  <p className="text-[11px] text-emerald-400/90 mt-0.5">
                    연관 조례: {lastAutoBinding.title} (유사도: {(lastAutoBinding.similarity * 100).toFixed(1)}%)
                  </p>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 mt-2 border-t border-slate-800 pt-3">
              <button
                onClick={handleCloseUpload}
                className="px-4 py-2 text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl cursor-pointer transition-all"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 📜 2. RAG 업로드 조례 PDF 파일 목록 관람 모달 */}
      {isListVisible && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-3xl p-6 flex flex-col gap-4 relative animate-fade-in max-h-[85vh] text-slate-100 border border-slate-800 rounded-2xl shadow-2xl">
            <button 
              onClick={handleCloseList}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>

            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>📜</span>
                  <span>업로드 적재 조례 PDF 파일 목록</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">현재 시스템 저장소에 등록되어 활성화된 자치법규 조례 PDF 목록입니다.</p>
              </div>
              <button
                onClick={loadRegulationList}
                disabled={loadingList}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 rounded-lg border border-slate-700 font-bold transition-all cursor-pointer flex items-center gap-1.5"
              >
                <span>🔄</span>
                <span>{loadingList ? '조회 중...' : '새로고침'}</span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto max-h-[50vh] pr-1 space-y-3 custom-scrollbar">
              {loadingList ? (
                <div className="p-8 text-center text-xs text-slate-400 animate-pulse">
                  ⏳ 업로드된 자치법규 조례 파일 목록을 조회하는 중...
                </div>
              ) : internalList.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  등록된 자치법규 조례 PDF 문서가 없습니다. 조례 PDF를 업로드해 주십시오.
                </div>
              ) : (
                internalList.map((reg, idx) => {
                  const filename = reg.filename || reg.title || `조례 문서 #${idx + 1}`;
                  const sizeStr = reg.size_formatted || 'PDF 문서';
                  const version = reg.version_tag || "v1.0";

                  return (
                    <div key={idx} className="p-4 bg-slate-900/70 border border-slate-800 hover:border-blue-500/50 transition-all rounded-xl flex flex-col gap-2 shadow-md">
                      <div className="flex justify-between items-center gap-2">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <span className="text-base shrink-0">📄</span>
                          <h4 className="text-xs font-bold text-slate-100 truncate font-sans" title={filename}>
                            {filename}
                          </h4>
                          <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] rounded font-bold border border-blue-500/30 shrink-0">
                            {version}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[11px] text-slate-400 font-mono bg-slate-950/60 px-2 py-0.5 rounded border border-slate-800">
                            {sizeStr}
                          </span>
                          {userRole === 'admin' && (
                            <button
                              onClick={() => handleDeleteRegulation(reg)}
                              disabled={deletingFile === filename}
                              className="px-2.5 py-1 text-[11px] font-bold bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded-lg transition-all cursor-pointer flex items-center gap-1 shadow-sm hover:scale-105"
                            >
                              <span>🗑️</span>
                              <span>{deletingFile === filename ? '삭제 중...' : '삭제'}</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={handleCloseList}
                className="px-5 py-2 text-xs font-bold bg-slate-800 hover:bg-slate-700 text-white rounded-xl cursor-pointer transition-all"
              >
                확인 및 닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
