'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

export default function Home() {
  // 플랫폼 단계별 상태 제어 (Pipeline Wizard Steps)
  // Step 1: 데이터 일괄 업로드 및 감리 (Ingestion & AI Audit)
  // Step 2: 비주얼 HITL 좌표 보정 (Visual HITL Alignment)
  // Step 3: AHP 상대적 가중치 잠금 (AHP Weight Profile Lock)
  // Step 4: 최적 입지 선정 및 갈등도 평가 (PostGIS Filtering & CSS)
  // Step 5: AI 모의 심의 및 PDF 보고서 (AI Simulation & PDF Report)
  const [pipelineStep, setPipelineStep] = useState(1);

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
  const [missingCoordinates, setMissingCoordinates] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  // 1. AHP 가중치 입력 상태
  const [ahpWeights, setAhpWeights] = useState({
    traffic: 5,
    complaint: 5,
    dumping: 5,
    population: 5,
    youth: 5
  });
  const [crValue, setCrValue] = useState(0.04);
  const [isAhpLocked, setIsAhpLocked] = useState(false);

  // 2. 후보지 탭 및 상태 (Step 4 & 5에서 노출)
  const [activeTab, setActiveTab] = useState('top1');
  const [selectedParcel, setSelectedParcel] = useState({
    top1: { id: 1, pnu: '1117011200100420000', jibun: '한강로동 42-12 (국유지)', price: 14200000, area: 15, css: 78, cssGrade: '상', lat: 37.5302, lng: 126.9724, simulated: true },
    top2: { id: 2, pnu: '1117011200100450002', jibun: '한강로동 45-2 (시유지)', price: 9800000, area: 12, css: 45, cssGrade: '중', lat: 37.5328, lng: 126.9751, simulated: false },
    top3: { id: 3, pnu: '1117011300100120001', jibun: '이촌동 12-1 (구유지)', price: 18500000, area: 18, css: 12, cssGrade: '하', lat: 37.5255, lng: 126.9702, simulated: false }
  });

  // 3. 비주얼 HITL 보정 상태
  const [hitlJibun, setHitlJibun] = useState('');
  const [hitlLng, setHitlLng] = useState(126.9724);
  const [hitlLat, setHitlLat] = useState(37.5302);

  // 4. AI 시뮬레이션 상태
  const [showSimModal, setShowSimModal] = useState(false);
  const [simStep, setSimStep] = useState(0);
  const [simLogs, setSimLogs] = useState([]);

  // 5. 로그인 모달 상태
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [municipalId, setMunicipalId] = useState('');
  const [department, setDepartment] = useState('스마트도시과');

  // Leaflet 지도 인스턴스 참조
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const [leafletLoaded, setLeafletLoaded] = useState(false);

  // 위경도 결측치(Null/Zero)에 기반한 군부대/보안시설 우회 예외처리 함수
  const isValidCoordinate = (lat, lng) => {
    if (lat === null || lat === undefined || isNaN(lat) || lat === 0) return false;
    if (lng === null || lng === undefined || isNaN(lng) || lng === 0) return false;
    if (lat < 33.0 || lat > 39.0 || lng < 124.0 || lng > 132.0) return false; // 대한민국 위경도 한계 범주 검증
    return true;
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
        autoPan: false // 마커 드래그 시 지도 자동 스크롤(autoPan) 완전 차단
      }).addTo(map);

      // 법정 금제 원형 레이어 오버레이
      const subwayBuffer = L.circle([37.5290, 126.9680], {
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.25,
        radius: 30
      }).addTo(map);

      const schoolBuffer = L.circle([37.5315, 126.9740], {
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.15,
        radius: 200
      }).addTo(map);

      const militaryBuffer = L.circle([37.5240, 126.9650], {
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.1,
        radius: 400
      }).addTo(map);

      marker.on('dragstart', () => {
        map.dragging.disable(); // 마커 드래그 개시 시 지도 드래그 일시 잠금 (이격 예방)
      });

      marker.isWarning = false; // 드래그 도중 DOM 업데이트 쓰레싱 방지 플래그

      marker.on('drag', (e) => {
        const pos = e.target.getLatLng();
        const distSubway = pos.distanceTo(L.latLng(37.5290, 126.9680));
        const distSchool = pos.distanceTo(L.latLng(37.5315, 126.9740));
        const distMilitary = pos.distanceTo(L.latLng(37.5240, 126.9650));

        const shouldWarn = (distSubway < 30 || distSchool < 200 || distMilitary < 400);

        if (shouldWarn !== marker.isWarning) {
          marker.isWarning = shouldWarn;
          if (shouldWarn) {
            marker.setIcon(L.divIcon({
              className: 'custom-marker-warning',
              html: `<div style="
                width: 30px; 
                height: 30px; 
                background: #ef4444; 
                border: 2px solid white; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                font-size: 11px; 
                font-weight: bold; 
                color: white;
                box-shadow: 0 0 15px rgba(239,68,68,0.8);
              ">⚠️</div>`,
              iconSize: [30, 30]
            }));
          } else {
            marker.setIcon(markerIcon);
          }
        }
      });

      marker.on('dragend', () => {
        map.dragging.enable(); // 드래그 완료 시 지도 드래그 재활성화
        const newPos = marker.getLatLng();
        const distSubway = newPos.distanceTo(L.latLng(37.5290, 126.9680));
        const distSchool = newPos.distanceTo(L.latLng(37.5315, 126.9740));
        const distMilitary = newPos.distanceTo(L.latLng(37.5240, 126.9650));

        if (distSubway < 30 || distSchool < 200 || distMilitary < 400) {
          alert('⚠️ 경고: 해당 지점은 법정 금역 구역(지하철/학교/군사보호구역)에 침범합니다. 안전한 구역으로 위치를 복원합니다.');
          marker.setLatLng([hitlLat, hitlLng]);
          marker.setIcon(markerIcon);
          marker.isWarning = false;
          return;
        }
        setHitlLat(parseFloat(newPos.lat.toFixed(4)));
        setHitlLng(parseFloat(newPos.lng.toFixed(4)));
      });

      markersRef.current['temp'] = marker;
      markersRef.current['subway'] = subwayBuffer;
      markersRef.current['school'] = schoolBuffer;
      markersRef.current['military'] = militaryBuffer;
      map.panTo([hitlLat, hitlLng]);

    } else if (pipelineStep >= 4) {
      // Step 4 이상: 추천 후보 3개 마커 동시 드로잉
      Object.keys(selectedParcel).forEach(key => {
        const parcel = selectedParcel[key];

        // 결측 위경도(Null/Zero) 기반 군사보호/보안구역 자동 예외처리 및 렌더 제외
        if (!isValidCoordinate(parcel.lat, parcel.lng)) {
          console.warn(`[GIS Exception] ${key} (${parcel.jibun}) has invalid coordinates. Excluded as restricted/military zone.`);
          return;
        }

        const isSelected = activeTab === key;

        const markerIcon = L.divIcon({
          className: 'custom-marker',
          html: `<div style="
            width: 28px; 
            height: 28px; 
            background: ${isSelected ? 'hsl(217, 91%, 60%)' : 'hsla(142, 70%, 50%, 0.9)'}; 
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

      const activeParcel = selectedParcel[activeTab];
      if (activeParcel && isValidCoordinate(activeParcel.lat, activeParcel.lng)) {
        map.panTo([activeParcel.lat, activeParcel.lng]);
      }
    }
  }, [leafletLoaded, pipelineStep]);

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
      if (Math.abs(currentPos.lat - parcel.lat) > 0.005 || Math.abs(currentPos.lng - parcel.lng) > 0.005) {
        marker.setLatLng([parcel.lat, parcel.lng]);
      }

      // 아이콘 스타일 색상 업데이트 (transition: all 0.2s 삭제!)
      const markerIcon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="
          width: 28px; 
          height: 28px; 
          background: ${isSelected ? 'hsl(217, 91%, 60%)' : 'hsla(142, 70%, 50%, 0.9)'}; 
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
    const value = parseInt(val);
    setAhpWeights(prev => ({ ...prev, [key]: value }));
    const values = [...Object.values({ ...ahpWeights, [key]: value })];
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const mockCr = parseFloat(((maxVal - minVal) / 20).toFixed(2));
    setCrValue(mockCr);
  };

  // HITL 폼 동기화
  useEffect(() => {
    const active = selectedParcel[activeTab];
    setHitlJibun(active.jibun);
    setHitlLng(active.lng);
    setHitlLat(active.lat);
  }, [activeTab, selectedParcel]);

  // HITL 보정 완료
  const handleHitlCommit = async () => {
    if (!isValidCoordinate(hitlLat, hitlLng)) {
      alert('⚠️ 예외 감지: 입력된 좌표가 결측치(Null/Zero) 상태이거나 위경도 한계를 이탈했습니다. (군사기지 및 주요 보안시설로 자동 감지되어 분석 후보군에서 즉시 예외 처리 및 격리 제외됩니다.)');
      return;
    }

    const payload = {
      filename: uploadedCsvFilename || 'unknown.csv',
      column_mapping: columnMapping,
      corrections: missingCoordinates.map(mc => ({
        row_index: mc.row_index,
        lat: hitlLat,
        lng: hitlLng
      })),
      confirmed_domain: inferredDomainTag
    };

    try {
      const response = await fetch('/api/v1/upload/hitl/commit', {
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
    }
  };

  // AI 시뮬레이션 개시
  const runSimulation = () => {
    setShowSimModal(true);
    setSimStep(0);
    setSimLogs([]);
  };

  useEffect(() => {
    if (!showSimModal) return;

    const debateScripts = [
      { sender: '시스템', text: '⚡ pgvector RAG로부터 용산구 간재/행정 조례 데이터셋 매핑 완료...' },
      { sender: '시스템', text: `⚡ 지역 갈등 민감도 CSS(${selectedParcel[activeTab].css}점) 및 통제 인자 에이전트 주입 완료.` },
      { sender: '주민대표 (반대)', text: '🔴 학교 인근 정화구역 경계선 바로 바깥이라 해도, 아이들 보행 안전과 간접흡연 우려로 절대 찬성할 수 없습니다!' },
      { sender: '상인대표 (찬성)', text: '🔵 상가 앞 흡연 꽁초 투기로 매출 타격이 막심합니다. 규격화된 흡연부스를 세워 흡연자를 격리하는 것이 타개책입니다.' },
      { sender: '공무원 (조정)', text: '🟢 주민분들의 연막 소독 필터 및 운영시간 차단 요구를 조례 규칙 제4조에 의거 수용하여, 08시~22시 가동 락(Lock)을 조건으로 합의안을 발의합니다.' },
      { sender: '시스템', text: '✅ 시뮬레이션 분석 종결. 3대 시나리오 확률 예측: 시나리오 A(일반적 협상) 78% 타결 예상.' }
    ];

    if (simStep < debateScripts.length) {
      const timer = setTimeout(() => {
        setSimLogs(prev => [...prev, debateScripts[simStep]]);
        setSimStep(prev => prev + 1);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [showSimModal, simStep, activeTab]);

  // 로그인 처리
  const handleLogin = (e) => {
    e.preventDefault();
    if (!municipalId.trim()) {
      alert('공무원 ID를 입력해주세요.');
      return;
    }
    setIsLoggedIn(true);
    setShowLoginModal(false);
  };

  // 조례 목록 비동기 조회
  const fetchRegulations = async () => {
    try {
      const response = await fetch('/api/v1/upload/regulations');
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
      const response = await fetch(`/api/v1/upload/regulations/${encodeURIComponent(filename)}`, {
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

      const response = await fetch('/api/v1/upload/regulation', {
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
      const uploadRes = await fetch('/api/v1/upload', {
        method: 'POST',
        body: formData
      });
      if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(err.detail || '파일 업로드 실패');
      }
      const uploadData = await uploadRes.json();
      const filenames = uploadData.files.map(f => f.filename);

      // 2. AI 교차 시맨틱 목적 추론 감리 API 호출
      const auditRes = await fetch('/api/v1/upload/audit', {
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

      const csvResult = auditData.results.find(r => r.filename.endsWith('.csv'));
      if (csvResult) {
        setUploadedCsvFilename(csvResult.filename);
        setColumnMapping(csvResult.column_mapping || {});
        setMissingCoordinates([]);
        try {
          const geojsonRes = await fetch(`/api/v1/upload/geojson/${csvResult.filename}`);
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
        features: filenames
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
      
      {/* 1. 상단 글로벌 네비게이션 헤더 */}
      <header className="absolute top-0 left-0 right-0 h-16 glass-panel rounded-none border-t-0 border-x-0 z-45 px-8 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight text-white">OmniSite</span>
          <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30">B2G SDSS v1.0</span>
        </div>
        <nav className="flex items-center gap-8 text-xs font-semibold">
          <Link href="/" className="text-white border-b-2 border-blue-500 pb-1">입지분석 메인 (Map)</Link>
          <Link href="/dashboard" className="text-slate-400 hover:text-white transition-all pb-1">이력 대시보드 (Analytics)</Link>
        </nav>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => {
              setShowRegulationListModal(true);
              fetchRegulations();
            }}
            className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-slate-200 px-3.5 py-1.5 rounded-lg font-semibold cursor-pointer transition-all flex items-center gap-1.5"
          >
            📋 조례 목록 조회
          </button>
          <button 
            onClick={() => setShowRagModal(true)}
            className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-slate-200 px-3.5 py-1.5 rounded-lg font-semibold cursor-pointer transition-all flex items-center gap-1.5"
          >
            ⚖️ 법규 RAG 관리
          </button>
          {isLoggedIn ? (
            <span className="text-xs text-slate-300 font-medium">{department} | {municipalId}</span>
          ) : (
            <button 
              onClick={() => setShowLoginModal(true)}
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold cursor-pointer transition-all"
            >
              공무원 로그인
            </button>
          )}
        </div>
      </header>

      {/* 2. 인터랙티브 Leaflet GIS 3D 맵 공간 영역 (Map Container) */}
      <div id="interactive-map" className="map-container w-full h-full" />

      {/* 3. 좌측 플로팅 패널: 일괄 업로드 및 AHP 가중치 제어 (Upload & AHP Control Panel) */}
      <div className="floating-overlay left-6 top-20 w-96 glass-panel p-6 flex flex-col gap-6 max-h-[82vh] overflow-y-auto">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-sm font-bold text-white mb-0.5">입지선정 기준 설정</h2>
            <p className="text-[10px] text-slate-400">데이터 적재 및 가중치 의사결정 수립</p>
          </div>
          <span className="text-xs bg-blue-600/20 text-blue-400 px-2.5 py-1 rounded-full font-bold">
            Step {pipelineStep} / 5
          </span>
        </div>

        {/* RAG 조례 업로더는 독립 모달로 분리됨 */}

        {/* [Step 1] 공간 데이터 업로드 및 AI 감리 의도 검증 */}
        <div className={`flex flex-col gap-3 transition-all duration-300 ${pipelineStep !== 1 ? 'opacity-40 pointer-events-none' : ''}`}>
          <div className="flex justify-between items-center">
            <label className="text-xs font-semibold text-slate-300">Step 1. 공간 데이터 수집 & AI 감리</label>
            <span className="text-[10px] text-blue-400 font-mono">CSV 전용 (분석용)</span>
          </div>

          {!isAuditComplete ? (
            <div 
              onClick={triggerFileAudit}
              className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-5 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-900/30"
            >
              <p className="text-xs text-slate-300 font-semibold">📁 공간 데이터 CSV 업로드 (클릭)</p>
              <p className="text-[10px] text-slate-500 mt-1">컬럼명 및 위치 결측 검증 가동</p>
              {isUploading && <p className="text-[10px] text-amber-400 mt-1 animate-pulse">업로드 및 AI 감리 분석 중...</p>}
            </div>
          ) : (
            /* AI 감리 결과 판독 및 실무자 의도 승인 루프 */
            <div className="bg-slate-950/60 p-4 rounded-xl border border-blue-500/30 flex flex-col gap-3">
              <div className="flex justify-between items-center border-b border-slate-900 pb-1.5">
                <span className="text-[11px] text-blue-400 font-bold">✓ AI 감리 결과 분석 완료</span>
                <span className="text-[10px] text-slate-500">인프라 목적 판독</span>
              </div>
              <div className="text-[11px] flex flex-col gap-2.5 text-slate-300 leading-relaxed">
                <p><strong className="text-slate-400">분석 의도 판독:</strong> {inferredPurpose}</p>
                {inferredReasoning && (
                  <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800 text-[10px] text-slate-400 leading-normal font-mono">
                    <strong className="text-slate-300 block mb-1">🔍 AI 감리 추론 근거 (Reasoning):</strong>
                    {inferredReasoning}
                  </div>
                )}
                {hitlQuestion && (
                  <div className="bg-blue-950/40 p-2.5 rounded border border-blue-500/20 text-blue-300 font-medium">
                    ❓ {hitlQuestion}
                  </div>
                )}
                <div className="flex flex-col gap-1 my-1">
                  <span className="text-slate-400">분석 목적 보정 (HITL)</span>
                  <input
                    type="text"
                    value={userPurpose}
                    onChange={(e) => {
                      setUserPurpose(e.target.value);
                      setInferredPurpose(e.target.value);
                    }}
                    className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white text-[11px] outline-none focus:border-blue-500"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-slate-400">시맨틱 도메인 태그 지정</span>
                  <select
                    value={inferredDomainTag}
                    onChange={(e) => setInferredDomainTag(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-[11px] outline-none focus:border-blue-500"
                  >
                    <option value="smoking_zone">실외 흡연구역 입지 (smoking_zone)</option>
                    <option value="ev_charging">전기차 충전소 입지 (ev_charging)</option>
                    <option value="yellow_carpet">어린이 보호구역 옐로카펫 (yellow_carpet)</option>
                    <option value="city_feature">일반 스마트시티 시설물 (city_feature)</option>
                  </select>
                </div>
              </div>
              <button
                onClick={() => setPipelineStep(2)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold py-2.5 rounded-lg transition-all"
              >
                의도 일치 확인 및 공간 매핑 승인 (Approve)
              </button>
            </div>
          )}
          <input 
            type="file" 
            multiple 
            accept=".csv" 
            id="file-uploader" 
            className="hidden" 
            onChange={handleFileChange} 
          />
        </div>

        {/* [Step 3] AHP 슬라이더 컨트롤러 */}
        <div className={`flex flex-col gap-4 border-t border-slate-800/80 pt-4 transition-all duration-300 ${pipelineStep < 3 ? 'opacity-20 pointer-events-none' : ''} ${pipelineStep > 3 ? 'opacity-40 pointer-events-none' : ''}`}>
          <div className="flex justify-between items-center">
            <label className="text-xs font-semibold text-slate-300">Step 3. AHP 인자별 상대 가중치</label>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold transition-all ${crValue < 0.1 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
              C.R. = {crValue} ({crValue < 0.1 ? '만족' : '위배'})
            </span>
          </div>

          <div className="flex flex-col gap-3">
            {Object.keys(ahpWeights).map(key => (
              <div key={key} className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>{key === 'traffic' ? '대중교통 유동성' : key === 'complaint' ? '불법 민원빈도' : key === 'dumping' ? '상습 무단투기' : key === 'population' ? '배후 생활인구' : '청소년 비율'}</span>
                  <span className="font-mono text-white">{ahpWeights[key]}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="9"
                  disabled={isAhpLocked || pipelineStep !== 3}
                  value={ahpWeights[key]}
                  onChange={(e) => handleSliderChange(key, e.target.value)}
                  className="w-full accent-blue-500 cursor-pointer h-1 bg-slate-800 rounded-lg appearance-none"
                />
              </div>
            ))}
          </div>

          {/* AHP 잠금 버튼 -> 입지 분석 트리거 */}
          <button
            onClick={() => {
              setIsAhpLocked(true);
              setPipelineStep(4);
              alert('AHP 모델 일관성 검증 승인. PostGIS 다기준 공간 차집합 연산 기동 완료! [Step 4: 최적 입지 선정 결과]를 우측에서 확인하세요.');
            }}
            disabled={crValue >= 0.1 || pipelineStep !== 3}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all disabled:opacity-30"
          >
            🔒 AHP 가중치 확정 및 추천 입지 연산 (Lock)
          </button>
        </div>
      </div>

      {/* 4. 우측 플로팅 패널: 후보지 탭 및 속성 정보 카드 (Information & HITL Panel) */}
      <div className="floating-overlay right-6 top-20 w-96 glass-panel p-6 flex flex-col gap-5 max-h-[82vh] overflow-y-auto">
        
        {/* [Step 2] 비주얼 HITL 좌표 보정 영역 */}
        {pipelineStep === 2 && (
          <div className="flex flex-col gap-3">
            <div className="border-b border-slate-800 pb-2">
              <h2 className="text-xs font-bold text-amber-500">Step 2. 비주얼 HITL 좌표 보정 중</h2>
              <p className="text-[10px] text-slate-400 font-medium">지도의 주황색 핀을 드래그하거나 아래 좌표를 보정하세요</p>
            </div>
            
            <div className="bg-slate-950/40 p-4 rounded-xl border border-amber-500/30 flex flex-col gap-3">
              <div className="flex flex-col gap-1 text-xs">
                <span className="text-slate-400">임시 지번 주소 수정</span>
                <input 
                  type="text" 
                  value={hitlJibun} 
                  onChange={(e) => setHitlJibun(e.target.value)} 
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-amber-500"
                />
              </div>
              <div className="flex gap-2">
                <div className="flex-1 flex flex-col gap-1 text-[11px]">
                  <span className="text-slate-400">경도(Lng)</span>
                  <input type="number" step="0.0001" value={hitlLng} onChange={(e) => setHitlLng(parseFloat(e.target.value))} className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs" />
                </div>
                <div className="flex-1 flex flex-col gap-1 text-[11px]">
                  <span className="text-slate-400">위도(Lat)</span>
                  <input type="number" step="0.0001" value={hitlLat} onChange={(e) => setHitlLat(parseFloat(e.target.value))} className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs" />
                </div>
              </div>
              <button 
                onClick={handleHitlCommit}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs py-2 rounded-lg transition-all"
              >
                보정 완료 및 데이터 확정 (Commit)
              </button>
            </div>
          </div>
        )}

        {/* [Step 4 & 5] 최적 추천 후보지 리스트 정보 */}
        {pipelineStep >= 4 ? (
          <div className="flex flex-col gap-5">
            {/* Top 1 ~ Top 3 탭 */}
            <div className="flex bg-slate-950/60 p-1 rounded-lg border border-slate-800/80">
              {['top1', 'top2', 'top3'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 text-center py-1.5 text-xs font-semibold rounded-md cursor-pointer transition-all ${activeTab === tab ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  {tab.toUpperCase()}
                </button>
              ))}
            </div>

            {/* 필지 속성 카드 */}
            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold text-slate-300">Step 4. 추천지 속성 정보</h3>
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 flex flex-col gap-2.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">지번 / 소유 구분</span>
                  <span className="text-white font-semibold">{selectedParcel[activeTab].jibun}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">면적(㎡)</span>
                  <span className="font-mono text-white">{selectedParcel[activeTab].area} ㎡</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">공시지가</span>
                  <span className="font-mono text-emerald-400">₩ {selectedParcel[activeTab].price.toLocaleString()} / ㎡</span>
                </div>
                <div className="flex justify-between text-[11px] border-t border-slate-900 pt-2 text-slate-500">
                  <span>위도/경도 좌표</span>
                  <span className="font-mono">{selectedParcel[activeTab].lat}, {selectedParcel[activeTab].lng}</span>
                </div>
              </div>
            </div>

            {/* 갈등 민감도 카드 */}
            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-300">지역 갈등 민감도 (CSS)</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  selectedParcel[activeTab].cssGrade === '상' ? 'bg-rose-500/20 text-rose-400' :
                  selectedParcel[activeTab].cssGrade === '중' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-emerald-500/20 text-emerald-400'
                }`}>
                  등급: {selectedParcel[activeTab].cssGrade} ({selectedParcel[activeTab].css}점)
                </span>
              </div>

              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className={`h-full transition-all duration-500 ${
                  selectedParcel[activeTab].cssGrade === '상' ? 'bg-rose-500' :
                  selectedParcel[activeTab].cssGrade === '중' ? 'bg-amber-500' :
                  'bg-emerald-500'
                }`} style={{ width: `${selectedParcel[activeTab].css}%` }} />
              </div>
            </div>

            {/* [Step 5] AI 모의 토론 및 WeasyPrint PDF 발급 */}
            <div className="border-t border-slate-800/80 pt-4 flex flex-col gap-2">
              <span className="text-xs font-semibold text-slate-300">Step 5. 의사결정 시뮬레이션</span>
              <button 
                onClick={() => {
                  setPipelineStep(5);
                  runSimulation();
                }}
                className="w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs py-3 rounded-xl transition-all cursor-pointer shadow-lg shadow-rose-900/30"
              >
                {activeTab.toUpperCase()} 갈등 심의 시뮬레이터 실행 (GPT-4o)
              </button>
            </div>
          </div>
        ) : (
          pipelineStep !== 2 && (
            <div className="text-center py-20 text-slate-500 text-xs">
              [Step 1] 데이터 적재 및 <br />
              [Step 3] AHP 가중치 잠금을 진행하시면<br />
              이곳에 공간 차집합 추천 결과가 출력됩니다.
            </div>
          )
        )}
      </div>

      {/* AI 시뮬레이션 모달 팝업 */}
      {showSimModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="w-[800px] h-[550px] glass-panel p-6 flex flex-col justify-between">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-300">OMS-01-03-001 | AI 에이전트 실시간 모의 심의 토론</h3>
                <p className="text-[10px] text-slate-500">Target PNU: {selectedParcel[activeTab].pnu}</p>
              </div>
              <button 
                onClick={() => setShowSimModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
              >
                &times;
              </button>
            </div>

            {/* 터미널 대화 스크롤 */}
            <div className="flex-1 my-4 bg-slate-950/70 rounded-xl p-4 overflow-y-auto font-mono text-xs flex flex-col gap-3 border border-slate-900/80">
              {simLogs.map((log, index) => (
                <div key={index} className="flex gap-2">
                  <span className={`font-semibold shrink-0 ${
                    log.sender.startsWith('시스템') ? 'text-blue-400' :
                    log.sender.includes('반대') ? 'text-rose-400' :
                    log.sender.includes('찬성') ? 'text-emerald-400' : 'text-slate-300'
                  }`}>
                    [{log.sender}]
                  </span>
                  <span className="text-slate-200">{log.text}</span>
                </div>
              ))}
              {simStep < 6 && (
                <div className="text-slate-500 animate-pulse">... 에이전트 심의 분석 진행 중 ...</div>
              )}
            </div>

            {/* 하단 제어 바 (보고서 다운로드 포함) */}
            <div className="flex justify-between items-center border-t border-slate-800 pt-3">
              <span className="text-[10px] text-slate-500">
                도로점용료 예상액: ₩ {Math.round(selectedParcel[activeTab].area * selectedParcel[activeTab].price * 0.02 * (365/365)).toLocaleString()} / 년
              </span>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    alert('WeasyPrint를 통해 입지 타당성 분석 PDF를 컴파일 및 다운로드합니다.');
                  }}
                  disabled={simStep < 6}
                  className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-semibold text-xs px-4 py-2.5 rounded-lg transition-all cursor-pointer"
                >
                  📝 WeasyPrint PDF 보고서 다운로드
                </button>
                <button
                  onClick={() => setShowSimModal(false)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-4 py-2.5 rounded-lg transition-all cursor-pointer"
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 공무원 로그인 모달 */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="w-[400px] glass-panel p-6 flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-slate-300">도시행정망 실무자 인증</h3>
              <button onClick={() => setShowLoginModal(false)} className="text-slate-400 hover:text-white text-lg font-bold cursor-pointer">&times;</button>
            </div>

            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1 text-xs">
                <span className="text-slate-400">소속 자치구 / 부서</span>
                <select 
                  value={department} 
                  onChange={(e) => setDepartment(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                >
                  <option value="용산구 스마트도시과">용산구 스마트도시과</option>
                  <option value="용산구 도시계획과">용산구 도시계획과</option>
                  <option value="용산구 보건위생과">용산구 보건위생과</option>
                </select>
              </div>

              <div className="flex flex-col gap-1 text-xs">
                <span className="text-slate-400">공무원 행정 ID</span>
                <input 
                  type="text" 
                  placeholder="admin_yongsan"
                  value={municipalId}
                  onChange={(e) => setMunicipalId(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs py-2.5 rounded-lg transition-all"
              >
                행정망 접속 승인
              </button>
            </form>
          </div>
        </div>
      )}

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

    </div>
  );
}
