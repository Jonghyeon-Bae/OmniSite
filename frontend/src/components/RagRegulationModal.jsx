import React, { useState } from 'react';

export default function RagRegulationModal({
  showUpload,
  showList,
  onCloseUpload,
  onCloseList,
  apiFetch,
  showToast,
  regulationList,
  fetchRegulations
}) {
  const [isRegulationUploading, setIsRegulationUploading] = useState(false);
  const [lastAutoBinding, setLastAutoBinding] = useState(null);

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
        showToast(data.message || `✓ RAG 법규 조례 PDF가 성공적으로 적재 처리되었습니다.`, 'success');
        if (fetchRegulations) fetchRegulations();
      } else {
        const err = await res.json();
        showToast(`❌ 업로드 실패: ${err.detail || '오류 발생'}`, 'error');
      }
    } catch (err) {
      showToast(`❌ 네트워크 오류: ${err.message}`, 'error');
    } finally {
      setIsRegulationUploading(false);
    }
  };

  if (!showUpload && !showList) return null;

  return (
    <>
      {/* ⚖️ 1. RAG 조례 PDF 업로드 모달 */}
      {showUpload && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100 border border-blue-500/30 rounded-2xl shadow-2xl">
            <button 
              onClick={onCloseUpload}
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
                <span>RAG 자치법규 조례 PDF 임베딩 적재</span>
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
                onClick={onCloseUpload}
                className="px-4 py-2 text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl cursor-pointer transition-all"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 📜 2. RAG 적재 조례 목록 관람 모달 */}
      {showList && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-3xl p-6 flex flex-col gap-4 relative animate-fade-in max-h-[85vh] text-slate-100 border border-slate-800 rounded-2xl shadow-2xl">
            <button 
              onClick={onCloseList}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>

            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>📜</span>
                  <span>RAG 백엔드 적재 조례 법규 메타데이터 목록</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">현재 Vector DB에 활성화된 지자체 조례 및 시행령 목록입니다.</p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto max-h-[50vh] pr-1 space-y-2 custom-scrollbar">
              {(!regulationList || regulationList.length === 0) ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  적재된 조례 문서가 없습니다. RAG 조례 PDF를 등록해 주십시오.
                </div>
              ) : (
                regulationList.map((reg, idx) => (
                  <div key={idx} className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-blue-300">{reg.regulation_title}</span>
                      <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] rounded-full font-bold">
                        {reg.category || 'health_sanitation'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 font-mono line-clamp-2 bg-slate-950/50 p-2 rounded border border-slate-800/80">
                      {reg.content}
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={onCloseList}
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
