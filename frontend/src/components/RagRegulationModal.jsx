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
  const [ragUploadSuccess, setRagUploadSuccess] = useState(false);

  // RAG 조례 PDF 파일 업로드 핸들러
  const handleRegulationFileChange = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    setIsRegulationUploading(true);
    setRagUploadSuccess(false);
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    
    try {
      const res = await apiFetch('/api/v1/upload/regulations', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        setRagUploadSuccess(true);
        showToast('✓ RAG 법규 조례 PDF가 성공적으로 적재 및 임베딩 처리되었습니다.', 'success');
        if (fetchRegulations) {
          fetchRegulations(); // 업로드 성공 시 목록 갱신
        }
      } else {
        const err = await res.json();
        throw new Error(err.detail || 'RAG 조례 적재 실패');
      }
    } catch (err) {
      showToast(`조례 업로드 중 오류 발생: ${err.message}`, 'error');
    } finally {
      setIsRegulationUploading(false);
    }
  };

  // 조례 파일 삭제
  const handleDeleteRegulation = async (filename) => {
    if (!confirm(`⚠️ 조례 파일 '${filename}'을 RAG 지식베이스에서 삭제하시겠습니까?\n삭제 시 해당 규정의 공간 지리 감리가 즉각 해제됩니다.`)) {
      return;
    }
    
    try {
      const res = await apiFetch(`/api/v1/spatial/regulations/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showToast('✓ RAG 조례 법규가 성공적으로 삭제되었습니다.', 'success');
        if (fetchRegulations) {
          fetchRegulations();
        }
      } else {
        const err = await res.json();
        showToast(err.detail || '조례 삭제 실패', 'error');
      }
    } catch (err) {
      showToast('조례 삭제 처리 중 오류 발생: ' + err.message, 'error');
    }
  };

  // 1) 업로드 관리 모달 렌더링
  if (showUpload) {
    return (
      <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="glass-panel w-full max-w-md p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100">
          <button 
            onClick={() => {
              onCloseUpload();
              setRagUploadSuccess(false);
            }}
            className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
          >
            ✕
          </button>
          <div>
            <h3 className="text-sm font-bold text-white mb-1">⚖️ 법규 RAG 데이터베이스 관리</h3>
            <p className="text-[10px] text-slate-400">지자체 자치법규, 조례, 시행령 PDF를 업로드하여 pgvector 기반 RAG 인공지능 감리 DB를 구축합니다.</p>
          </div>

          <div className="bg-blue-950/30 border border-blue-500/30 p-2.5 rounded-xl text-[10px] text-blue-300 leading-relaxed flex flex-col gap-1">
            <span className="font-bold text-blue-200">💡 조례 PDF 업로드 규격 가이드</span>
            <span>- <strong>조(條) 단위 자동 분할</strong>: [조례명 &gt; 제N조] 단위로 백엔드가 파싱되어 pgvector 1,536 차원으로 자동 임베딩 적재됩니다.</span>
            <span>- <strong>다중 PDF 선택 지원</strong>: 지자체별 금연구역 조례, 킥보드 준수사항 등 여러 문서를 다중 드래그앤드롭 업로드하십시오.</span>
          </div>
          
          <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/40 flex flex-col gap-3">
            <div 
              onClick={() => document.getElementById('modal-regulation-uploader').click()}
              className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30 flex flex-col items-center justify-center gap-1.5"
            >
              <span className="text-xl">⚖️</span>
              <p className="text-xs text-slate-300 font-semibold">조례 및 법규 PDF 파일 등록</p>
              <p className="text-[10px] text-slate-500">클릭하여 PDF 파일을 선택해 주세요.</p>
              {isRegulationUploading && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">RAG 적재 및 텍스트 벡터 캐싱 중...</p>}
            </div>
            
            {ragUploadSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] p-2.5 rounded-lg text-center font-medium animate-pulse">
                ✓ 법규 문서의 RAG DB 적재가 성공적으로 완료되었습니다!
              </div>
            )}
            
            <input 
              type="file" 
              multiple 
              accept=".pdf" 
              id="modal-regulation-uploader" 
              className="hidden" 
              onChange={handleRegulationFileChange} 
            />
          </div>
          
          <button 
            onClick={() => {
              onCloseUpload();
              setRagUploadSuccess(false);
            }}
            className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-bold py-2.5 rounded-lg transition-all cursor-pointer"
          >
            확인 및 닫기
          </button>
        </div>
      </div>
    );
  }

  // 2) 목록 관리 모달 렌더링
  if (showList) {
    return (
      <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="glass-panel w-full max-w-md p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100">
          <button 
            onClick={onCloseList}
            className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
          >
            ✕
          </button>
          <div>
            <h3 className="text-sm font-bold text-white mb-1">📋 등록된 조례/법규 목록</h3>
            <p className="text-[11px] text-slate-400">RAG 지식베이스에 적재되어 공간 감리에 반영되고 있는 조례 문서들입니다.</p>
          </div>
          
          <div className="border border-slate-800 rounded-lg p-3 bg-slate-900/40 flex flex-col gap-2">
            <div className="max-h-60 overflow-y-auto pr-1 flex flex-col gap-2">
              {regulationList.length === 0 ? (
                <p className="text-center py-8 text-xs text-slate-500 font-medium">등록된 조례/시행규칙이 없습니다.</p>
              ) : (
                regulationList.map((reg) => (
                  <div key={reg.filename} className="flex justify-between items-center bg-slate-950/50 border border-slate-800/80 p-2.5 rounded-lg">
                    <div className="flex flex-col gap-0.5 max-w-[80%]">
                      <span className="text-[11px] font-semibold text-slate-200 truncate" title={reg.filename}>
                        {reg.filename}
                      </span>
                      <span className="text-[9px] text-slate-500 font-mono">
                        {(reg.size_bytes / 1024).toFixed(1)} KB
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteRegulation(reg.filename)}
                      className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 p-1.5 rounded-md transition-all shrink-0 cursor-pointer"
                      title="조례 삭제"
                    >
                      🗑️
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <button 
            onClick={onCloseList}
            className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-bold py-2.5 rounded-lg transition-all cursor-pointer"
          >
            닫기
          </button>
        </div>
      </div>
    );
  }

  return null;
}
