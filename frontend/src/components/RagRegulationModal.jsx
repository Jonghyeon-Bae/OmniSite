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
  const [previewDiffFile, setPreviewDiffFile] = useState(null);
  const [diffData, setDiffData] = useState(null);
  const [isDiffLoading, setIsDiffLoading] = useState(false);

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

  // 1클릭 조례 개정 이력 Diff 조회
  const handleFetchDiffPreview = async (filename) => {
    if (previewDiffFile === filename) {
      setPreviewDiffFile(null);
      setDiffData(null);
      return;
    }

    setPreviewDiffFile(filename);
    setIsDiffLoading(true);
    setDiffData(null);

    try {
      const res = await apiFetch(`/api/v1/upload/diff?version_a=v1.0&version_b=v2.0`);
      if (res.ok) {
        const data = await res.json();
        setDiffData(data.diff || data);
      }
    } catch (err) {
      console.warn('[Diff Preview Error]', err);
    } finally {
      setIsDiffLoading(false);
    }
  };

  // 등록된 조례 삭제 핸들러
  const handleDeleteRegulation = async (filename) => {
    if (!window.confirm(`정말 '${filename}' 문서를 RAG 지식베이스에서 삭제하시겠습니까?`)) return;
    try {
      const res = await apiFetch(`/api/v1/upload/regulations/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showToast(`✓ 조례 문서가 성공적으로 삭제되었습니다.`, 'success');
        if (fetchRegulations) fetchRegulations();
      }
    } catch (err) {
      showToast(`❌ 삭제 실패: ${err.message}`, 'error');
    }
  };

  if (!showUpload && !showList) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fade-in font-sans">
      <div className="relative w-full max-w-2xl bg-slate-900/95 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* 모달 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">📋</span>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                {showUpload ? 'RAG 법규/조례 PDF 신규 적재' : 'RAG 조례 지식베이스 관리 현황'}
              </h3>
              <p className="text-[11px] text-slate-400">
                pgvector 1,536차원 벡터 공간 기반 지능형 조례 개정 자동 체이닝 및 활성 지식베이스
              </p>
            </div>
          </div>
          <button
            onClick={showUpload ? onCloseUpload : onCloseList}
            className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer text-sm"
          >
            ✕
          </button>
        </div>

        {/* 모달 바디 */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          
          {/* pgvector 오토 바인딩 체이닝 성공 뱃지 */}
          {lastAutoBinding && (
            <div className="p-3.5 bg-emerald-950/60 border border-emerald-500/40 rounded-xl flex items-start gap-2.5 shadow-md">
              <span className="text-base shrink-0 mt-0.5">🎯</span>
              <div className="text-[11px] text-emerald-200 space-y-0.5 font-sans">
                <span className="font-bold text-emerald-400">✓ pgvector 코사인 유사도 자동 체이닝 ({lastAutoBinding.similarity}%)</span>
                <p className="opacity-90 leading-relaxed">
                  기존 조례 <strong>'{lastAutoBinding.title}'</strong>의 개정안으로 탐지되어 <strong>'{lastAutoBinding.version}' 스냅샷</strong>으로 자동 연동되었습니다.
                </p>
              </div>
            </div>
          )}

          {/* 1. 조례 PDF 파일 등록 세션 */}
          {showUpload && (
            <div className="space-y-2.5 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
              <label className="block text-xs font-bold text-slate-200">
                📄 RAG 조례 PDF / HWP 문서 업로드
              </label>
              <input
                type="file"
                multiple
                accept=".pdf,.hwp"
                onChange={handleRegulationFileChange}
                disabled={isRegulationUploading}
                className="w-full text-xs text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer border border-slate-800 rounded-xl bg-slate-900 p-1"
              />
              {isRegulationUploading && (
                <div className="flex items-center gap-2 text-[11px] text-blue-400 font-semibold animate-pulse pt-1">
                  <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span>pgvector 1,536차원 임베딩 코사인 유사도 스캔 및 적재 연산 중...</span>
                </div>
              )}
            </div>
          )}

          {/* 2. 등록된 RAG 조례 지식베이스 목록 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <span>📂</span>
                <span>활성 RAG 조례 파일 목록 ({regulationList ? regulationList.length : 0}개)</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Active Knowledge Base</span>
            </div>

            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {regulationList && regulationList.length > 0 ? (
                regulationList.map((item, idx) => (
                  <div key={idx} className="flex flex-col gap-2.5 p-4 bg-slate-950/70 border border-slate-800/90 hover:border-blue-500/40 rounded-2xl transition-all duration-200 shadow-md hover:shadow-blue-500/5">
                    
                    {/* 상단 1열: 조례 제목 (Truncate 제거, 깔끔한 멀티라인 표출) & 우측 반짝이는 버전 뱃지 */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2.5 min-w-0 flex-1">
                        <span className="text-base shrink-0 mt-0.5">📜</span>
                        <h4 className="text-xs font-bold text-slate-100 leading-relaxed font-sans break-keep">
                          {item.filename.replace(/\.pdf$/i, '').replace(/\.hwp$/i, '')}
                        </h4>
                      </div>
                      <span className="shrink-0 text-[10px] bg-blue-500/15 text-blue-400 border border-blue-500/30 px-2.5 py-0.5 rounded-full font-mono font-bold shadow-[0_0_10px_rgba(59,130,246,0.2)]">
                        {item.version_tag || 'v1.0'}
                      </span>
                    </div>

                    {/* 하단 2열: 메타 정보(용량/카테고리) & 우측 액션 버튼 그룹 */}
                    <div className="flex items-center justify-between border-t border-slate-900/80 pt-2.5 mt-0.5">
                      <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono">
                        <span className="flex items-center gap-1">
                          <span>💾</span>
                          <span>{(item.size_bytes / 1024).toFixed(1)} KB</span>
                        </span>
                        <span className="text-slate-600">|</span>
                        <span className="text-slate-400 flex items-center gap-1 font-sans">
                          <span>🏷️</span>
                          <span>pgvector RAG</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleFetchDiffPreview(item.filename)}
                          className="text-[11px] bg-gradient-to-r from-blue-600/20 to-indigo-600/20 hover:from-blue-600/40 hover:to-indigo-600/40 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-xl font-bold transition-all cursor-pointer shadow-sm hover:scale-105 flex items-center gap-1.5"
                        >
                          <span>⚖️</span>
                          <span>{previewDiffFile === item.filename ? '이력 접기' : '개정 이력'}</span>
                        </button>
                        <button
                          onClick={() => handleDeleteRegulation(item.filename)}
                          className="text-[11px] bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/20 px-2.5 py-1 rounded-xl font-semibold transition-all cursor-pointer flex items-center gap-1"
                          title="조례 삭제"
                        >
                          <span>🗑️</span>
                          <span>삭제</span>
                        </button>
                      </div>
                    </div>

                    {/* 개정 이력 1클릭 프리뷰 카드 */}
                    {previewDiffFile === item.filename && (
                      <div className="mt-1 p-3.5 bg-slate-900/90 rounded-xl border border-blue-500/30 space-y-2 text-[11px] font-sans shadow-lg animate-fade-in">
                        <div className="flex justify-between items-center text-slate-300 border-b border-slate-800 pb-1.5">
                          <span className="font-bold text-blue-400 flex items-center gap-1.5">
                            <span>⚖️</span>
                            <span>조례 개정 전후 조항 변동 요약</span>
                          </span>
                          {isDiffLoading && <span className="text-[10px] text-blue-400 animate-pulse font-mono">pgvector 조항 연산 중...</span>}
                        </div>
                        {diffData ? (
                          <div className="space-y-1.5 text-slate-300">
                            <div className="flex items-center gap-3 text-[10px] font-mono bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                              <span className="text-emerald-400 font-bold">🟢 신규 {diffData.added_count || 0}</span>
                              <span className="text-amber-400 font-bold">🟡 수정 {diffData.modified_count || 0}</span>
                              <span className="text-rose-400 font-bold">🔴 삭제 {diffData.deleted_count || 0}</span>
                            </div>
                            <p className="text-[11px] text-slate-300 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80 font-sans">
                              {diffData.summary || "조항 변동 내역 연산 완료."}
                            </p>
                          </div>
                        ) : (
                          !isDiffLoading && <p className="text-[10px] text-slate-500">개정 변동 내역이 없거나 v1.0 단일 버전입니다.</p>
                        )}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 text-center py-6 border border-dashed border-slate-800 rounded-xl">
                  등록된 RAG 조례 문서가 없습니다.
                </div>
              )}
            </div>
          </div>

        </div>

        {/* 모달 푸터 */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/90 flex justify-end">
          <button
            onClick={showUpload ? onCloseUpload : onCloseList}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-5 py-2 rounded-xl transition-all cursor-pointer"
          >
            닫기
          </button>
        </div>

      </div>
    </div>
  );
}
