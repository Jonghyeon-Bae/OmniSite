import React, { useState, useEffect } from 'react';

export default function AdminConsoleModal({
  show,
  onClose,
  apiFetch,
  showToast,
  userDistrictId,
  mlStatus,
  setMlStatus,
  fetchMlStatus
}) {
  const [adminTab, setAdminTab] = useState('bulk');
  const [seedTable, setSeedTable] = useState('cadastral_lands');
  const [modelDomain, setModelDomain] = useState('smoking_zone');
  const [isSeeding, setIsSeeding] = useState(false);
  const [isModelUploading, setIsModelUploading] = useState(false);
  const [isRegulationUploading, setIsRegulationUploading] = useState(false);
  const [ragUploadSuccess, setRagUploadSuccess] = useState(false);
  const [adminUsers, setAdminUsers] = useState([]);
  const [masterKeyTabInput, setMasterKeyTabInput] = useState('');
  // 실무자 계정 등록 폼 상태
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('user');
  const [regDept, setRegDept] = useState('스마트도시과');
  const [isRegistering, setIsRegistering] = useState(false);

  // 데이터 규격 안내 모달 상태
  const [showDataGuideModal, setShowDataGuideModal] = useState(false);

  // 콜드스타트 위저드 및 ZIP 파일 상태
  const [coldStartFile, setColdStartFile] = useState(null);
  const [isColdStarting, setIsColdStarting] = useState(false);
  const [coldStartResult, setColdStartResult] = useState(null);

  // 4단계 순차 위저드 상태
  const [wizardStep, setWizardStep] = useState(1);
  const [step1SigFiles, setStep1SigFiles] = useState([]);
  const [step1EmdFiles, setStep1EmdFiles] = useState([]);
  const [step1MappingFile, setStep1MappingFile] = useState(null);
  
  const [step2CadFiles, setStep2CadFiles] = useState([]);
  const [step2PropertyFile, setStep2PropertyFile] = useState(null);
  const [step2BuildingFile, setStep2BuildingFile] = useState(null);
  
  const [step4RegulationFile, setStep4RegulationFile] = useState(null);
  const [step3Progress, setStep3Progress] = useState({
    restricted_zones: 'idle',
    transit_stations: 'idle',
    transit_passengers: 'idle',
    population_stats: 'idle'
  });
  const [wizardLoading, setWizardLoading] = useState(false);

  // 서버 레지스트리 ML 모델 목록 및 선택 상태
  const [registryModels, setRegistryModels] = useState([]);
  const [selectedDomainTag, setSelectedDomainTag] = useState('');

  // 서버 레지스트리에 저장된 모든 도메인 모델 메타데이터 스캔
  const fetchModelRegistry = async () => {
    try {
      const res = await apiFetch('/api/v1/model/registry');
      if (res.ok) {
        const data = await res.json();
        const models = data.models || [];
        setRegistryModels(models);
        if (models.length > 0 && !selectedDomainTag) {
          setSelectedDomainTag(models[0].domain);
        }
      }
    } catch (err) {
      console.error('모델 레지스트리 목록 조회 실패:', err);
    }
  };

  // 계정 관리 탭 클릭 시 사용자 목록 로드
  useEffect(() => {
    if (show && adminTab === 'users') {
      fetchAdminUsers();
    }
    if (show && adminTab === 'master_key') {
      fetchCurrentMasterKey();
          }
  }, [show, adminTab]);

  // 안전한 ML 상태 조회 헬퍼 (fetchMlStatus prop 유무에 관계없이 100% 안전 구동)
  const safeFetchMlStatus = async () => {
    if (typeof fetchMlStatus === 'function') {
      return await fetchMlStatus();
    }
    try {
      const res = await apiFetch('/api/v1/model/status');
      if (res.ok) {
        const data = await res.json();
        if (typeof setMlStatus === 'function') {
          setMlStatus(data);
        }
        return data;
      }
    } catch (err) {
      console.error('ML status fetch failed:', err);
    }
    return null;
  };

  // ML 모델 감사 탭 클릭 시 또는 모달 진입 시 레지스트리 모델 스캔
  useEffect(() => {
    if (show && adminTab === 'ml_retrain') {
      fetchModelRegistry();
      safeFetchMlStatus();
    }
  }, [show, adminTab]);

  // ML 상태 주기적 폴링 (학습 중일 때)
  useEffect(() => {
    let intervalId = null;
    if (mlStatus && mlStatus.is_training) {
      intervalId = setInterval(async () => {
        const status = await safeFetchMlStatus();
        if (status && !status.is_training) {
          clearInterval(intervalId);
          if (status.error) {
            showToast('❌ 모델 재학습이 실패했습니다:\n' + status.error, 'error');
          } else {
            showToast('🎉 XGBoost 모델 재학습 및 실시간 핫스왑 바인딩이 완공되었습니다!', 'success');
          }
        }
      }, 3000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [mlStatus?.is_training]);

  // 관리자 전용 사용자 계정 목록 조회
  const fetchAdminUsers = async () => {
    try {
      const res = await apiFetch('/api/v1/auth/users');
      if (res.ok) {
        const data = await res.json();
        setAdminUsers(data);
      }
    } catch (err) {
      console.error('사용자 계정 목록 로드 실패:', err);
    }
  };

  // 사용자 계정 삭제
  const handleUserDelete = async (userId, username) => {
    if (!confirm(`[ADMIN CONFIRM] 사용자 계정 '${username}'을 강제 영구 탈퇴/삭제하겠습니까?`)) {
      return;
    }
    try {
      const res = await apiFetch(`/api/v1/auth/users/${userId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showToast(`✓ 계정 '${username}'이 정상 삭제되었습니다.`, 'success');
        fetchAdminUsers();
      } else {
        const err = await res.json();
        showToast(err.detail || '삭제 실패', 'error');
      }
    } catch (err) {
      showToast('사용자 삭제 중 오류 발생', 'error');
    }
  };

  // 사용자 비밀번호 초기화 커스텀 모달 상태
  const [resetTargetUser, setResetTargetUser] = useState(null);
  const [resetPasswordInput, setResetPasswordInput] = useState('');

  const openPasswordResetModal = (user) => {
    setResetTargetUser(user);
    setResetPasswordInput('');
  };

  const handleUserPasswordResetSubmit = async (e) => {
    e.preventDefault();
    if (!resetTargetUser) return;
    
    const newPwd = resetPasswordInput;
    const hasLetter = /[A-Za-z]/.test(newPwd);
    const hasDigit = /\d/.test(newPwd);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newPwd);

    if (newPwd.length < 8 || !hasLetter || !hasDigit || !hasSpecial) {
      showToast('⚠️ 비밀번호는 영문, 숫자, 특수문자를 조합하여 8자리 이상이어야 합니다.', 'warning');
      return;
    }
    
    try {
      const res = await apiFetch(`/api/v1/auth/users/${resetTargetUser.id}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: newPwd })
      });
      if (res.ok) {
        showToast(`✓ 계정 '${resetTargetUser.username}'의 비밀번호가 성공적으로 변경되었습니다.`, 'success');
        setResetTargetUser(null);
        setResetPasswordInput('');
      } else {
        const err = await res.json();
        showToast(err.detail || '비밀번호 재설정 실패', 'error');
      }
    } catch (err) {
      showToast('비밀번호 재설정 중 오류 발생', 'error');
    }
  };

  // 신규 실무자 계정 가입 제출
  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (!regUsername || !regPassword) {
      showToast("등록할 아이디와 비밀번호를 입력해 주십시오.", "warning");
      return;
    }

    const hasLetter = /[A-Za-z]/.test(regPassword);
    const hasDigit = /\d/.test(regPassword);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(regPassword);

    if (regPassword.length < 8 || !hasLetter || !hasDigit || !hasSpecial) {
      showToast('⚠️ 비밀번호는 영문, 숫자, 특수문자를 조합하여 8자리 이상이어야 합니다.', 'warning');
      return;
    }

    setIsRegistering(true);
    try {
      const res = await apiFetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: regUsername,
          password: regPassword,
          role: regRole,
          department: regDept,
          district_id: userDistrictId
        })
      });

      if (res.ok) {
        showToast(`✓ 신규 실무자 계정 [${regUsername}]이 성공적으로 등록되었습니다.`, 'success');
        setRegUsername('');
        setRegPassword('');
        setRegRole('user');
        setRegDept('스마트도시과');
        fetchAdminUsers(); 
      } else {
        const errData = await res.json();
        throw new Error(errData.detail || "등록 처리 실패");
      }
    } catch (err) {
      showToast(`실무자 계정 등록 중 오류 발생: ${err.message}`, 'error');
    } finally {
      setIsRegistering(false);
    }
  };

  // CSV/Shapefile 원천 데이터 적재
  const handleSeedFileChange = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    const hasShp = files.some(f => f.name.endsWith('.shp'));
    const hasCsv = files.some(f => f.name.endsWith('.csv'));
    
    if (hasShp) {
      const shpFile = files.find(f => f.name.endsWith('.shp'));
      const dbfFile = files.find(f => f.name.endsWith('.dbf'));
      const shxFile = files.find(f => f.name.endsWith('.shx'));
      
      if (!shpFile || !dbfFile || !shxFile) {
        showToast('⚠️ Shapefile 적재를 위해서는 .shp, .dbf, .shx 파일들이 모두 한꺼번에 선택되어 업로드되어야 합니다.', 'warning');
        return;
      }
      
      if (!confirm(`[ADMIN ALERT] 선택한 Shapefile 셋(.shp, .dbf, .shx)을 '${seedTable}' 테이블에 공간 지오메트리 변환 적재하겠습니까?\n이 작업은 PostGIS 구면 좌표계 변환 트랜잭션을 강제 실행합니다.`)) {
        return;
      }
      
      setIsSeeding(true);
      try {
        const formData = new FormData();
        files.forEach(file => {
          formData.append('files', file);
        });
        
        const res = await apiFetch(`/api/v1/upload/seed-shapefile?target_table=${seedTable}`, {
          method: 'POST',
          body: formData
        });
        
        if (res.ok) {
          const data = await res.json();
          showToast(`✓ Shapefile 벌크 적재 성공! 결과: ${data.message}`, 'success');
          onClose();
        } else {
          const err = await res.json();
          throw new Error(err.detail || 'Shapefile 적재 실패');
        }
      } catch (err) {
        showToast(`Shapefile 적재 중 오류 발생: ${err.message}`, 'error');
      } finally {
        setIsSeeding(false);
      }
    } else if (hasCsv) {
      const file = files.find(f => f.name.endsWith('.csv'));
      if (!confirm(`[ADMIN ALERT] 선택한 CSV 파일을 '${seedTable}' 테이블에 벌크 적재하겠습니까?\n이 작업은 데이터베이스 인스턴스 DDL에 영향을 주며 공간 인덱스(GIST)가 강제 빌드됩니다.`)) {
        return;
      }
      
      setIsSeeding(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const res = await apiFetch(`/api/v1/upload/seed-spatial?target_table=${seedTable}&if_exists=append`, {
          method: 'POST',
          body: formData
        });
        
        if (res.ok) {
          showToast(`✓ 벌크 적재 성공! 테이블: ${seedTable}`, 'success');
          onClose();
        } else {
          const err = await res.json();
          throw new Error(err.detail || '벌크 적재 실패');
        }
      } catch (err) {
        showToast(`벌크 적재 중 치명적 오류 발생: ${err.message}`, 'error');
      } finally {
        setIsSeeding(false);
      }
    } else {
      showToast('⚠️ 허용되지 않는 파일 확장자입니다. .csv 또는 .shp/.dbf/.shx 셋을 업로드해 주십시오.', 'warning');
    }
  };

  // ML 모델 업로드 (.pkl)
  const handleModelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pkl') {
      showToast('⚠️ 모델 파일은 오직 .pkl 확장자만 허용됩니다.', 'warning');
      return;
    }
    
    if (!confirm(`[ADMIN ALERT] '${modelDomain}' 도메인의 예측 모델(.pkl)을 강제 업로드하여 핫 바인딩하겠습니까?\n이 작업은 실시간 입지 선정 예측 추천 스코어 모델 가중치를 영구 변경합니다.`)) {
      return;
    }
    
    setIsModelUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await apiFetch(`/api/v1/upload/model?domain_tag=${modelDomain}`, {
        method: 'POST',
        body: formData
      });
      
      if (res.ok) {
        showToast(`✓ ML 예측 모델 업로드 및 실시간 핫 바인딩 성공! 도메인: ${modelDomain}`, 'success');
        onClose();
      } else {
        const err = await res.json();
        throw new Error(err.detail || '모델 적재 실패');
      }
    } catch (err) {
      showToast(`모델 적재 중 오류 발생: ${err.message}`, 'error');
    } finally {
      setIsModelUploading(false);
    }
  };

  // RAG 조례 법령 PDF 적재
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

  // ZIP 콜드스타트 전체 빌드
  const handleColdStartUpload = async () => {
    if (!coldStartFile) {
      showToast("업로드할 ZIP 파일셋을 선택해 주십시오.", "warning");
      return;
    }
    if (!confirm("⚠️ 주의: 이 작업은 전체 데이터베이스의 지반 공간 정보(행정동, 지적도 등)를 완전히 파괴하고 새로 빌드합니다. 계속 진행하시겠습니까?")) {
      return;
    }
    
    setIsColdStarting(true);
    setColdStartResult(null);
    
    const formData = new FormData();
    formData.append("file", coldStartFile);
    
    try {
      const res = await apiFetch("/api/v1/upload/init-coldstart", {
        method: "POST",
        body: formData
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "인프라 초기 설정 중 서버 장애가 발생했습니다.");
      }
      
      setColdStartResult({
        status: "success",
        message: data.message,
        district: data.district,
        sig_cd: data.sig_cd,
        dongs: data.dongs_seeded,
        parcels: data.parcels_seeded
      });
      showToast(`✓ 인프라 초기 설정이 성공적으로 완공되었습니다! 대상 지자체: ${data.district}`, 'success');
    } catch (err) {
      showToast(`❌ 에러 발생: ${err.message}`, 'error');
      setColdStartResult({
        status: "error",
        message: err.message
      });
    } finally {
      setIsColdStarting(false);
    }
  };

  // ML 모델 재학습 요청
  const handleMlRetrain = async () => {
    if (mlStatus.is_training) return;
    if (!confirm('⚡ XGBoost ML 모델 재학습 파이프라인을 기동하시겠습니까?\n이 작업은 백그라운드에서 비동기로 실행됩니다.')) {
      return;
    }
    try {
      const res = await apiFetch('/api/v1/model/retrain', { method: 'POST' });
      if (res.ok) {
        showToast('✓ ML 모델 재학습 프로세스가 백그라운드에서 시작되었습니다.', 'success');
        setMlStatus(prev => ({ ...prev, is_training: true }));
      } else {
        const err = await res.json();
        showToast(err.detail || '재학습 요청 실패', 'error');
      }
    } catch (err) {
      showToast('ML 재학습 중 오류 발생: ' + err.message, 'error');
    }
  };

  // 위저드 1단계 업로드
  const handleStep1Upload = async () => {
    if (!step1MappingFile || step1EmdFiles.length === 0) {
      showToast('⚠️ 읍면동 경계 SHP 파일셋과 법정동 연계 CSV 파일은 필수입니다.', 'warning');
      return;
    }
    setWizardLoading(true);
    const formData = new FormData();
    formData.append('mapping_csv', step1MappingFile);
    step1SigFiles.forEach(f => formData.append('sig_files', f));
    step1EmdFiles.forEach(f => formData.append('emd_files', f));
    
    try {
      const res = await apiFetch('/api/v1/upload/seed-spatial-step1', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '1단계 적재 실패');
      
      showToast(`✓ 1단계 공간 뼈대 구축 완공!\n구역명: ${data.district_name} (행정동 ${data.dongs_count}개)`, 'success');
      setWizardStep(2);
    } catch (err) {
      showToast('❌ 1단계 에러: ' + err.message, 'error');
    } finally {
      setWizardLoading(false);
    }
  };

  // 위저드 2단계 업로드
  const handleStep2Upload = async () => {
    if (step2CadFiles.length === 0) {
      showToast('⚠️ 지적도 SHP 파일셋(.shp, .dbf, .shx)은 필수입니다.', 'warning');
      return;
    }
    setWizardLoading(true);
    const formData = new FormData();
    step2CadFiles.forEach(f => formData.append('cad_files', f));
    if (step2PropertyFile) {
      formData.append('property_csv', step2PropertyFile);
    }
    if (step2BuildingFile) {
      formData.append('building_csv', step2BuildingFile);
    }
    
    try {
      const res = await apiFetch('/api/v1/upload/seed-spatial-step2', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '2단계 적재 실패');
      
      showToast(`✓ 2단계 연속지적도 적재 완공!\n지적 필지 수: ${data.parcels_count}개, 표제부 건물 수: ${data.buildings_count || 0}개`, 'success');
      setWizardStep(3);
    } catch (err) {
      showToast('❌ 2단계 에러: ' + err.message, 'error');
    } finally {
      setWizardLoading(false);
    }
  };

  // 위저드 3단계 업로드
  const handleStep3Upload = async (fileType, file) => {
    if (!file) {
      showToast('업로드할 파일을 선택하십시오.', 'warning');
      return;
    }
    setStep3Progress(prev => ({ ...prev, [fileType]: 'loading' }));
    const formData = new FormData();
    formData.append('files', file);
    
    try {
      const res = await apiFetch(`/api/v1/upload/seed-spatial-step3?file_type=${fileType}`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '지표 적재 실패');
      
      showToast(`✓ [${fileType}] 적재 성공! (${data.inserted_rows}행 삽입)`, 'success');
      setStep3Progress(prev => ({ ...prev, [fileType]: 'success' }));
    } catch (err) {
      showToast(`❌ [${fileType}] 적재 에러: ` + err.message, 'error');
      setStep3Progress(prev => ({ ...prev, [fileType]: 'idle' }));
    }
  };

  // 위저드 4단계 최종 커밋
  const handleStep4Submit = async () => {
    setWizardLoading(true);
    const formData = new FormData();
    if (step4RegulationFile) {
      formData.append('regulation_file', step4RegulationFile);
    }
    
    try {
      const res = await apiFetch('/api/v1/upload/seed-spatial-step4', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '4단계 활성화 실패');
      
      showToast('🎉 4단계 위저드 최종 완공!\n스마트시티 입지 설정 및 GIS 인프라 락이 해제되었습니다.', 'success');
      setWizardStep(1);
      setStep1SigFiles([]);
      setStep1EmdFiles([]);
      setStep1MappingFile(null);
      setStep2CadFiles([]);
      setStep2PropertyFile(null);
      setStep4RegulationFile(null);
      setStep3Progress({
        restricted_zones: 'idle',
        transit_stations: 'idle',
        transit_passengers: 'idle',
        population_stats: 'idle'
      });
      onClose();
    } catch (err) {
      showToast('❌ 4단계 에러: ' + err.message, 'error');
    } finally {
      setWizardLoading(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-panel w-full max-w-4xl p-6 flex flex-col gap-4 relative animate-fade-in max-h-[90vh] overflow-y-auto text-slate-100">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
        >
          ✕
        </button>
        <div>
          <span className="text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-400 px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
            System Administrator Console
          </span>
          <h3 className="text-sm font-bold text-white mt-2">⚙️ 통합 관리자 콘솔</h3>
          <p className="text-[10px] text-slate-400">데이터베이스 벌크 적재, 예측 추천 모델 갱신 및 계정 생명주기를 통합 조립합니다.</p>
        </div>
        
        {/* 탭 네비게이터 */}
        <div className="flex border-b border-slate-800">
          <button 
            onClick={() => setAdminTab('bulk')}
            className={`flex-1 pb-2 text-[11px] font-bold text-center border-b-2 transition-all cursor-pointer ${adminTab === 'bulk' ? 'border-amber-500 text-amber-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            📊 데이터 벌크
          </button>
          <button 
            onClick={() => setAdminTab('users')}
            className={`flex-1 pb-2 text-[11px] font-bold text-center border-b-2 transition-all cursor-pointer ${adminTab === 'users' ? 'border-amber-500 text-amber-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            👥 계정 관리
          </button>

          <button 
            onClick={() => setAdminTab('ml_retrain')}
            className={`flex-1 pb-2 text-[11px] font-bold text-center border-b-2 transition-all cursor-pointer ${adminTab === 'ml_retrain' ? 'border-amber-500 text-amber-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            🤖 ML 모델 레지스트리 감사
          </button>
        </div>

        {adminTab === 'bulk' && (
          <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/40 flex flex-col gap-4">
            {/* RAG 관리 파트 통합 적재 */}
            <div className="flex flex-col gap-2">
              <label className="text-[11px] font-bold text-slate-200">⚖️ RAG 법규 라이브러리 적재</label>
              <div 
                onClick={() => document.getElementById('seed-regulation-uploader').click()}
                className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-4 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30 flex flex-col items-center justify-center gap-1"
              >
                <span className="text-lg">⚖️</span>
                <p className="text-[11px] text-slate-300 font-semibold">조례 PDF 파일 등록</p>
                <p className="text-[9px] text-slate-500">PDF RAG 임베딩 DB 벡터화를 진행합니다.</p>
                {isRegulationUploading && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">RAG 적재 및 벡터 캐싱 중...</p>}
              </div>
              {ragUploadSuccess && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] p-2 rounded-lg text-center font-medium">
                  ✓ 조례 법규의 RAG 벡터 적재가 성공적으로 완료되었습니다!
                </div>
              )}
              <input 
                type="file" 
                multiple 
                accept=".pdf" 
                id="seed-regulation-uploader" 
                className="hidden" 
                onChange={handleRegulationFileChange} 
              />
            </div>

            {/* 기능 1: 공간/행정 데이터 벌크 적재 */}
            <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-bold text-slate-200 flex items-center gap-2">
                  <span>🚀 원천 데이터 벌크 적재 (PostGIS CSV/Shapefile Seed)</span>
                  <button
                    type="button"
                    onClick={() => setShowDataGuideModal(true)}
                    className="px-2.5 py-0.5 text-[10px] font-bold bg-amber-500/15 hover:bg-amber-500/30 text-amber-400 border border-amber-500/40 rounded-full transition-all cursor-pointer flex items-center gap-1 shadow-sm hover:scale-105"
                  >
                    <span>💡 업로드 데이터 규격가이드</span>
                  </button>
                </label>
              </div>
              <div className="flex gap-2">
                <select 
                  value={seedTable} 
                  onChange={(e) => setSeedTable(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none cursor-pointer w-full font-semibold"
                >
                  <option value="cadastral_lands">지적 필지 정보 (cadastral_lands)</option>
                  <option value="civil_complaints">주민 민원 데이터 (civil_complaints)</option>
                  <option value="commercial_shops">상권 점포 정보 (commercial_shops)</option>
                  <option value="restricted_zones">용도제한 보호구역 (restricted_zones)</option>
                  <option value="user_exclusion_zones">물리 장애물 금역 (user_exclusion_zones)</option>
                  <option value="city_spatial_features">범용 공간 피처 (city_spatial_features)</option>
                </select>
              </div>
              <div 
                onClick={() => document.getElementById('seed-csv-uploader').click()}
                className="border-2 border-dashed border-slate-700 hover:border-amber-500 rounded-xl p-4 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30 flex flex-col items-center justify-center gap-1"
              >
                <span className="text-lg">📁</span>
                <p className="text-[11px] text-slate-300 font-semibold">벌크 CSV 또는 Shapefile 셋 업로드</p>
                <p className="text-[9px] text-slate-500">CSV 한 개 또는 Shapefile 셋(.shp,.dbf,.shx)을 드래그하여 공간 변환 적재합니다.</p>
                {isSeeding && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">PostGIS 벌크 시딩 및 GIST 인덱싱 가동 중...</p>}
              </div>
              <input 
                type="file" 
                multiple
                accept=".csv,.shp,.dbf,.shx" 
                id="seed-csv-uploader" 
                className="hidden" 
                onChange={handleSeedFileChange} 
              />
            </div>

          </div>
        )}

        {adminTab === 'users' && (
          <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/40 flex flex-col gap-4">
            <h4 className="text-xs font-bold text-white mb-2">👥 실무자 계정 목록 및 제어</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2">ID</th>
                    <th className="py-2">아이디</th>
                    <th className="py-2">직위</th>
                    <th className="py-2">부서</th>
                    <th className="py-2">자치구 ID</th>
                    <th className="py-2 text-center">보안 리셋 / 탈퇴</th>
                  </tr>
                </thead>
                <tbody>
                  {adminUsers.map(u => (
                    <tr key={u.id} className="border-b border-slate-800/40 text-slate-200 hover:bg-slate-950/20">
                      <td className="py-2 font-mono text-slate-400">{u.id}</td>
                      <td className="py-2 font-bold">{u.username}</td>
                      <td className="py-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${u.role === 'admin' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'}`}>
                          {u.role === 'admin' ? '최고관리자' : '실무관'}
                        </span>
                      </td>
                      <td className="py-2">{u.department || '스마트도시과'}</td>
                      <td className="py-2 font-mono text-slate-400">{u.district_id || 1}</td>
                      <td className="py-2 text-center flex items-center justify-center gap-2">
                        <button 
                          onClick={() => openPasswordResetModal(u)}
                          className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[10px] px-2 py-1 rounded transition-all cursor-pointer font-bold"
                        >
                          비밀번호 초기화
                        </button>
                        {u.username !== 'admin' && (
                          <button 
                            onClick={() => handleUserDelete(u.id, u.username)}
                            className="bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 text-[10px] px-2 py-1 rounded transition-all cursor-pointer font-bold"
                          >
                            강제 탈퇴
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 신규 실무자 계정 등록 폼 */}
            <form onSubmit={handleRegisterSubmit} className="border-t border-slate-800 pt-4 flex flex-col gap-3">
              <h5 className="text-[11px] font-bold text-slate-200">➕ 신규 스마트시티 실무자 승인 등록</h5>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] text-slate-400">아이디</label>
                  <input 
                    type="text"
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
                    placeholder="신규 아이디 입력"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] text-slate-400">초기 패스워드 (8자 이상, 영문+숫자+특수문자)</label>
                  <input 
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
                    placeholder="초기 비밀번호 (영문/숫자/특수문자 8자 이상)"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] text-slate-400">부서명</label>
                  <input 
                    type="text"
                    value={regDept}
                    onChange={(e) => setRegDept(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
                    placeholder="예: 스마트도시과, 자원순환과"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] text-slate-400">권한 구분</label>
                  <select 
                    value={regRole}
                    onChange={(e) => setRegRole(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none cursor-pointer"
                  >
                    <option value="user">일반 실무관 (User)</option>
                    <option value="admin">최고 시스템 관리자 (Admin)</option>
                  </select>
                </div>
              </div>
              <button 
                type="submit"
                disabled={isRegistering}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold py-2 rounded-lg transition-all mt-1 cursor-pointer"
              >
                {isRegistering ? "등록하는 중..." : "✓ 실무자 계정 등록 승인"}
              </button>
            </form>
          </div>
        )}

        {adminTab === 'ml_retrain' && (
          <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/40 flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2.5">
              <div>
                <h4 className="text-xs font-bold text-white mb-0.5">🤖 활성 ML 예측 모델 레지스트리 감사 (Model Registry Audit)</h4>
                <p className="text-[10px] text-slate-400">
                  서버 레지스트리(`backend/app/models/registry/`)에 실존하는 도메인별 XGBoost 모델의 성능 통계 및 피처 기여도를 감사 점검합니다.
                </p>
              </div>
              <button 
                onClick={fetchModelRegistry}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[10px] font-bold px-2.5 py-1 rounded transition-all cursor-pointer flex items-center gap-1"
              >
                🔄 목록 새로고침
              </button>
            </div>

            {/* 도메인 선택 칩 목록 */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold text-slate-300">📌 감지된 서버 등록 도메인 모델 목록 ({registryModels.length}개)</span>
              <div className="flex flex-wrap gap-2">
                {registryModels.length > 0 ? (
                  registryModels.map((m) => {
                    const isSelected = (selectedDomainTag || registryModels[0]?.domain) === m.domain;
                    return (
                      <button
                        key={m.domain}
                        onClick={() => setSelectedDomainTag(m.domain)}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all cursor-pointer border ${
                          isSelected
                            ? 'bg-amber-500/20 text-amber-400 border-amber-500/50 shadow-sm'
                            : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:text-slate-200'
                        }`}
                      >
                        🏷️ {m.domain} <span className="text-[9px] font-mono text-slate-500">({m.model_filename})</span>
                      </button>
                    );
                  })
                ) : (
                  <div className="text-[10px] text-slate-500 italic p-2 bg-slate-950 rounded-lg">
                    서버 레지스트리에 등록된 활성 ML 모델이 없습니다.
                  </div>
                )}
              </div>
            </div>

            {/* 선택된 도메인 모델의 상세 성능 카드 */}
            {(() => {
              const currentModel = registryModels.find(m => m.domain === (selectedDomainTag || registryModels[0]?.domain)) || registryModels[0];
              if (!currentModel) return null;
              
              const importances = currentModel.feature_importances || mlStatus?.feature_importances || {};

              return (
                <div className="flex flex-col gap-3">
                  <div className="grid grid-cols-3 gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <div className="flex flex-col gap-1 text-center">
                      <span className="text-[9px] text-slate-400">모델 정확도 (Accuracy)</span>
                      <span className="text-sm font-mono font-bold text-amber-400">
                        {currentModel.accuracy ? (currentModel.accuracy * 100).toFixed(1) + '%' : '미집계'}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1 text-center">
                      <span className="text-[9px] text-slate-400">조화 평균 (F1-Score)</span>
                      <span className="text-sm font-mono font-bold text-amber-400">
                        {currentModel.f1_score ? currentModel.f1_score.toFixed(3) : '미집계'}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1 text-center">
                      <span className="text-[9px] text-slate-400">최종 동적 학습 완료 시점</span>
                      <span className="text-[10px] font-mono font-bold text-slate-300 leading-normal">
                        {currentModel.last_trained_at || '정보 없음'}
                      </span>
                    </div>
                  </div>

                  {/* Feature Importance 차트 시각화 */}
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-bold text-slate-300">📊 [{currentModel.domain}] 의사결정 피처 기여도 (Feature Importance)</span>
                      <span className="text-[9px] text-slate-500 font-mono">파일 용량: {currentModel.file_size || 'N/A'}</span>
                    </div>
                    <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800 flex flex-col gap-2 max-h-48 overflow-y-auto">
                      {Object.keys(importances).length > 0 ? (
                        Object.entries(importances).map(([feature, val]) => (
                          <div key={feature} className="flex items-center text-[10px]">
                            <span className="w-44 text-slate-400 truncate">{feature}</span>
                            <div className="flex-1 bg-slate-800 h-2.5 rounded-full overflow-hidden mx-2">
                              <div 
                                className="bg-amber-500 h-full rounded-full transition-all" 
                                style={{ width: `${val * 100}%` }}
                              />
                            </div>
                            <span className="font-mono text-amber-400 w-10 text-right">{(val * 100).toFixed(1)}%</span>
                          </div>
                        ))
                      ) : (
                        <div className="text-[10px] text-slate-500 italic text-center py-3">
                          해당 모델의 세부 피처 중요도 정보가 없습니다.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg text-[10px] text-amber-300 flex items-center justify-between">
                    <span>💡 실시간 ML 예측 모델의 재학습은 AI 감리(Step 1 ➔ Step 2) 파이프라인 승인 시 도메인별로 자동 정밀 갱신됩니다.</span>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
        
        <button 
          onClick={onClose}
          className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-bold py-2.5 rounded-lg transition-all cursor-pointer"
        >
          콘솔 닫기
        </button>
      </div>

      {/* 💡 업로드 데이터 규격가이드 서브 모달 */}
      {showDataGuideModal && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-[60] flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-2xl p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100 max-h-[85vh] overflow-y-auto border border-amber-500/30">
            <button 
              onClick={() => setShowDataGuideModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>
            
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <span className="text-xl">💡</span>
              <div>
                <h4 className="text-sm font-bold text-amber-400">공간 및 행정 데이터 업로드 규격 상세 가이드</h4>
                <p className="text-[10px] text-slate-400">타 도메인 인프라(불법주정차, 킥보드, CCTV 등) 적용 시 필요한 파일 확장자 및 데이터 예시입니다.</p>
              </div>
            </div>

            {/* 1. 허용 확장자 규격 */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col gap-2">
              <h5 className="text-[11px] font-bold text-white flex items-center gap-1.5">
                <span>📁 1. 허용 파일 확장자 규격</span>
              </h5>
              <div className="grid grid-cols-3 gap-2 text-[10px]">
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-amber-400 font-bold block mb-1">.CSV 파일</span>
                  <span className="text-slate-400 text-[9px]">단일 텍스트 데이터. 위도/경도(lat, lng) 또는 PNU 필지고유번호 포함 필수.</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-blue-400 font-bold block mb-1">.SHP 세트 (Shapefile)</span>
                  <span className="text-slate-400 text-[9px]">.shp, .dbf, .shx 3종 이상을 한 번에 다중 선택하여 드래그앤드롭 업로드.</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-emerald-400 font-bold block mb-1">.PDF 조례 문서</span>
                  <span className="text-slate-400 text-[9px]">RAG 법률 자동 감리용 조례 및 시행령 비정형 텍스트 문서.</span>
                </div>
              </div>
            </div>

            {/* 2. 도메인별 업로드 데이터 예시 */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col gap-2">
              <h5 className="text-[11px] font-bold text-white flex items-center gap-1.5">
                <span>🎯 2. 도메인별 데이터셋 파일 및 지표 예시</span>
              </h5>
              <div className="space-y-2 text-[10px]">
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 flex flex-col gap-1">
                  <span className="text-amber-300 font-bold">🚗 불법주정차 단속 CCTV 입지선정 도메인</span>
                  <p className="text-slate-300 text-[9.5px] font-mono">권장 파일명: <span className="text-amber-400">용산구_불법주정차_단속CCTV_위치.csv</span> / <span className="text-blue-400">어린이보호구역_주정차금지.shp</span></p>
                  <p className="text-slate-400 text-[9px]">필수 포함 열: lat, lng, road_width(도로폭), complaint_count(단속민원수), zone_type</p>
                </div>

                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 flex flex-col gap-1">
                  <span className="text-teal-300 font-bold">🛴 공공 퍼스널모빌리티 (킥보드) 거치대 도메인</span>
                  <p className="text-slate-300 text-[9.5px] font-mono">권장 파일명: <span className="text-amber-400">공유킥보드_반납거치대_후보지.csv</span> / <span className="text-blue-400">자전거도로_연계구역.shp</span></p>
                  <p className="text-slate-400 text-[9px]">필수 포함 열: lat, lng, station_distance(지하철역거리), pedestrian_flow(유동인구)</p>
                </div>

                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 flex flex-col gap-1">
                  <span className="text-indigo-300 font-bold">🎥 스마트 도로 / 다목적 방범 CCTV 도메인</span>
                  <p className="text-slate-300 text-[9.5px] font-mono">권장 파일명: <span className="text-amber-400">도로_다목적_CCTV_설치현황.csv</span> / <span className="text-blue-400">용산구_도로망_네트워크.shp</span></p>
                  <p className="text-slate-400 text-[9px]">필수 포함 열: lat, lng, cctv_type, coverage_m(감시범위), road_class(도로등급)</p>
                </div>
              </div>
            </div>

            {/* 3. 데이터 오염 방지 안내 */}
            <div className="bg-emerald-500/10 border border-emerald-500/20 p-3 rounded-xl text-[10px] text-emerald-300 flex items-start gap-2">
              <span className="text-base">🛡️</span>
              <div className="leading-relaxed">
                <strong className="block text-emerald-200 mb-0.5">데이터 오염 방지 & 시맨틱 도메인 격리 안내</strong>
                업로드하신 데이터는 백엔드 OpenAI 임베딩 파이프라인에 의해 도메인 태그(예: <code className="text-amber-300">illegal_parking</code>, <code className="text-amber-300">kickboard</code>)가 자동 할당됩니다. 타 도메인 간 공간 데이터가 DB 내부에서 섞이거나 오염되지 않도록 완전히 파티셔닝되어 저장됩니다.
              </div>
            </div>

            <button 
              onClick={() => setShowDataGuideModal(false)}
              className="w-full bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold py-2 text-xs rounded-lg transition-all cursor-pointer shadow-lg mt-1"
            >
              확인 및 안내 닫기
            </button>
          </div>
        </div>
      )}

      {/* 🔑 관리자 전용 사용자 비밀번호 초기화 커스텀 모달 */}
      {resetTargetUser && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-[70] flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-6 flex flex-col gap-4 relative animate-fade-in text-slate-100 border border-amber-500/40 rounded-2xl shadow-2xl">
            <button 
              onClick={() => setResetTargetUser(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>
            
            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-xl text-amber-400">
                🔑
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">비밀번호 강제 초기화</h4>
                <p className="text-[10px] text-slate-400">계정 <span className="text-amber-400 font-bold">[{resetTargetUser.username}]</span>의 보안 비밀번호를 신규 설정합니다.</p>
              </div>
            </div>

            <form onSubmit={handleUserPasswordResetSubmit} className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-semibold text-slate-300">신규 보안 비밀번호</label>
                <input 
                  type="password"
                  value={resetPasswordInput}
                  onChange={(e) => setResetPasswordInput(e.target.value)}
                  className="bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl p-3 text-xs text-white outline-none transition-all"
                  placeholder="영문 / 숫자 / 특수문자 조합 8자 이상"
                  autoFocus
                />
                <p className="text-[9.5px] text-slate-500">※ 보안 규정에 따라 최소 8자 이상, 영문, 숫자, 특수문자(!@#$%^&*)를 필수 포함해야 합니다.</p>
              </div>

              <div className="flex gap-2 mt-2">
                <button 
                  type="button"
                  onClick={() => setResetTargetUser(null)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold py-2.5 rounded-xl cursor-pointer transition-all"
                >
                  취소
                </button>
                <button 
                  type="submit"
                  className="flex-1 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 text-xs font-extrabold py-2.5 rounded-xl transition-all shadow-md cursor-pointer"
                >
                  ✓ 비밀번호 변경 커밋
                </button>
              </div>
            </form>
          </div>

            {/* AI 프로바이더 & 로컬 LLM 핫 스와핑 컨트롤 카드 [v3.9.0] */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-blue-500/30 flex flex-col gap-3 font-sans mt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-blue-400 font-bold text-sm">
                  <span>🤖</span>
                  <span>AI 엔진 프로바이더 & 로컬 LLM 핫 스와핑 (Air-Gap Provider)</span>
                </div>
                <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded border border-blue-500/30 font-bold">
                  OmniSite Provider Engine
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                개발 환경(<code className="text-emerald-400 font-mono">Cloud OpenAI</code>)과 공공 폐쇄망 실증 환경(<code className="text-amber-400 font-mono">Ollama / vLLM - EXAONE 3.0 / Llama3</code>) 간 AI 모델을 OmniSite 재시작 없이 1초 만에 실시간 핫 스와핑합니다.
              </p>

              <form onSubmit={handleUpdateAiProviderSubmit} className="mt-2 flex flex-col gap-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] font-semibold text-slate-300">프로바이더 모드 선택</label>
                    <select
                      value={aiProviderType}
                      onChange={(e) => {
                        const val = e.target.value;
                        setAiProviderType(val);
                        if (val === 'ollama') {
                          setAiModelName('exaone3:7.8b');
                          setAiBaseUrl('http://localhost:11434/v1');
                        } else if (val === 'vllm') {
                          setAiModelName('Llama-3.1-Korean-8B');
                          setAiBaseUrl('http://localhost:8000/v1');
                        } else if (val === 'fallback') {
                          setAiModelName('local-rule-engine');
                          setAiBaseUrl('offline');
                        } else {
                          setAiModelName('gpt-4o-mini');
                          setAiBaseUrl('https://api.openai.com/v1');
                        }
                      }}
                      className="bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-amber-400 font-bold outline-none cursor-pointer"
                    >
                      <option value="openai">🌐 Cloud API Mode (OpenAI)</option>
                      <option value="ollama">🔒 온프레미스 로컬 LLM (Ollama - EXAONE)</option>
                      <option value="vllm">⚡ 고성능 GPU 클러스터 (vLLM)</option>
                      <option value="fallback">🛡️ 오프라인 룰 엔진 (Rule Fallback)</option>
                    </select>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] font-semibold text-slate-300">모델명 (Model Name)</label>
                    <input
                      type="text"
                      value={aiModelName}
                      onChange={(e) => setAiModelName(e.target.value)}
                      placeholder="예: exaone3:7.8b"
                      className="bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs font-mono text-white outline-none"
                      required
                    />
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] font-semibold text-slate-300">엔드포인트 URL (Base URL)</label>
                    <input
                      type="text"
                      value={aiBaseUrl}
                      onChange={(e) => setAiBaseUrl(e.target.value)}
                      placeholder="http://localhost:11434/v1"
                      className="bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs font-mono text-white outline-none"
                      required
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center mt-1">
                  <span className="text-[10px] text-slate-400">
                    * 로컬 LLM 선택 시 FastAPI 백엔드 메모리 부하 <strong className="text-emerald-400">0 MB (Zero Bloat)</strong>로 동작합니다.
                  </span>
                  <button
                    type="submit"
                    disabled={isUpdatingAiProvider}
                    className="px-4 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-lg cursor-pointer transition-all shadow-md active:scale-95 disabled:opacity-50"
                  >
                    {isUpdatingAiProvider ? '스와핑 중...' : '⚡ AI 프로바이더 핫 스와핑 저장'}
                  </button>
                </div>
              </form>
            </div>
        </div>
      )}
    </div>
  );
}
