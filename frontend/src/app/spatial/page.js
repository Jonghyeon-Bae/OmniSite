'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import LoadingOverlay from '../../components/LoadingOverlay';
import ExclusionZoneControl from '../../components/ExclusionZoneControl';
import DebateSimulatorModal from '../../components/DebateSimulatorModal';
import SidebarControl from '../../components/SidebarControl';
import OptimalResultPanel from '../../components/OptimalResultPanel';

const apiFetch = (url, options = {}) => {
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('token') : null;
  const headers = {
    ...options.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
  const nativeFetch = typeof window !== 'undefined' ? window.fetch : (typeof globalThis !== 'undefined' ? globalThis.fetch : null);
  return nativeFetch ? nativeFetch(url, { ...options, headers }) : Promise.reject(new Error('Fetch not available'));
};

export default function Home() {
  const router = useRouter();

  // 🔒 행정망 인증 세션 가드 (JWT to SessionStorage 검사 및 미인가 차단)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = sessionStorage.getItem('token');
      if (!token) {
        alert("🔒 행정 인증 세션이 존재하지 않거나 만료되었습니다. 로그인 페이지로 이동합니다.");
        router.push('/');
      }
    }
  }, [router]);

  // 플랫폼 단계별 상태 제어 (Pipeline Wizard Steps)
  // Step 1: 데이터 일괄 업로드 및 감리 (Ingestion & AI Audit)
  // Step 2: 비주얼 HITL 좌표 보정 (Visual HITL Alignment)
  // Step 3: AHP 상대적 가중치 잠금 (AHP Weight Profile Lock)
  // Step 4: 최적 입지 선정 및 갈등도 평가 (PostGIS Filtering & CSS)
  // Step 5: AI 모의 심의 및 PDF 보고서 (AI Simulation & PDF Report)
  const [pipelineStep, setPipelineStep] = useState(1);

  // 🔒 로그인/로그아웃/자치구 상태 변수 (최상단 이동으로 ReferenceError 방지)
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [municipalId, setMunicipalId] = useState('');
  const [userRole, setUserRole] = useState('user');
  const [department, setDepartment] = useState('스마트도시과');
  const [userDistrictId, setUserDistrictId] = useState(1); // 동적 자치구 ID (Default: 1)

  // [Phase 2] 관리자 콘솔 및 시드 데이터 적재 상태
  const [showAdminConsoleModal, setShowAdminConsoleModal] = useState(false);
  const [seedTable, setSeedTable] = useState('cadastral_lands');
  const [isSeeding, setIsSeeding] = useState(false);
  
  // ML 모델 업로드 관련 상태
  const [modelDomain, setModelDomain] = useState('city_feature');
  const [isModelUploading, setIsModelUploading] = useState(false);

  // [Phase 2] 신규 실무관 등록용 상태 (최고관리자 콘솔 내 자동 연동)
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('user');
  const [regDept, setRegDept] = useState('스마트도시과');
  const [isRegistering, setIsRegistering] = useState(false);

  // Step 1 AI 감리 및 실무자 의도 매핑 검증 상태
  const [isAuditComplete, setIsAuditComplete] = useState(false);
  const [auditMetadata, setAuditMetadata] = useState(null);

  // 신규 AI 감리 & HITL 목적/도메인 바인딩 상태
  const [inferredPurpose, setInferredPurpose] = useState('');
  const [inferredDomainTag, setInferredDomainTag] = useState('city_feature');
  const [hitlQuestion, setHitlQuestion] = useState('');
  const [inferredReasoning, setInferredReasoning] = useState('');
  const [showRagModal, setShowRagModal] = useState(false);
  const [ragUploadSuccess, setRagUploadSuccess] = useState(false);
  const [isRegulationUploading, setIsRegulationUploading] = useState(false);
  const [showRegulationListModal, setShowRegulationListModal] = useState(false);
  const [regulationList, setRegulationList] = useState([]);
  const [userPurpose, setUserPurpose] = useState('');
  const [uploadedCsvFilename, setUploadedCsvFilename] = useState('');
  const [columnMapping, setColumnMapping] = useState({});
  const [csvHeaders, setCsvHeaders] = useState([]);
  const [missingCoordinates, setMissingCoordinates] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFilenames, setUploadedFilenames] = useState([]);
  const [fileBehaviors, setFileBehaviors] = useState({});
  const [showManualMapping, setShowManualMapping] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);

  // 1. AHP 가중치 입력 상태
  const [criteriaList, setCriteriaList] = useState([
    { key: 'traffic', label: '대중교통 유동성' },
    { key: 'complaint', label: '불법흡연 민원빈도' },
    { key: 'dumping', label: '상습 무단투기' },
    { key: 'population', label: '배후 생활인구' },
    { key: 'youth', label: '청소년 비율' }
  ]);
  const [ahpWeights, setAhpWeights] = useState({
    traffic: 5.0,
    complaint: 5.0,
    dumping: 5.0,
    population: 5.0,
    youth: 5.0
  });
  const [crValue, setCrValue] = useState(0.0);
  const [isAhpLocked, setIsAhpLocked] = useState(false);

  // 2. 후보지 탭 및 상태 (Step 4 & 5에서 노출)
  const [activeTab, setActiveTab] = useState('top1');
  const [selectedParcel, setSelectedParcel] = useState({
    top1: { id: 1, pnu: '1117011200100420000', jibun: '한강로동 42-12 (국유지)', price: 14200000, area: 15, css: 78, cssGrade: '상', lat: 37.5302, lng: 126.9724, simulated: true, is_fallback: false, reason: '의사결정 우선순위인 \'대중교통 유동성\' 지표 측면에서 가장 부합하는 정량적 우수 입지입니다.' },
    top2: { id: 2, pnu: '1117011200100450002', jibun: '한강로동 45-2 (시유지)', price: 9800000, area: 12, css: 45, cssGrade: '중', lat: 37.5328, lng: 126.9751, simulated: false, is_fallback: false, reason: '배후 주거 인구의 분포 비율 및 도로 접근성을 종합 검토하여 보통 등급으로 판정된 입지입니다.' },
    top3: { id: 3, pnu: '1117011300100120001', jibun: '이촌동 12-1 (구유지)', price: 18500000, area: 18, css: 12, cssGrade: '하', lat: 37.5255, lng: 126.9702, simulated: false, is_fallback: false, reason: '조례상 규제 구역 경계선과 다소 인접해 있으며 보행 가용폭 확인이 권장되는 필지입니다.' },
    top4: { id: 4, pnu: '1117011200100420001', jibun: '한강로동 42-13 (시유지)', price: 12000000, area: 20, css: 55, cssGrade: '중', lat: 37.5310, lng: 126.9730, simulated: false, is_fallback: true, reason: '법정 규제 완화 차선책으로, 규제 구역 인근의 실제 시유지 필지 중 조건이 적합한 곳을 탐색했습니다.' },
    top5: { id: 5, pnu: '1117011200100450003', jibun: '한강로동 45-3 (구유지)', price: 15500000, area: 22, css: 30, cssGrade: '하', lat: 37.5332, lng: 126.9760, simulated: false, is_fallback: true, reason: '법정 규제 완화 차선책으로, 규제 구역 인근의 실제 구유지 필지 중 조건이 적합한 곳을 탐색했습니다.' }
  });

  // 3. 비주얼 HITL 보정 상태
  const [hitlJibun, setHitlJibun] = useState('');
  const [hitlLng, setHitlLng] = useState(126.9724);
  const [hitlLat, setHitlLat] = useState(37.5302);
  const [isCommitting, setIsCommitting] = useState(false);

  // 4. AI 시뮬레이션 상태
  const [showSimModal, setShowSimModal] = useState(false);
  const [simStep, setSimStep] = useState(0);
  const [simLogs, setSimLogs] = useState([]);
  const [intensityLevel, setIntensityLevel] = useState("normal");
  const [dynamicPersonas, setDynamicPersonas] = useState(['찬성측', '반대측', '정부측']);

  // 4단계 추가 상태: 자치구 경계 및 규제 시설물 포인트
  const [districtGeoJson, setDistrictGeoJson] = useState(null);
  const [restrictionPoints, setRestrictionPoints] = useState([]);
  const [spatialRestrictions, setSpatialRestrictions] = useState({});
  const [userExclusionGeoJson, setUserExclusionGeoJson] = useState(null);
  const [isDrawingExclusion, setIsDrawingExclusion] = useState(false);
  const [drawnPoints, setDrawnPoints] = useState([]);
  const [panelPosition, setPanelPosition] = useState({ x: 420, y: 80 });
  const [dragStart, setDragStart] = useState(null);
  const [mapZoom, setMapZoom] = useState(14);
  // [v4.9.35] 국유재산 공간 폴리곤 데이터 GeoJSON 상태
  const [nationalPropertiesGeoJson, setNationalPropertiesGeoJson] = useState(null);

  // 최초 서비스 마운트 시 (웹 접속 시) 데이터베이스 및 로컬 캐시 초기화
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setPanelPosition({ x: 420, y: 80 });
    }

    apiFetch('/api/v1/upload/clear', { method: 'POST' })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) {
          console.log('[OmniSite Initialization] Cleared server upload caches:', data);
        }
      })
      .catch(err => {
        console.error('[OmniSite Initialization Error] Failed to clear upload caches:', err);
      });
  }, []);

  // [v4.4.1] 공간 통제 영역 제어판 마우스 드래그 이벤트 리스너
  useEffect(() => {
    if (!dragStart) return;
    const handleMouseMove = (e) => {
      const dx = e.clientX - dragStart.startX;
      const dy = e.clientY - dragStart.startY;
      setPanelPosition({
        x: dragStart.posX + dx,
        y: dragStart.posY + dy
      });
    };
    const handleMouseUp = () => {
      setDragStart(null);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragStart]);

  // Step 2 진입 시 관할 경계 GeoJSON 및 규제 시설물 목록 로드
  useEffect(() => {
    if (pipelineStep === 2) {
      apiFetch(`/api/v1/spatial/district-boundary/${userDistrictId}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => { if (data) setDistrictGeoJson(data); });
        
      apiFetch(`/api/v1/spatial/restrictions/points?facility_type=${inferredDomainTag || 'city_feature'}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => { if (data) setRestrictionPoints(data.points); });

      apiFetch('/api/v1/spatial/user-exclusions')
        .then(res => res.ok ? res.json() : null)
        .then(data => { if (data) setUserExclusionGeoJson(data); });

      // [v4.9.36] 국유재산 공간 데이터셋 로드 추가
      apiFetch('/api/v1/spatial/national-properties')
        .then(res => res.ok ? res.json() : null)
        .then(data => { if (data) setNationalPropertiesGeoJson(data); });
    }
  }, [pipelineStep, inferredDomainTag, userDistrictId]);

  // 컴포넌트 마운트 시 세션스토리지 기반 자동 로그인 복구 (SSR window is not defined 크래시 예방)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = sessionStorage.getItem('token');
      const savedUser = sessionStorage.getItem('username');
      const savedRole = sessionStorage.getItem('role');
      const savedDept = sessionStorage.getItem('department');
      const savedDistrict = sessionStorage.getItem('district_id');
      if (token && savedUser) {
        setIsLoggedIn(true);
        setMunicipalId(savedUser);
        setUserRole(savedRole || 'user');
        setDepartment(savedDept || '스마트도시과');
        const parsedDistrict = savedDistrict ? parseInt(savedDistrict, 10) : 1;
        setUserDistrictId(!isNaN(parsedDistrict) && parsedDistrict ? parsedDistrict : 1);
      }
    }
  }, []);



  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      sessionStorage.clear();
      setIsLoggedIn(false);
      setUserRole('user');
      setMunicipalId('');
      alert("정상적으로 행정 세션이 로그아웃(휘발 소거)되었습니다.");
      router.push('/');
    }
  };

  const handleSeedUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'csv') {
      alert('⚠️ 시드 데이터는 오직 CSV 형식만 지원합니다.');
      return;
    }
    
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
        const data = await res.json();
        alert(`✓ 벌크 적재 성공!\n테이블: ${seedTable}\n적재 메시지: ${data.message}\n공간 지오메트리 빌드: ${data.spatial_geometry_built ? "성공 (Point/4326)" : "없음"}`);
        setShowAdminConsoleModal(false);
      } else {
        const err = await res.json();
        throw new Error(err.detail || '벌크 적재 실패');
      }
    } catch (err) {
      alert(`벌크 적재 중 치명적 오류 발생: ${err.message}`);
    } finally {
      setIsSeeding(false);
    }
  };

  const handleModelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pkl') {
      alert('⚠️ 모델 파일은 오직 .pkl 확장자만 허용됩니다.');
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
        alert(`✓ ML 예측 모델 업로드 및 실시간 핫 바인딩 성공!\n도메인: ${modelDomain}`);
        setShowAdminConsoleModal(false);
      } else {
        const err = await res.json();
        throw new Error(err.detail || '모델 적재 실패');
      }
    } catch (err) {
      alert(`모델 적재 중 오류 발생: ${err.message}`);
    } finally {
      setIsModelUploading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (!regUsername || !regPassword) {
      alert("등록할 아이디와 비밀번호를 입력해 주십시오.");
      return;
    }

    setIsRegistering(true);
    try {
      // apiFetch는 sessionStorage 내의 어드민 JWT 토큰을 자동으로 헤더에 바인딩합니다!
      const res = await apiFetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: regUsername,
          password: regPassword,
          role: regRole,
          department: regDept
        })
      });

      if (res.ok) {
        alert(`✓ 신규 실무자 계정 [${regUsername}]이 성공적으로 등록되었습니다.\n부서: ${regDept} | 직위: ${regRole === 'admin' ? '관리자' : '실무관'}`);
        setRegUsername('');
        setRegPassword('');
        setRegRole('user');
        setRegDept('스마트도시과');
      } else {
        const errData = await res.json();
        throw new Error(errData.detail || "등록 처리 실패");
      }
    } catch (err) {
      alert(`실무자 계정 등록 중 오류 발생: ${err.message}`);
    } finally {
      setIsRegistering(false);
    }
  };

  // Leaflet 지도 인스턴스 참조
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const tempPointsRef = useRef([]);
  const tempMarkersRef = useRef([]);
  const tempPolylineRef = useRef(null);

  // [v4.9.21] 실제 법정 조례 규제에 완전히 동조하는 물리 미터 반경(m) 시각화 환원
  const getZoomAdjustedRadius = (pt, zoom) => {
    // 백엔드 PostGIS AHP 연산 규제 반경과 100% 동일하게 맵에 미터로 플롯
    if (pt.type === 'school' || pt.zone_type === 'school') return 200; // 학교정화구역 200m
    if (pt.type === 'childcare_center' || pt.zone_type === 'childcare_center') return 50; // 어린이집/유치원 50m
    if (pt.type === 'nosmoking_zone' || pt.zone_type === 'nosmoking_zone') return 10; // 금연구역 10m
    return pt.radius || 30;
  };

  // 위경도 결측치(Null/Zero)에 기반한 군부대/보안시설 우회 예외처리 함수
  const isValidCoordinate = (lat, lng) => {
    if (lat === null || lat === undefined || isNaN(lat) || lat === 0) return false;
    if (lng === null || lng === undefined || isNaN(lng) || lng === 0) return false;
    if (lat < 33.0 || lat > 39.0 || lng < 124.0 || lng > 132.0) return false; // 대한민국 위경도 한계 범주 검증
    return true;
  };

  const handleMouseDown = (e) => {
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
    setDragStart({
      startX: e.clientX,
      startY: e.clientY,
      posX: panelPosition.x,
      posY: panelPosition.y
    });
  };

  const clearTempDrawing = () => {
    tempMarkersRef.current.forEach(m => m.remove());
    tempMarkersRef.current = [];
    if (tempPolylineRef.current) {
      tempPolylineRef.current.remove();
      tempPolylineRef.current = null;
    }
    tempPointsRef.current = [];
  };

  const finishDrawingExclusion = async () => {
    const points = tempPointsRef.current;
    if (points.length < 3) {
      alert("⚠️ 통제 영역을 그리려면 최소 3개 이상의 지점을 마우스로 클릭해야 합니다.");
      clearTempDrawing();
      setIsDrawingExclusion(false);
      return;
    }

    const zoneName = prompt("✏️ 생성할 가상 금지구역(Exclusion Area)의 명칭을 입력해 주세요:");
    if (!zoneName) {
      clearTempDrawing();
      setIsDrawingExclusion(false);
      return;
    }

    const memoText = prompt("📝 해당 통제구역의 상세 사유 및 설명 메모를 입력해 주세요:");
    
    try {
      const res = await apiFetch('/api/v1/spatial/user-exclusions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          zone_name: zoneName,
          coordinates: points,
          memo: memoText || '지정 사유 없음'
        })
      });

      if (res.ok) {
        const resData = await res.json();
        alert(`✅ 저장 완료: ${resData.message}`);
        clearTempDrawing();
        setIsDrawingExclusion(false);

        const listRes = await apiFetch('/api/v1/spatial/user-exclusions');
        if (listRes.ok) {
          const listData = await listRes.json();
          setUserExclusionGeoJson(listData);
        }
      } else {
        const errData = await res.json();
        alert(`❌ 저장 실패: ${errData.detail || '알 수 없는 오류'}`);
        clearTempDrawing();
        setIsDrawingExclusion(false);
      }
    } catch (err) {
      console.error("Custom exclusion save error:", err);
      alert("❌ 서버 통신 오류로 인해 금지구역을 저장하지 못했습니다.");
      setIsDrawingExclusion(false);
    } finally {
      clearTempDrawing();
      if (mapRef.current) {
        mapRef.current.doubleClickZoom.enable();
      }
    }
  };

  // 플랫폼 데이터 및 분석 파이프라인 전체 초기화
  const handlePlatformReset = async () => {
    if (!confirm('⚠️ 플랫폼 데이터와 분석 파이프라인 단계를 모두 초기화하고 처음부터 다시 시작하시겠습니까?')) return;
    try {
      const res = await apiFetch('/api/v1/upload/clear', { method: 'POST' });
      if (res.ok) {
        // Step 1 및 파일 감리 상태 완전 초기화
        setPipelineStep(1);
        setIsAuditComplete(false);
        setAuditMetadata(null);
        setInferredPurpose('');
        setInferredDomainTag('city_feature');
        setHitlQuestion('');
        setInferredReasoning('');
        setUserPurpose('');
        setUploadedCsvFilename('');
        setColumnMapping({});
        setCsvHeaders([]);
        setMissingCoordinates([]);
        setIsUploading(false);
        setUploadedFilenames([]);
        setFileBehaviors({});
        setShowManualMapping(false);
        
        // Step 2 보정 상태 초기화
        setHitlJibun('');
        setHitlLng(126.9724);
        setHitlLat(37.5302);
        
        // Step 3, 4, 5 상태 초기화
        setSimLogs([]);
        setSimStep(0);
        setIsAhpLocked(false);

        // HTML 파일 인풋 값 강제 비우기 (처음부터 재업로드 가능하도록 지원)
        const fileInput = document.getElementById('file-uploader');
        if (fileInput) {
          fileInput.value = '';
        }
        
        alert('🔄 플랫폼 파이프라인 및 임시 공간 데이터 초기화가 완료되었습니다. Step 1 단계부터 다시 시작하십시오.');
      } else {
        alert('❌ 초기화 API 호출 실패');
      }
    } catch (err) {
      alert('❌ 초기화 오류: ' + err.message);
    }
  };

  const handleAhpLock = async () => {
    setIsRecommending(true);
    try {
      const finalDistrictId = !isNaN(parseInt(userDistrictId, 10)) ? parseInt(userDistrictId, 10) : 1;
      const lockRes = await apiFetch('/api/v1/ahp/lock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          district_id: finalDistrictId,
          facility_type: inferredDomainTag || 'smoking_zone',
          criteria_weights: ahpWeights,
          criteria_list: criteriaList,
          uploaded_files: uploadedFilenames
        })
      });
      if (!lockRes.ok) {
        const errData = await lockRes.json();
        let errMsg = '검증 실패';
        if (errData && errData.detail) {
          if (typeof errData.detail === 'string') {
            errMsg = errData.detail;
          } else {
            errMsg = JSON.stringify(errData.detail);
          }
        }
        alert('AHP 모델 락 오류: ' + errMsg);
        setIsRecommending(false);
        return;
      }
      const lockData = await lockRes.json();
      
      const targetLat = isNaN(hitlLat) ? 37.5302 : hitlLat;
      const targetLng = isNaN(hitlLng) ? 126.9724 : hitlLng;
      
      // 추천 입지 연산 기동 (HITL 마커 좌표 기준 인근 탐색, 동적 자치구 ID 및 가변 limit 6개 매핑)
      const recommendRes = await apiFetch(`/api/v1/spatial/recommend?model_id=${lockData.model_id}&ref_lat=${targetLat}&ref_lng=${targetLng}&district_id=${finalDistrictId}&limit=6`);
      if (!recommendRes.ok) {
        throw new Error('공간 입지 추천 연산 실패');
      }
      const recommendData = await recommendRes.json();
      
      // selectedParcel 업데이트 [v4.9.20] 동적 candidates 가변 수집 적용
      const cands = recommendData.candidates || {};
      setSelectedParcel(cands);
      
      const validKeys = Object.keys(cands).filter(k => cands[k] && cands[k].id);
      if (validKeys.length > 0) {
        setActiveTab(validKeys[0]);
      } else {
        setActiveTab('');
      }
      
      setIsAhpLocked(true);
      setPipelineStep(4);
      alert('AHP 모델 일관성 검증 승인. PostGIS 다기준 공간 차집합 연산 기동 완료! [Step 4: 최적 입지 선정 결과]를 우측에서 확인하세요.');
    } catch (err) {
      alert('오류 발생: ' + err.message);
    } finally {
      setIsRecommending(false);
    }
  };

  // 1. Leaflet 스크립트 및 CSS 로드 (최초 마운트 시 단 1회만 기동)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    }

    if (window.L) {
      setLeafletLoaded(true);
    } else {
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.async = true;
      script.onload = () => {
        setLeafletLoaded(true);
      };
      document.body.appendChild(script);
    }
  }, []);

  // 2. 지도 초기화 및 마커 동적 갱신 (leafletLoaded 및 pipelineStep 변경 시에만 안전 연동)
  useEffect(() => {
    if (!leafletLoaded) return;
    const L = window.L;
    if (!L) return;

    // 맵 객체 생성 (기존에 없을 때만 최초 1회)
    if (!mapRef.current) {
      const map = L.map('interactive-map', {
        zoomControl: false,
        dragging: true,           // 드래그 정상 허용 (마커 드래그 메커니즘 정상화)
        touchZoom: true,          // 터치 줌 허용
        scrollWheelZoom: true,     // 마우스 휠 줌 허용
        doubleClickZoom: true,     // 더블클릭 줌 허용
        boxZoom: true,             // 박스 줌 허용
        keyboard: true             // 키보드 이동 허용
      }).setView([37.5302, 126.9724], 14);

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
      }).addTo(map);

      map.on('zoomend', () => {
        setMapZoom(map.getZoom());
      });

      mapRef.current = map;
    }

    const map = mapRef.current;
    if (map) {
      map.dragging.enable();
      if (map.touchZoom) map.touchZoom.enable();
      if (map.doubleClickZoom) map.doubleClickZoom.enable();
      if (map.scrollWheelZoom) map.scrollWheelZoom.enable();
      if (map.boxZoom) map.boxZoom.enable();
      if (map.keyboard) map.keyboard.enable();
    }

    // 기존 맵 레이어/마커 일괄 청소 및 수거
    Object.values(markersRef.current).forEach(m => {
      if (m && typeof m.remove === 'function') {
        m.remove();
      }
    });
    markersRef.current = {};

    // 파이프라인 단계별 시각 요소 렌더링
    if (pipelineStep === 2) {
      const markerIcon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="
          width: 28px; 
          height: 28px; 
          background: hsl(28, 91%, 54%); 
          border: 2px solid white; 
          border-radius: 50%; 
          display: flex; 
          align-items: center; 
          justify-content: center; 
          font-size: 11px; 
          font-weight: bold; 
          color: white;
          box-shadow: 0 0 10px rgba(0,0,0,0.5);
        ">★</div>`,
        iconSize: [28, 28]
      });

      if (!isValidCoordinate(hitlLat, hitlLng)) {
        console.error("[Exception] Step 2 coordinate is invalid. Suspended rendering.");
        return;
      }

      const marker = L.marker([hitlLat, hitlLng], {
        icon: markerIcon,
        draggable: true,
        autoPan: true // 드래그 시 지도 자동 스크롤(autoPan) 지원으로 멈춤 현상 제거
      }).addTo(map);

      // 0. 관할 자치구 경계 GeoJSON 레이어 오버레이
      if (districtGeoJson) {
        const boundaryLayer = L.geoJSON(districtGeoJson, {
          style: {
            color: '#3b82f6',
            fillColor: '#3b82f6',
            fillOpacity: 0.04,
            weight: 2,
            dashArray: '5, 5'
          }
        }).addTo(map);
        markersRef.current['boundary'] = boundaryLayer;
      }

      // 0-1. 사용자 정의 금지구역(userExclusionGeoJson) 레이어 오버레이 [v4.4.1]
      if (userExclusionGeoJson) {
        const userExclLayer = L.geoJSON(userExclusionGeoJson, {
          style: {
            color: '#ea580c',
            fillColor: '#ea580c',
            fillOpacity: 0.28,      // [v4.9.37] 금지구역 강렬한 시각 가이드 (진하게)
            weight: 2.2
          },
          onEachFeature: (feature, layer) => {
            if (feature.properties && feature.properties.name) {
              layer.bindPopup(`
                <div style="font-family: inherit; font-size: 11px; padding: 4px; color: #1e293b;">
                  <strong style="color: #ea580c; font-size: 12px;">🚫 사용자 지정 통제 영역</strong><br/>
                  <span style="font-weight: 700; margin-top: 4px; display: inline-block;">명칭:</span> ${feature.properties.name}<br/>
                  <span style="font-weight: 700; margin-top: 2px; display: inline-block;">사유:</span> ${feature.properties.memo || '지정 사유 없음'}
                </div>
              `);
            }
          }
        }).addTo(map);
        markersRef.current['user_exclusion'] = userExclLayer;
      }

      // 0-2. 국유재산 공간 영역 GeoJSON 레이어 오버레이 (연한 하늘색) [v4.9.36]
      if (nationalPropertiesGeoJson) {
        const nationalLayer = L.geoJSON(nationalPropertiesGeoJson, {
          style: {
            color: '#38bdf8',       // [v4.9.37] 더 은은한 연한 하늘색 테두리
            fillColor: '#bae6fd',   // 더 부드러운 하늘색 면
            fillOpacity: 0.05,      // 더 연하게 투명도 대폭 낮춤 (연하게)
            weight: 1.0
          },
          onEachFeature: (feature, layer) => {
            if (feature.properties && feature.properties.jibun) {
              layer.bindPopup(`
                <div style="font-family: inherit; font-size: 11px; padding: 4px; color: #1e293b;">
                  <strong style="color: #0284c7; font-size: 12px;">🏛️ 국유부동산 대지</strong><br/>
                  <span style="font-weight: 700; margin-top: 4px; display: inline-block;">지번:</span> ${feature.properties.jibun}<br/>
                  <span style="font-weight: 700; margin-top: 2px; display: inline-block;">지목:</span> ${feature.properties.land_use_code || '미지정'}
                </div>
              `);
            }
          }
        }).addTo(map);
        markersRef.current['national_properties'] = nationalLayer;
      }

      // 1. 규제 시설물 포인트에 따른 동적 버퍼 오버레이 생성 (limit_radius 우선 적용, 조례 기준 점선 및 0.05 투명화) [v4.4.2]
      const circles = [];
      restrictionPoints.forEach((pt, idx) => {
        const limitRadius = getZoomAdjustedRadius(pt, mapZoom);
        
        if (limitRadius > 0) {
          const circle = L.circle([pt.lat, pt.lng], {
            color: '#dc2626',
            fillColor: '#dc2626',
            fillOpacity: 0.18,  // [v4.9.37] 규제 버퍼 시각성 증폭 (진하게)
            weight: 1.8,        // 두꺼운 테두리
            dashArray: '4, 4',  // 점선 테두리
            radius: limitRadius
          }).addTo(map);
          circles.push({ circle, pt, limitRadius });
          markersRef.current[`restriction_circle_${idx}`] = circle;
        }
      });

      marker.isWarning = false;

      marker.on('dragend', async () => {
        const newPos = marker.getLatLng();
        
        // 1. 규제 시설물 버퍼 침범 체크
        let violated = false;
        for (const item of circles) {
          const dist = newPos.distanceTo(L.latLng(item.pt.lat, item.pt.lng));
          if (dist < item.limitRadius) {
            violated = true;
            break;
          }
        }

        if (violated) {
          alert('⚠️ 경고: 해당 지점은 법정 규제 반경 내의 금제 구역에 침범합니다. 안전한 구역으로 위치를 복원합니다.');
          marker.setLatLng([hitlLat, hitlLng]);
          marker.setIcon(markerIcon);
          marker.isWarning = false;
          return;
        }

        // 2. 관할 자치구 경계선 이탈 체크 (PostGIS ST_Contains API 연동)
        try {
          const boundaryRes = await apiFetch('/api/v1/spatial/check-boundary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              lat: newPos.lat,
              lng: newPos.lng,
              district_id: 1
            })
          });
          if (boundaryRes.ok) {
            const boundaryData = await boundaryRes.json();
            if (!boundaryData.contained) {
              alert('⚠️ 경고: 마커가 관할 자치구(용산구) 경계를 벗어났습니다. 관할 구역 내에만 위치시킬 수 있습니다.');
              marker.setLatLng([hitlLat, hitlLng]);
              marker.setIcon(markerIcon);
              marker.isWarning = false;
              return;
            }
          }
        } catch (err) {
          console.error("Boundary check API failed:", err);
        }

        setHitlLat(parseFloat(newPos.lat.toFixed(6)));
        setHitlLng(parseFloat(newPos.lng.toFixed(6)));
      });

      markersRef.current['temp'] = marker;
    } else if (pipelineStep >= 4) {
      // Step 4 이상: 추천 후보 3개 마커 동시 드로잉

      // 0. 관할 자치구 경계 GeoJSON 레이어 오버레이
      if (districtGeoJson) {
        const boundaryLayer = L.geoJSON(districtGeoJson, {
          style: {
            color: '#3b82f6',
            fillColor: '#3b82f6',
            fillOpacity: 0.04,
            weight: 2,
            dashArray: '5, 5'
          }
        }).addTo(map);
        markersRef.current['boundary'] = boundaryLayer;
      }

      // 0-1. 사용자 정의 금지구역(userExclusionGeoJson) 레이어 오버레이 [v4.4.1]
      if (userExclusionGeoJson) {
        const userExclLayer = L.geoJSON(userExclusionGeoJson, {
          style: {
            color: '#ea580c',
            fillColor: '#ea580c',
            fillOpacity: 0.22,      // [v4.9.37] 금지구역 가시성 강화 (진하게)
            weight: 2.0
          },
          onEachFeature: (feature, layer) => {
            if (feature.properties && feature.properties.name) {
              layer.bindPopup(`
                <div style="font-family: inherit; font-size: 11px; padding: 4px; color: #1e293b;">
                  <strong style="color: #ea580c; font-size: 12px;">🚫 사용자 지정 통제 영역</strong><br/>
                  <span style="font-weight: 700; margin-top: 4px; display: inline-block;">명칭:</span> ${feature.properties.name}<br/>
                  <span style="font-weight: 700; margin-top: 2px; display: inline-block;">사유:</span> ${feature.properties.memo || '지정 사유 없음'}
                </div>
              `);
            }
          }
        }).addTo(map);
        markersRef.current['user_exclusion'] = userExclLayer;
      }

      // 0-2. 국유재산 공간 영역 GeoJSON 레이어 오버레이 (연한 하늘색) [v4.9.35]
      if (pipelineStep >= 4 && nationalPropertiesGeoJson) {
        const nationalLayer = L.geoJSON(nationalPropertiesGeoJson, {
          style: {
            color: '#0ea5e9',       // 연한 하늘색 테두리
            fillColor: '#38bdf8',   // 연한 하늘색 면
            fillOpacity: 0.16,      // 반투명도
            weight: 1.5
          },
          onEachFeature: (feature, layer) => {
            if (feature.properties && feature.properties.jibun) {
              layer.bindPopup(`
                <div style="font-family: inherit; font-size: 11px; padding: 4px; color: #1e293b;">
                  <strong style="color: #0284c7; font-size: 12px;">🏛️ 국유부동산 대지</strong><br/>
                  <span style="font-weight: 700; margin-top: 4px; display: inline-block;">지번:</span> ${feature.properties.jibun}<br/>
                  <span style="font-weight: 700; margin-top: 2px; display: inline-block;">지목:</span> ${feature.properties.land_use_code || '미지정'}
                </div>
              `);
            }
          }
        }).addTo(map);
        markersRef.current['national_properties'] = nationalLayer;
      }

      // 1. 규제 시설물 포인트에 따른 동적 버퍼 오버레이 생성 (점선 및 0.05 극저 투명화) [v4.4.2]
      restrictionPoints.forEach((pt, idx) => {
        const limitRadius = getZoomAdjustedRadius(pt, mapZoom);
        
        if (limitRadius > 0) {
          const circle = L.circle([pt.lat, pt.lng], {
            color: '#dc2626',
            fillColor: '#dc2626',
            fillOpacity: 0.15,  // [v4.9.37] 규제 버퍼 시각성 증폭 (진하게)
            weight: 1.5,        // 두꺼운 테두리
            dashArray: '4, 4',  // 점선 테두리
            radius: limitRadius
          }).addTo(map);
          markersRef.current[`restriction_circle_${idx}`] = circle;
        }
      });

      Object.keys(selectedParcel).forEach(key => {
        const parcel = selectedParcel[key];

        // 결측 위경도(Null/Zero) 기반 군사보호/보안구역 자동 예외처리 및 렌더 제외
        if (!isValidCoordinate(parcel.lat, parcel.lng)) {
          console.warn(`[GIS Exception] ${key} (${parcel.jibun}) has invalid coordinates. Excluded as restricted/military zone.`);
          return;
        }

        const isSelected = activeTab === key;

        const isNational = parcel.ownership_type === '국유지' || parcel.ownership_type === '국유재산';
        const markerIcon = L.divIcon({
          className: 'custom-marker',
          html: `<div style="
            width: 28px; 
            height: 28px; 
            background: ${isSelected ? 'hsl(217, 91%, 60%)' : isNational ? 'hsla(199, 89%, 55%, 0.9)' : 'hsla(142, 70%, 50%, 0.9)'}; 
            border: 2px solid white; 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 11px; 
            font-weight: bold; 
            color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
          ">${key.replace('top', '')}</div>`,
          iconSize: [28, 28]
        });

        const marker = L.marker([parcel.lat, parcel.lng], {
          icon: markerIcon,
          draggable: false
        }).addTo(map);

        marker.on('click', () => {
          setActiveTab(key);
        });

        markersRef.current[key] = marker;
      });

      // [v4.9.18] 사용자가 직접 지정한 HITL 보정 기준점(주황색 별)을 Step 4 이상에서도 유지하여 표시
      if (isValidCoordinate(hitlLat, hitlLng)) {
        const hitlIcon = L.divIcon({
          className: 'custom-marker',
          html: `<div style="
            width: 28px; 
            height: 28px; 
            background: hsl(28, 91%, 54%); 
            border: 2px solid white; 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 11px; 
            font-weight: bold; 
            color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
          ">★</div>`,
          iconSize: [28, 28]
        });

        const hitlMarker = L.marker([hitlLat, hitlLng], {
          icon: hitlIcon,
          draggable: false
        }).addTo(map);

        hitlMarker.bindPopup(`
          <div style="font-family: inherit; font-size: 11px; padding: 4px; color: #1e293b;">
            <strong style="color: #ea580c; font-size: 12px;">📍 보정 지정 기준점 (HITL)</strong><br/>
            실무자가 수동 보정 완료한 의사결정의 공간 중심점입니다. 후보지는 이 점을 기준으로 실시간 PostGIS 공간 분석되었습니다.
          </div>
        `);

        markersRef.current['hitl_step45'] = hitlMarker;
      }

    }
  }, [leafletLoaded, pipelineStep, districtGeoJson, restrictionPoints, spatialRestrictions, selectedParcel, userExclusionGeoJson, mapZoom, nationalPropertiesGeoJson]);

  // [v4.4.1] 사용자 정의 금지구역 마우스 드로잉 이벤트 연동
  useEffect(() => {
    if (!leafletLoaded || !mapRef.current || pipelineStep !== 2) return;
    const map = mapRef.current;
    const L = window.L;
    
    if (!isDrawingExclusion) {
      clearTempDrawing();
      return;
    }

    map.doubleClickZoom.disable();

    const handleMapClick = (e) => {
      if (!isDrawingExclusion) return;
      const { lat, lng } = e.latlng;
      const pt = [parseFloat(lng.toFixed(5)), parseFloat(lat.toFixed(5))];
      tempPointsRef.current.push(pt);
      
      const m = L.circleMarker(e.latlng, {
        radius: 4,
        color: '#f97316',
        fillColor: '#f97316',
        fillOpacity: 1
      }).addTo(map);
      tempMarkersRef.current.push(m);
      
      if (tempPolylineRef.current) {
        tempPolylineRef.current.remove();
      }
      const latlngs = tempPointsRef.current.map(p => [p[1], p[0]]);
      tempPolylineRef.current = L.polyline(latlngs, {
        color: '#f97316',
        weight: 2,
        dashArray: '3, 3'
      }).addTo(map);
    };

    const handleMapContextMenu = (e) => {
      if (e && e.originalEvent) {
        e.originalEvent.preventDefault();
        e.originalEvent.stopPropagation();
      }
      finishDrawingExclusion();
    };

    map.on('click', handleMapClick);
    map.on('contextmenu', handleMapContextMenu);

    return () => {
      map.off('click', handleMapClick);
      map.off('contextmenu', handleMapContextMenu);
      clearTempDrawing();
      map.doubleClickZoom.enable();
    };
  }, [leafletLoaded, isDrawingExclusion, pipelineStep]);

  // 마커 속성 및 지도 동기화 효과 (드래그 스냅 보정)
  useEffect(() => {
    const L = window.L;
    if (!L || !mapRef.current || pipelineStep < 4) return;

    Object.keys(selectedParcel).forEach(key => {
      const marker = markersRef.current[key];
      if (!marker) return;

      const parcel = selectedParcel[key];
      if (!isValidCoordinate(parcel.lat, parcel.lng)) return;

      const isSelected = activeTab === key;

      const currentPos = marker.getLatLng();
      if (currentPos.lat !== parcel.lat || currentPos.lng !== parcel.lng) {
        marker.setLatLng([parcel.lat, parcel.lng]);
      }

      // 아이콘 스타일 색상 업데이트 (transition: all 0.2s 삭제!)
      const isNational = parcel.ownership_type === '국유지' || parcel.ownership_type === '국유재산';
      const markerIcon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="
          width: 28px; 
          height: 28px; 
          background: ${isSelected ? 'hsl(217, 91%, 60%)' : isNational ? 'hsla(199, 89%, 55%, 0.9)' : 'hsla(142, 70%, 50%, 0.9)'}; 
          border: 2px solid white; 
          border-radius: 50%; 
          display: flex; 
          align-items: center; 
          justify-content: center; 
          font-size: 11px; 
          font-weight: bold; 
          color: white;
          box-shadow: 0 0 10px rgba(0,0,0,0.5);
        ">${key.replace('top', '')}</div>`,
        iconSize: [28, 28]
      });
      
      marker.setIcon(markerIcon);
    });

    const activeParcel = selectedParcel[activeTab];
    if (activeParcel && isValidCoordinate(activeParcel.lat, activeParcel.lng)) {
      mapRef.current.panTo([activeParcel.lat, activeParcel.lng]);
    }
  }, [activeTab, selectedParcel, pipelineStep]);

  // AHP 가중치 조절
  const handleSliderChange = (key, val) => {
    if (isAhpLocked) return;
    const value = parseFloat(val);
    const updatedWeights = { ...ahpWeights, [key]: value };
    setAhpWeights(updatedWeights);
    
    if (window.ahpCalcTimeout) {
      clearTimeout(window.ahpCalcTimeout);
    }
    
    window.ahpCalcTimeout = setTimeout(async () => {
      try {
        const finalDistrictId = !isNaN(parseInt(userDistrictId, 10)) ? parseInt(userDistrictId, 10) : 1;
        const res = await apiFetch('/api/v1/ahp/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            district_id: finalDistrictId,
            facility_type: inferredDomainTag || 'smoking_zone',
            criteria_weights: updatedWeights
          })
        });
        if (res.ok) {
          const data = await res.json();
          setCrValue(data.consistency_ratio);
        }
      } catch (err) {
        console.error("Failed to calculate AHP CR:", err);
      }
    }, 250);
  };

  // HITL 폼 동기화 (v4.9.19 | Step 2 일 때만 기동하여 Step 4/5 보정 기준점의 강제 오염 덮어쓰기 방지)
  useEffect(() => {
    if (pipelineStep !== 2) return;
    const active = selectedParcel[activeTab];
    if (active) {
      setHitlJibun(active.jibun || '');
      setHitlLng(active.lng || 126.9724);
      setHitlLat(active.lat || 37.5302);
    }
  }, [activeTab, selectedParcel]);

  // HITL 보정 완료
  const handleHitlCommit = async () => {
    if (!isValidCoordinate(hitlLat, hitlLng)) {
      alert('⚠️ 예외 감지: 입력된 좌표가 결측치(Null/Zero) 상태이거나 위경도 한계를 이탈했습니다. (군사기지 및 주요 보안시설로 자동 감지되어 분석 후보군에서 즉시 예외 처리 및 격리 제외됩니다.)');
      return;
    }

    setIsCommitting(true);
    const payload = {
      filename: uploadedCsvFilename || 'unknown.csv',
      column_mapping: columnMapping,
      corrections: missingCoordinates.map(mc => ({
        row_index: mc.row_index,
        lat: hitlLat,
        lng: hitlLng
      })),
      confirmed_domain: inferredDomainTag,
      file_behaviors: fileBehaviors
    };

    try {
      const response = await apiFetch('/api/v1/upload/hitl/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || '보정 커밋 실패');
      }
      const data = await response.json();
      
      setSelectedParcel(prev => ({
        ...prev,
        [activeTab]: {
          ...prev[activeTab],
          jibun: hitlJibun,
          lat: hitlLat,
          lng: hitlLng
        }
      }));
      setPipelineStep(3);
      alert(data.message || '공간 좌표 및 지번 속성이 보정 완료되었습니다. [Step 3: AHP 인자 설정] 단계를 진행합니다.');
    } catch (error) {
      alert('보정 커밋 중 오류: ' + error.message);
    } finally {
      setIsCommitting(false);
    }
  };

  // AI 시뮬레이션 개시
  const runSimulation = () => {
    setShowSimModal(true);
    setSimLogs([
      { sender: '시스템', text: '⚡ pgvector RAG로부터 관할 자치구 조례 데이터셋 매핑 완료...' },
      { sender: '시스템', text: `⚡ 지역 갈등 민감도 CSS(${selectedParcel[activeTab].css}점) 및 통제 인자 에이전트 주입 완료.` },
      { sender: '시스템', text: '💬 3자 모의 토론 채널 접속 중...' }
    ]);
  };

  useEffect(() => {
    if (!showSimModal) return;

    let isClosed = false;
    let reader = null;

    const startDebateStream = async () => {
      setSimStep(0);
      try {
        const payload = {
          facility_type: inferredDomainTag || "city_feature",
          inferred_purpose: inferredPurpose || "입지 분석",
          candidate_jibun: selectedParcel[activeTab]?.jibun || "용산구 미지정 부지",
          candidate_css: selectedParcel[activeTab]?.css || 50,
          candidate_lat: selectedParcel[activeTab]?.lat || 37.53,
          candidate_lng: selectedParcel[activeTab]?.lng || 126.97,
          ahp_weights: ahpWeights || {},
          intensity_level: intensityLevel,
          address_analysis: selectedParcel[activeTab]?.address_analysis || "",
          selection_reason: selectedParcel[activeTab]?.reason || ""
        };

        // Next.js BFF Proxy의 스트림 버퍼링 렉을 차단하기 위해, 백엔드 포트(8000)로 다이렉트 브라우저 SSE 통신 수행
        const backendBaseUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
        const res = await fetch(`${backendBaseUrl}/api/v1/spatial/debate`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionStorage.getItem('jwtToken') || ''}`
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          throw new Error(`SSE stream initiation failed: ${res.statusText}`);
        }

        reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let accumulatedText = '';

        const initialSystemLogs = [
          { sender: '시스템', text: '⚡ pgvector RAG로부터 관할 자치구 조례 데이터셋 매핑 완료...' },
          { sender: '시스템', text: `⚡ 지역 갈등 민감도 CSS(${selectedParcel[activeTab]?.css || 50}점) 및 통제 인자 에이전트 주입 완료.` },
          { sender: '시스템', text: '💬 3자 모의 토론 채널 접속 중...' }
        ];

        let activePersonas = [...dynamicPersonas];

        while (!isClosed) {
          const { value, done } = await reader.read();
          if (done) {
            setSimStep(6);
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop(); // 아직 완료되지 않은 라인은 버퍼로 이월

          for (const line of lines) {
            if (line.trim().startsWith('data:')) {
              const dataContent = line.replace('data:', '').trim();
              try {
                const data = JSON.parse(dataContent);
                if (data) {
                  if (data.meta && data.personas) {
                    activePersonas = data.personas;
                    setDynamicPersonas(data.personas);
                    continue;
                  }
                  
                  if (data.text) {
                    accumulatedText += data.text;
                    
                    // 누적 텍스트를 줄 단위로 분해하여 토론 로그 재구성
                    const parsedLogs = [];
                    const rawLines = accumulatedText.split('\n');
                    
                    const merchantName = activePersonas[0] || '찬성';
                    const residentName = activePersonas[1] || '반대';
                    const coordinatorName = activePersonas[2] || '정부';
                    
                    const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    
                    const merchantRegex = new RegExp(`^(${escapeRegExp(merchantName)}|찬성측|상인대표|상인|찬성)\\s*(\\(찬성\\))?:?\\s*`);
                    const residentRegex = new RegExp(`^(${escapeRegExp(residentName)}|반대측|주민대표|구민대표|주민|구민|반대)\\s*(\\(반대\\))?:?\\s*`);
                    const coordinatorRegex = new RegExp(`^(${escapeRegExp(coordinatorName)}|정부측|갈등조정관|조정관|정부)\\s*(\\(중재\\)|\\(조정안\\)|\\(조정\\))?:?\\s*`);
                    
                    for (let rawLine of rawLines) {
                      const trimmed = rawLine.trim();
                      if (!trimmed) continue;
                      
                      if (trimmed.startsWith('[')) {
                        parsedLogs.push({ sender: '시스템', text: trimmed });
                      } else if (merchantRegex.test(trimmed)) {
                        const content = trimmed.replace(merchantRegex, '');
                        parsedLogs.push({ sender: merchantName, text: content });
                      } else if (residentRegex.test(trimmed)) {
                        const content = trimmed.replace(residentRegex, '');
                        parsedLogs.push({ sender: residentName, text: content });
                      } else if (coordinatorRegex.test(trimmed)) {
                        const content = trimmed.replace(coordinatorRegex, '');
                        parsedLogs.push({ sender: coordinatorName, text: content });
                      } else {
                        if (parsedLogs.length > 0 && parsedLogs[parsedLogs.length - 1].sender !== '시스템') {
                          parsedLogs[parsedLogs.length - 1].text += ' ' + trimmed;
                        } else {
                          parsedLogs.push({ sender: '토론위원', text: trimmed });
                        }
                      }
                    }
                    
                    setSimLogs([...initialSystemLogs, ...parsedLogs]);
                  }
                }
              } catch (e) {
                console.error("Failed to parse stream chunk:", e);
              }
            }
          }
        }
      } catch (err) {
        console.error("Debate stream error:", err);
      }
    };

    startDebateStream();

    return () => {
      isClosed = true;
      if (reader) {
        reader.cancel().catch(() => {});
      }
    };
  }, [showSimModal, activeTab, intensityLevel]);



  // 조례 목록 비동기 조회
  const fetchRegulations = async () => {
    try {
      const response = await apiFetch('/api/v1/upload/regulations');
      if (!response.ok) throw new Error('조례 목록 조회 실패');
      const data = await response.json();
      setRegulationList(data.regulations || []);
    } catch (error) {
      console.error("Failed to fetch regulations:", error);
    }
  };

  // 조례 물리 삭제 및 캐시 수거 처리
  const handleDeleteRegulation = async (filename) => {
    if (!confirm(`정말로 '${filename}' 조례를 삭제하시겠습니까?\n삭제된 법규는 RAG 감리 데이터베이스에서 영구 제외됩니다.`)) {
      return;
    }
    try {
      const response = await apiFetch(`/api/v1/upload/regulations/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || '삭제 실패');
      }
      const data = await response.json();
      alert(data.message || '조례가 삭제되었습니다.');
      fetchRegulations();
    } catch (error) {
      alert('조례 삭제 중 오류: ' + error.message);
    }
  };

  // 조례 및 규제 법령 PDF 개별 등록 이벤트 핸들러 (다중 업로드 지원)
  const handleRegulationFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    for (let i = 0; i < files.length; i++) {
      const ext = files[i].name.split('.').pop().toLowerCase();
      if (ext !== 'pdf') {
        alert('⚠️ 조례/규칙 문서는 오직 PDF 형식만 업로드 가능합니다.');
        return;
      }
    }

    setIsRegulationUploading(true);
    setRagUploadSuccess(false);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      const response = await apiFetch('/api/v1/upload/regulation', {
        method: 'POST',
        body: formData
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || '조례 업로드 실패');
      }
      const data = await response.json();
      setRagUploadSuccess(true);
      fetchRegulations(); // 업로드 성공 시 목록 갱신
    } catch (error) {
      alert('조례 등록 중 오류: ' + error.message);
    } finally {
      setIsRegulationUploading(false);
    }
  };

  // 실제 공간 데이터(CSV) 파일 선택 이벤트 핸들러 및 AI 감리 API 트리거 (다중 업로드 지원)
  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    for (let i = 0; i < files.length; i++) {
      const ext = files[i].name.split('.').pop().toLowerCase();
      if (ext !== 'csv') {
        alert('⚠️ 공간 데이터셋은 오직 CSV 형식만 업로드 가능합니다.');
        return;
      }
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      // 1. 원천 데이터 일괄 업로드 API (CSV 다중 업로드)
      const uploadRes = await apiFetch('/api/v1/upload', {
        method: 'POST',
        body: formData
      });
      if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(err.detail || '파일 업로드 실패');
      }
      const uploadData = await uploadRes.json();
      const filenames = uploadData.files.map(f => f.filename);
      setUploadedFilenames(filenames);

      // 2. AI 교차 시맨틱 목적 추론 감리 API 호출
      const auditRes = await apiFetch('/api/v1/upload/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filenames })
      });
      if (!auditRes.ok) {
        throw new Error('AI 시맨틱 감리 분석 중 오류가 발생했습니다.');
      }
      const auditData = await auditRes.json();

      // 3. 추론 결과 기반 상태 세팅
      setInferredPurpose(auditData.inferred_purpose);
      setInferredDomainTag(auditData.inferred_domain_tag);
      setHitlQuestion(auditData.hitl_question);
      setInferredReasoning(auditData.reasoning || '');
      setUserPurpose(auditData.inferred_purpose);
      setSpatialRestrictions(auditData.spatial_restrictions || {});
      setFileBehaviors(auditData.file_behaviors || {});

      if (auditData.criteria && auditData.criteria.length > 0) {
        setCriteriaList(auditData.criteria);
        const initialWeights = {};
        auditData.criteria.forEach(c => {
          initialWeights[c.key] = c.initial_weight !== undefined ? c.initial_weight : 5.0;
        });
        setAhpWeights(initialWeights);
      }

      const csvResult = auditData.results.find(r => r.filename.endsWith('.csv'));
      if (csvResult) {
        setUploadedCsvFilename(csvResult.filename);
        setColumnMapping(csvResult.column_mapping || {});
        setCsvHeaders(csvResult.headers || []);
        setMissingCoordinates([]);
        try {
          const geojsonRes = await apiFetch(`/api/v1/upload/geojson/${csvResult.filename}`);
          if (geojsonRes.ok) {
            const geojsonData = await geojsonRes.json();
            const missing = geojsonData.features
              .filter(f => f.properties && f.properties.status === 'missing_coordinate')
              .map(f => ({
                row_index: f.properties.row_index,
                address: f.properties.address || '용산구 관내 결측지'
              }));
            setMissingCoordinates(missing);
            
            if (missing.length > 0) {
              setHitlJibun(missing[0].address);
              const firstMissingFeature = geojsonData.features.find(f => f.properties && f.properties.row_index === missing[0].row_index);
              if (firstMissingFeature && firstMissingFeature.geometry && firstMissingFeature.geometry.coordinates) {
                setHitlLng(firstMissingFeature.geometry.coordinates[0]);
                setHitlLat(firstMissingFeature.geometry.coordinates[1]);
              } else {
                setHitlLat(37.5395);
                setHitlLng(126.9721);
              }
            }
          }
        } catch (err) {
          console.error("Failed to fetch geojson coordinates for correction:", err);
        }
      }

      setAuditMetadata({
        fileName: filenames.join(' / '),
        schemaScore: 95,
        inferredIntention: auditData.inferred_purpose,
        features: filenames,
        hasRegulations: auditData.has_regulations
      });
      setIsAuditComplete(true);
    } catch (error) {
      alert('오류 발생: ' + error.message);
    } finally {
      setIsUploading(false);
    }
  };

  // 기존 모킹 함수는 백워드 컴팩트성을 위해 남겨둠
  const triggerFileAudit = () => {
    document.getElementById('file-uploader').click();
  };

  return (
    <div className="relative min-h-screen overflow-hidden text-slate-100 font-sans">
      
      {/* 글로벌 분석 로딩 오버레이 [v4.5.4] */}
      <LoadingOverlay isUploading={isUploading} isRecommending={isRecommending} />
      
      {/* 1. 상단 글로벌 네비게이션 헤더 (JWT Session-aware) */}
      <header className="absolute top-0 left-0 right-0 h-16 glass-panel rounded-none border-t-0 border-x-0 z-45 px-8 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight text-white">OmniSite</span>
          <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30">B2G SDSS v1.0</span>
        </div>
        <nav className="flex items-center gap-8 text-xs font-semibold">
          <Link href="/spatial" className="text-white border-b-2 border-blue-500 pb-1">입지분석 메인 (Map)</Link>
          <Link href="/dashboard" className="text-slate-400 hover:text-white transition-all pb-1">이력 대시보드 (Analytics)</Link>
        </nav>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => {
              setShowRegulationListModal(true);
              fetchRegulations();
            }}
            className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-slate-200 px-3.5 py-1.5 rounded-lg font-semibold cursor-pointer transition-all flex items-center gap-1.5"
          >
            📋 조례 목록 조회
          </button>

          {isLoggedIn ? (
            <div className="flex items-center gap-3">
              {/* 소속 부서 및 실무관 식별 */}
              <span className="text-[10px] bg-slate-800/80 border border-slate-700/80 text-slate-300 px-3 py-1.5 rounded-lg font-medium">
                🏢 {department} | <span className="font-bold text-white">{municipalId}</span> 실무관
              </span>
              
              {/* 관리자(Admin) 권한 가드 ⚙️ 버튼 동적 렌더링 */}
              {userRole === 'admin' && (
                <button 
                  onClick={() => setShowAdminConsoleModal(true)}
                  className="text-xs bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-400 px-3.5 py-1.5 rounded-lg font-bold cursor-pointer transition-all flex items-center gap-1.5"
                >
                  ⚙️ 관리자 콘솔
                </button>
              )}

              <button 
                onClick={handleLogout}
                className="text-xs bg-rose-950/45 hover:bg-rose-900/60 border border-rose-500/30 text-rose-300 px-3.5 py-1.5 rounded-lg font-semibold cursor-pointer transition-all flex items-center gap-1.5"
              >
                🔓 로그아웃
              </button>
            </div>
          ) : (
            <button 
              onClick={() => setShowLoginModal(true)}
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg font-bold cursor-pointer transition-all flex items-center gap-1.5 shadow-md shadow-blue-500/10"
            >
              🔒 행정망 로그인
            </button>
          )}
        </div>
      </header>

      {/* 2. 인터랙티브 Leaflet GIS 3D 맵 공간 영역 (Map Container) */}
      <div className="relative w-full h-full">
        <div id="interactive-map" className="map-container w-full h-full" />
        
        {/* [v4.4.1] 마우스로 끌어서 이동할 수 있는 공간 통제 영역 제어판 (Draggable Control Panel) */}
        <ExclusionZoneControl 
          pipelineStep={pipelineStep}
          panelPosition={panelPosition}
          handleMouseDown={handleMouseDown}
          isDrawingExclusion={isDrawingExclusion}
          setIsDrawingExclusion={setIsDrawingExclusion}
          finishDrawingExclusion={finishDrawingExclusion}
        />
      </div>

      {/* 3. 좌측 플로팅 패널: 일괄 업로드 및 AHP 가중치 제어 (Upload & AHP Control Panel) */}
      <SidebarControl
        pipelineStep={pipelineStep}
        setPipelineStep={setPipelineStep}
        isAuditComplete={isAuditComplete}
        triggerFileAudit={triggerFileAudit}
        isUploading={isUploading}
        isRecommending={isRecommending}
        auditMetadata={auditMetadata}
        inferredPurpose={inferredPurpose}
        setInferredPurpose={setInferredPurpose}
        inferredReasoning={inferredReasoning}
        hitlQuestion={hitlQuestion}
        userPurpose={userPurpose}
        setUserPurpose={setUserPurpose}
        inferredDomainTag={inferredDomainTag}
        setInferredDomainTag={setInferredDomainTag}
        handleFileChange={handleFileChange}
        crValue={crValue}
        criteriaList={criteriaList}
        ahpWeights={ahpWeights}
        isAhpLocked={isAhpLocked}
        handleSliderChange={handleSliderChange}
        handleAhpLock={handleAhpLock}
      />

      {/* 4. 우측 플로팅 패널: 후보지 탭 및 속성 정보 카드 (Information & HITL Panel) */}
      <OptimalResultPanel
        pipelineStep={pipelineStep}
        setPipelineStep={setPipelineStep}
        showManualMapping={showManualMapping}
        setShowManualMapping={setShowManualMapping}
        columnMapping={columnMapping}
        setColumnMapping={setColumnMapping}
        csvHeaders={csvHeaders}
        hitlLng={hitlLng}
        setHitlLng={setHitlLng}
        hitlLat={hitlLat}
        setHitlLat={setHitlLat}
        handleHitlCommit={handleHitlCommit}
        isCommitting={isCommitting}
        selectedParcel={selectedParcel}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        criteriaList={criteriaList}
        intensityLevel={intensityLevel}
        setIntensityLevel={setIntensityLevel}
        runSimulation={runSimulation}
        simStep={simStep}
        addressAnalysis={selectedParcel[activeTab]?.address_analysis || ""}
        isAnalyzingAddress={false}
      />

      {/* AI 시뮬레이션 모달 팝업 */}
      <DebateSimulatorModal
        showSimModal={showSimModal}
        setShowSimModal={setShowSimModal}
        selectedParcel={selectedParcel}
        activeTab={activeTab}
        simLogs={simLogs}
        simStep={simStep}
        intensityLevel={intensityLevel}
        setIntensityLevel={setIntensityLevel}
        setPipelineStep={setPipelineStep}
        runSimulation={runSimulation}
        inferredDomainTag={inferredDomainTag}
        inferredPurpose={inferredPurpose}
        ahpWeights={ahpWeights}
        apiFetch={apiFetch}
      />



      {/* ⚖️ 법규 RAG 관리 모달 (Ingestion Modal) */}
      {showRagModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-6 flex flex-col gap-4 relative animate-fade-in">
            <button 
              onClick={() => {
                setShowRagModal(false);
                setRagUploadSuccess(false);
              }}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>
            <div>
              <h3 className="text-sm font-bold text-white mb-1">⚖️ 법규 RAG 데이터베이스 관리</h3>
              <p className="text-[11px] text-slate-400">조례 및 시행령 PDF 문서를 텍스트로 벡터 캐싱하여 RAG 지식베이스를 구축합니다.</p>
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
                setShowRagModal(false);
                setRagUploadSuccess(false);
              }}
              className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-bold py-2.5 rounded-lg transition-all"
            >
              확인 및 닫기
            </button>
          </div>
        </div>
      )}

      {/* 📋 등록된 조례 목록 조회 모달 */}
      {showRegulationListModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-6 flex flex-col gap-4 relative animate-fade-in">
            <button 
              onClick={() => {
                setShowRegulationListModal(false);
              }}
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
              onClick={() => {
                setShowRegulationListModal(false);
              }}
              className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-bold py-2.5 rounded-lg transition-all"
            >
              닫기
            </button>
          </div>
        </div>
      )}

    


      {/* ⚙️ 관리자 전용 제어 콘솔 모달 */}
      {showAdminConsoleModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-6 flex flex-col gap-4 relative animate-fade-in">
            <button 
              onClick={() => setShowAdminConsoleModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold cursor-pointer"
            >
              ✕
            </button>
            <div>
              <span className="text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-400 px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                System Administrator Console
              </span>
              <h3 className="text-sm font-bold text-white mt-2">⚙️ 통합 관리자 콘솔</h3>
              <p className="text-[10px] text-slate-400">데이터베이스 벌크 적재, 초기화 및 법규 라이브러리 관리를 수행합니다.</p>
            </div>
            
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
                <label className="text-[11px] font-bold text-slate-200">🚀 원천 데이터 벌크 적재 (PostGIS Seed)</label>
                <div className="flex gap-2">
                  <select 
                    value={seedTable} 
                    onChange={(e) => setSeedTable(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none cursor-pointer w-full font-semibold"
                  >
                    <option value="cadastral_lands">지적 필지 정보 (cadastral_lands)</option>
                    <option value="civil_complaints">주민 민원 데이터 (civil_complaints)</option>
                    <option value="commercial_shops">상권 점포 정보 (commercial_shops)</option>
                    <option value="user_exclusion_zones">물리 장애물 금역 (user_exclusion_zones)</option>
                  </select>
                </div>
                <div 
                  onClick={() => document.getElementById('seed-csv-uploader').click()}
                  className="border-2 border-dashed border-slate-700 hover:border-amber-500 rounded-xl p-4 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30 flex flex-col items-center justify-center gap-1"
                >
                  <span className="text-lg">📁</span>
                  <p className="text-[11px] text-slate-300 font-semibold">벌크 CSV 데이터 업로드</p>
                  <p className="text-[9px] text-slate-500">지정 테이블에 to_sql 자동 공간 맵핑 적재를 실행합니다.</p>
                  {isSeeding && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">PostGIS 벌크 시딩 및 GIST 인덱싱 가동 중...</p>}
                </div>
                <input 
                  type="file" 
                  accept=".csv" 
                  id="seed-csv-uploader" 
                  className="hidden" 
                  onChange={handleSeedUpload} 
                />
              </div>

              {/* 기능 3: ML 모델 (.pkl) 업로드 및 핫 바인딩 */}
              <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
                <label className="text-[11px] font-bold text-slate-200">🤖 ML 예측 모델 (.pkl) 핫 업로드</label>
                <div className="flex gap-2">
                  <select 
                    value={modelDomain} 
                    onChange={(e) => setModelDomain(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none cursor-pointer w-full font-semibold"
                  >
                    <option value="city_feature">기본 도시 시설 도메인 (city_feature)</option>
                    <option value="smoking_zone">실외 흡연구역 도메인 (smoking_zone)</option>
                    <option value="ev_charging">전기차 충전소 도메인 (ev_charging)</option>
                  </select>
                </div>
                <div 
                  onClick={() => document.getElementById('seed-model-uploader').click()}
                  className="border-2 border-dashed border-slate-700 hover:border-amber-500 rounded-xl p-4 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30 flex flex-col items-center justify-center gap-1"
                >
                  <span className="text-lg">🤖</span>
                  <p className="text-[11px] text-slate-300 font-semibold">모델 파일 (.pkl) 업로드</p>
                  <p className="text-[9px] text-slate-500">지정 도메인에 XGBoost 예측 모델을 핫 로드합니다.</p>
                  {isModelUploading && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">모델 리로드 및 메모리 리인덱싱 중...</p>}
                </div>
                <input 
                  type="file" 
                  accept=".pkl" 
                  id="seed-model-uploader" 
                  className="hidden" 
                  onChange={handleModelUpload} 
                />
              </div>

              {/* 기능 4: 신규 실무자 (공무원) 추가 등록 폼 (최고관리자 토큰 자동 맵핑) */}
              <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
                <label className="text-[11px] font-bold text-slate-200">➕ 신규 실무자 (공무원) 계정 추가 등록</label>
                <form onSubmit={handleRegisterSubmit} className="flex flex-col gap-2 bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
                  <div className="flex gap-2">
                    <input 
                      type="text"
                      placeholder="신규 ID 입력"
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-[11px] text-white outline-none w-1/2 font-semibold"
                    />
                    <input 
                      type="password"
                      placeholder="비밀번호 설정"
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-[11px] text-white outline-none w-1/2 font-semibold"
                    />
                  </div>
                  <div className="flex gap-2">
                    <select 
                      value={regRole} 
                      onChange={(e) => setRegRole(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-[10px] text-white outline-none cursor-pointer w-1/2 font-semibold"
                    >
                      <option value="user">일반 실무자 (User)</option>
                      <option value="admin">최고 관리자 (Admin)</option>
                    </select>
                    <select 
                      value={regDept} 
                      onChange={(e) => setRegDept(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-[10px] text-white outline-none cursor-pointer w-1/2 font-semibold"
                    >
                      <option value="스마트도시과">스마트도시과</option>
                      <option value="도시행정정보과">도시행정정보과</option>
                      <option value="맑은환경과">맑은환경과</option>
                    </select>
                  </div>
                  <button 
                    type="submit"
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold py-2 rounded-lg transition-all shadow-md cursor-pointer mt-1"
                  >
                    {isRegistering ? "등록 요청 전송 중..." : "➕ 신규 실무관 승인 발급"}
                  </button>
                </form>
              </div>

              {/* 기능 2: 전체 리셋 단추 */}
              <div className="border-t border-slate-800 pt-3 flex justify-between items-center">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[11px] font-bold text-rose-400">🚨 시스템 데이터베이스 리셋</span>
                  <span className="text-[9px] text-slate-500">임시 캐시 및 저장 조례를 전역 삭제합니다.</span>
                </div>
                <button 
                  onClick={handlePlatformReset}
                  className="text-[10px] bg-rose-950/50 hover:bg-rose-900 border border-rose-500/30 text-rose-300 px-3.5 py-2 rounded-lg font-bold cursor-pointer transition-all"
                >
                  전체 리셋 실행
                </button>
              </div>
            </div>
            
            <button 
              onClick={() => setShowAdminConsoleModal(false)}
              className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-bold py-2.5 rounded-lg transition-all"
            >
              콘솔 닫기
            </button>
          </div>
        </div>
      )}
</div>
  );
}
