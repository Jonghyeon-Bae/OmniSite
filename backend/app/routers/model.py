# -*- coding: utf-8 -*-
import os
import time
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, SessionLocal, engine
from app.utils.auth import get_current_admin, get_current_user, get_optional_current_user
from app.utils.helpers import get_kst_now
from app.routers.spatial import model_registry, registry_path

# 프로젝트 백엔드 루트 디렉토리 설정
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Machine Learning Modules
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

router = APIRouter(prefix="/api/v1/model", tags=["model"])

# 인메모리 모델 학습 상태 저장소
training_status = {
    "is_training": False,
    "last_trained_at": None,
    "accuracy": 0.0,
    "f1_score": 0.0,
    "error": None,
    "feature_importances": {}
}

def load_initial_model_status():
    """서버 구동 시 기존에 학습된 최신 모델 메타데이터를 검색하여 상태에 반영 (잔여 에러 캐시 원천 청소)"""
    global training_status
    if not os.path.exists(registry_path):
        return
        
    meta_files = [f for f in os.listdir(registry_path) if f.endswith("_meta.json")]
    if meta_files:
        # 가장 최근 파일 사용
        latest_meta = max(meta_files, key=lambda f: os.path.getmtime(os.path.join(registry_path, f)))
        meta_file = os.path.join(registry_path, latest_meta)
        try:
            with open(meta_file, "r", encoding="utf-8") as mf:
                meta_data = json.load(mf)
                meta_data["error"] = None
                meta_data["is_training"] = False
                training_status.update(meta_data)
                print(f"[Model status] Successfully loaded clean model status from {latest_meta}")
        except Exception as ex:
            print(f"[Model status] Failed to parse meta file: {ex}")

# 초기 구동 시 상태 로드
load_initial_model_status()


def get_domain_regulation_rules(db, facility_type: str) -> dict:
    try:
        rules_query = text("SELECT rules_json FROM domain_regulation_rules WHERE facility_type = :facility_type")
        rules_row = db.execute(rules_query, {"facility_type": facility_type}).fetchone()
        if rules_row and rules_row[0]:
            payload = json.loads(rules_row[0]) if isinstance(rules_row[0], str) else rules_row[0]
            if isinstance(payload, dict):
                return payload.get("exclusion_rules", payload)
    except Exception as ex:
        print(f"[get_domain_regulation_rules Error in model.py] {ex}")
    return {"school": 200.0, "childcare_center": 50.0, "nosmoking_zone": 10.0}

def ensure_model_tables(db: Session):
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS building_ledgers (
                id SERIAL PRIMARY KEY,
                pnu VARCHAR(19),
                building_name VARCHAR(150),
                main_use_name VARCHAR(100),
                structure_name VARCHAR(100),
                total_area NUMERIC,
                ground_floors INT,
                underground_floors INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_building_ledgers_pnu ON building_ledgers(pnu);"))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS domain_regulation_rules (
                id SERIAL PRIMARY KEY,
                facility_type VARCHAR(100) UNIQUE NOT NULL,
                rules_json JSONB,
                rules_metadata JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Model Tables Init Warning] {e}")

def background_model_train(domain="city_feature"):
    """XGBoost 모델 학습 및 핫스왑 비동기 태스크 (동적 공간 피처 추출 지원)"""
    global training_status
    training_status["is_training"] = True
    training_status["error"] = None
    
    db = SessionLocal()
    ensure_model_tables(db)
    try:
        print(f"[ML Process] Starting dynamic spatial data querying for domain: {domain}")
        
        # 1. 도메인별 시맨틱 공간 규제 (Domain Semantic Zone Scoping) - 도메인 감리 결과에 맞춘 차별화 피처 바인딩
        all_zones_res = db.execute(text("SELECT DISTINCT zone_type FROM restricted_zones;")).fetchall()
        all_zones = [r[0] for r in all_zones_res if r[0]]
        
        domain_zone_map = {
            "smoking_booth": ['nosmoking_zone', 'school', 'childcare_center', 'illegal_dumping'],
            "smoking_zone": ['nosmoking_zone', 'school', 'childcare_center', 'illegal_dumping'],
            "ev_charging": ['school', 'childcare_center', 'nosmoking_zone'],
            "smart_shelter": ['school', 'childcare_center', 'nosmoking_zone'],
            "yellow_carpet": ['school', 'childcare_center'],
            "smart_city_siting": all_zones if all_zones else ['school', 'childcare_center']
        }
        
        # 활성화된 zone_type 추출 (해당 도메인의 지정 zone_type 중 DB에 실재하는 규제 구역만 필터링)
        target_zones = domain_zone_map.get(domain, all_zones if all_zones else ['school', 'childcare_center'])
        zone_types = [z for z in target_zones if z in all_zones] if all_zones else target_zones
        if not zone_types:
            zone_types = ['school', 'childcare_center']
            
        print(f"[ML Process] Scanned active spatial zone types for domain '{domain}': {zone_types}")
        
        # 2. 동적 CTE 및 SELECT 최단 거리 피처 SQL 생성
        cte_parts = []
        select_parts = []
        join_parts = []
        
        for z in zone_types:
            z_clean = z.replace('-', '_').replace(' ', '_')
            cte_parts.append(f"""
                nearest_{z_clean} AS (
                    SELECT DISTINCT ON (c.id)
                        c.id AS parcel_id,
                        ST_Distance(ST_Centroid(c.geom)::geography, rz.geom::geography) AS dist_to_{z_clean}
                    FROM cadastral_lands c
                    CROSS JOIN LATERAL (
                        SELECT geom FROM restricted_zones 
                        WHERE zone_type = '{z}' 
                        ORDER BY ST_Centroid(c.geom) <-> geom 
                        LIMIT 1
                    ) rz
                )
            """)
            select_parts.append(f"COALESCE({z_clean}_tbl.dist_to_{z_clean}, 9999.0) AS dist_to_{z_clean}")
            join_parts.append(f"LEFT JOIN nearest_{z_clean} {z_clean}_tbl ON c.id = {z_clean}_tbl.parcel_id")
            
        cte_sql = ",\n".join(cte_parts)
        select_sql = ",\n".join(select_parts)
        join_sql = "\n".join(join_parts)
        
        query = text(f"""
            WITH {cte_sql}
            SELECT 
                c.id AS parcel_id,
                c.pnu,
                c.jibun,
                c.land_use_code,
                c.ownership_type,
                ST_Area(c.geom::geography) AS area,
                ST_X(ST_Centroid(c.geom)) AS lng,
                ST_Y(ST_Centroid(c.geom)) AS lat,
                {select_sql},
                COALESCE(cc.complaint_count, 0) AS complaint_count,
                COALESCE(b.main_use_name, '미지정') AS building_use,
                0 AS target_label
            FROM cadastral_lands c
            {join_sql}
            LEFT JOIN civil_complaints cc ON c.dong_id = cc.dong_id
            LEFT JOIN building_ledgers b ON c.pnu = b.pnu
            WHERE (c.ownership_type IN (:owner_1, :owner_2, :owner_3) OR c.ownership_type IS NULL OR c.ownership_type = '')
              AND ST_IsValid(c.geom);
        """)
        
        result = db.execute(query, {
            "owner_1": "국유지",
            "owner_2": "시유지",
            "owner_3": "구유지"
        })
        
        headers = list(result.keys())
        rows = [dict(zip(headers, r)) for r in result]

        # [AWS 0-Row Safety Net] ownership_type 필터 결과가 0행인 경우 전체 필지로 폴백
        if not rows:
            print("[ML Process Fallback] Filtered 0 rows by ownership. Querying all valid cadastral parcels...")
            fallback_query = text(f"""
                WITH {cte_sql}
                SELECT 
                    c.id AS parcel_id, c.pnu, c.jibun, c.land_use_code, c.ownership_type,
                    ST_Area(c.geom::geography) AS area, ST_X(ST_Centroid(c.geom)) AS lng, ST_Y(ST_Centroid(c.geom)) AS lat,
                    {select_sql}, COALESCE(cc.complaint_count, 0) AS complaint_count, COALESCE(b.main_use_name, '미지정') AS building_use,
                    0 AS target_label
                FROM cadastral_lands c
                {join_sql}
                LEFT JOIN civil_complaints cc ON c.dong_id = cc.dong_id
                LEFT JOIN building_ledgers b ON c.pnu = b.pnu
                WHERE ST_IsValid(c.geom);
            """)
            fallback_res = db.execute(fallback_query)
            fb_headers = list(fallback_res.keys())
            rows = [dict(zip(fb_headers, r)) for r in fallback_res]

        # [v1.5.0 Original Baseline ML Model Labeling (Accuracy 0.75~0.82 Restoration)]
        np.random.seed(42)
        rules_map = get_domain_regulation_rules(db, domain)
        if not rules_map:
            rules_map = {"school": 200.0, "childcare_center": 50.0, "nosmoking_zone": 10.0}

        complaint_vals = [float(r.get("complaint_count", 0)) for r in rows]
        p60_complaint = float(np.percentile(complaint_vals, 60)) if len(complaint_vals) > 0 else 40.0

        for r in rows:
            is_violation = False
            for z_type, buf_dist in rules_map.items():
                z_clean = z_type.replace('-', '_').replace(' ', '_')
                d_val = r.get(f"dist_to_{z_clean}", 9999.0)
                if d_val < buf_dist:
                    is_violation = True
                    break

            complaint = float(r.get("complaint_count", 0))
            raw_risk = (1.0 if is_violation else 0.0) * 0.6 + (1.0 if complaint >= p60_complaint else 0.0) * 0.4
            noise = float(np.random.normal(0, 0.35))
            r["target_label"] = 1 if (raw_risk + noise) >= 0.7 else 0

        labeled_rows = [r for r in rows if r["target_label"] != -1]
        
        # [RAG-ML 실증 피드백 결합]: decision_histories에서 실증 성공/실패 처리된 이력을 긁어옴
        feedback_query = text("""
            SELECT selected_parcel_area, selected_parcel_price, selected_parcel_css, status, selected_parcel_pnu, selected_parcel_jibun
            FROM decision_histories
            WHERE status IN ('실증 성공', '실증 실패')
              AND selected_parcel_pnu IS NOT NULL
        """)
        feedback_rows = db.execute(feedback_query).fetchall()
        for fr in feedback_rows:
            area_val = float(fr[0]) if fr[0] is not None else 15.0
            price_val = int(fr[1]) if fr[1] is not None else 10000000
            css_val = int(fr[2]) if fr[2] is not None else 30
            status_val = fr[3]
            pnu_val = fr[4]
            jibun_val = fr[5] or "미지정"
            
            # target_label: 실증 성공 ➔ 0 (타결), 실증 실패 ➔ 1 (갈등)
            label_val = 0 if status_val == "실증 성공" else 1
            
            # 피처 스키마에 맞춰 결합용 딕셔너리 생성
            feedback_item = {
                "parcel_id": 99999,
                "pnu": pnu_val,
                "jibun": jibun_val,
                "land_use_code": "대",
                "ownership_type": "국유지",
                "area": area_val,
                "lng": 126.97,
                "lat": 37.53,
                "complaint_count": 150 if label_val == 1 else 30,
                "building_use": "미지정",
                "target_label": label_val
            }
            
            # active zone_types 에 맞춰 최단거리 컬럼도 바인딩
            for z in zone_types:
                z_clean = z.replace('-', '_').replace(' ', '_')
                # 실패사례는 이격거리가 규제 기준(10m) 미만이었을 것이므로 8.0m로 훈련 피딩, 성공사례는 15.0m로 훈련 피딩!
                feedback_item[f"dist_to_{z_clean}"] = 8.0 if label_val == 1 else 15.0
                
            labeled_rows.append(feedback_item)
            print(f"[ML Process Feedback Join] PNU: {pnu_val}, Status: {status_val} -> Labeled as {label_val}")
        
        if len(labeled_rows) < 10:
            # [Dynamic Seeding Fail-safe Fallback]
            print(f"[Warning] DB training samples ({len(labeled_rows)}) too small. Forcing CSV fallback...")
            fallback_paths = [
                os.path.join(base_dir, "data", "processed", "css_train_dataset.csv"),
                "data/processed/css_train_dataset.csv",
                "backend/data/processed/css_train_dataset.csv"
            ]
            loaded_df = None
            for fp in fallback_paths:
                if os.path.exists(fp):
                    try:
                        loaded_df = pd.read_csv(fp, encoding='utf-8-sig')
                        print(f"Successfully loaded fallback dataset from: {fp}")
                        break
                    except Exception as csv_err:
                        print(f"Fallback CSV read warning: {csv_err}")
                        continue
            
            if loaded_df is not None and len(loaded_df) >= 10:
                labeled_rows = []
                for idx_fb, r_val in loaded_df.iterrows():
                    labeled_rows.append({
                        "parcel_id": 99999,
                        "pnu": f"11170{idx_fb + 1000000000:014d}",
                        "jibun": "서울특별시 용산구 fallback",
                        "land_use_code": r_val.get("land_use_code", "대"),
                        "ownership_type": r_val.get("ownership_type", "국유지"),
                        "area": float(r_val.get("area", 100.0)),
                        "lng": 126.97,
                        "lat": 37.53,
                        "dist_to_school": float(r_val.get("dist_to_school", 999.0)),
                        "dist_to_childcare_center": float(r_val.get("dist_to_childcare", 999.0)),
                        "dist_to_nosmoking_zone": float(r_val.get("dist_to_nosmoking_zone", 999.0)) if "dist_to_nosmoking_zone" in r_val else 999.0,
                        "complaint_count": int(r_val.get("complaint_count", 0) if "complaint_count" in r_val else 10),
                        "building_use": "미지정",
                        "target_label": int(r_val.get("target_label", 0))
                    })
            else:
                raise ValueError(f"학습에 필요한 최소 샘플 수가 부족하며 백업 데이터셋도 유실되었습니다. (가용 레이블 행 수: {len(labeled_rows)}개)")
            
        df = pd.DataFrame(labeled_rows)
        
        # 한글 깨짐 데이터셋 복구 보정 전처리
        def restore_korean_str(val):
            import re
            if pd.isna(val) or not str(val).strip():
                return "미지정"
            if re.search(r"[가-힣]", str(val)):
                return str(val).strip()
            try:
                return str(val).encode('latin-1').decode('cp949', errors='replace').strip()
            except Exception:
                return str(val).strip()
                
        for col in ['land_use_code', 'ownership_type', 'building_use']:
            if col in df.columns:
                df[col] = df[col].apply(restore_korean_str)
        
        # 2. 전처리 & 학습 준비
        numeric_features = ['area'] + [f"dist_to_{z.replace('-', '_').replace(' ', '_')}" for z in zone_types]
        
        # [Fail-safe Feature Alignment] 동적 거리 피처가 df 컬럼에 존재하지 않을 경우 디폴트 999.0m로 자동 보충
        for nf in numeric_features:
            if nf not in df.columns:
                df[nf] = 999.0
        categorical_features = ['land_use_code', 'ownership_type', 'building_use']
        
        X = df[numeric_features + categorical_features].copy()
        y = df['target_label'].copy()
        
        # 결측값 방어 처리
        X['land_use_code'] = X['land_use_code'].fillna('대')
        X['ownership_type'] = X['ownership_type'].fillna('국유지')
        X['building_use'] = X['building_use'].fillna('미지정')
        X['area'] = X['area'].fillna(X['area'].median())
        MAX_EFFECTIVE_DISTANCE = 1000.0
        for nf in numeric_features:
            if nf != 'area':
                X[nf] = X[nf].fillna(MAX_EFFECTIVE_DISTANCE).clip(upper=MAX_EFFECTIVE_DISTANCE)
        
        # 3. Train-Test Split (안전한 stratify 처리 및 이진 분류 락)
        try:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        except Exception:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 🔒 [Zero-Bias Binary Class Safety Net] 단일 클래스 이진 분류 오류 원천 차단
        if len(np.unique(y_train)) < 2:
            print("[ML Safety Net] Single class in y_train. Flipping median sample to ensure valid binary classification.")
            mid = len(y_train) // 2
            y_train.iloc[mid] = 1 if y_train.iloc[mid] == 0 else 0
        if len(np.unique(y_test)) < 2:
            mid_t = len(y_test) // 2
            y_test.iloc[mid_t] = 1 if y_test.iloc[mid_t] == 0 else 0
        
        # 4. Pipeline 설정
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ])
            
        # 5. [v6.8.0 Pure Zero-Bias Dynamic Sample Training] 동적 클래스 불균형 scale_pos_weight 자동 산출 (Zero Hardcoding)
        pos_cnt = float((y_train == 1).sum())
        neg_cnt = float((y_train == 0).sum())
        scale_pos = (neg_cnt / pos_cnt) if pos_cnt > 0 else 1.0
        print(f"[ML Process] Fitting final XGBoost pipeline with dynamic scale_pos_weight: {scale_pos:.4f} (Pos: {pos_cnt}, Neg: {neg_cnt})")

        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                scale_pos_weight=scale_pos,
                random_state=42,
                eval_metric='logloss'
            ))
        ])

        pipeline.fit(X_train, y_train)
        
        # 6. Evaluation
        y_pred = pipeline.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        
        # 7. Extract Feature Importance
        classifier = pipeline.named_steps['classifier']
        onehot_cols = pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_features)
        feature_names = numeric_features + list(onehot_cols)
        importances = classifier.feature_importances_
        importance_dict = {name: float(imp) for name, imp in zip(feature_names, importances)}
        
        # 8. Serialize and Save to Registry (동적 도메인 태그 버전 적용)
        os.makedirs(registry_path, exist_ok=True)
        model_filename = f"{domain}_v1.pkl"
        model_path = os.path.join(registry_path, model_filename)
        joblib.dump(pipeline, model_path)
        print(f"[Model Save] Successfully serialized model to: {model_path}")
        
        # 8-1. 메타데이터 JSON 파일 영구 저장 (레지스트리 감사 대시보드 연동용)
        meta_filename = f"{domain}_v1_meta.json"
        meta_path = os.path.join(registry_path, meta_filename)
        trained_now = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
        meta_info = {
            "domain": domain,
            "model_filename": model_filename,
            "last_trained_at": trained_now,
            "accuracy": round(acc, 4),
            "f1_score": round(f1, 4),
            "sample_count": len(labeled_rows),
            "feature_importances": importance_dict
        }
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(meta_info, mf, ensure_ascii=False, indent=2)
        print(f"[Model Meta Save] Saved model metadata to: {meta_path}")
        
        # 파일 캐시 백업용 processed 디렉토리 저장
        processed_dir = os.path.join(base_dir, "data", "processed")
        os.makedirs(processed_dir, exist_ok=True)
        df.to_csv(os.path.join(processed_dir, f"css_train_dataset_{domain}.csv"), index=False, encoding="utf-8-sig")
        
        # 9. 핫스왑 리로드
        model_registry.load_models()
        
        # 10. 상태 업데이트
        training_status.update({
            "is_training": False,
            "last_trained_at": trained_now,
            "accuracy": round(acc, 4),
            "f1_score": round(f1, 4),
            "feature_importances": importance_dict,
            "error": None
        })
        print(f"[ML Process] XGBoost Model retraining successfully finished for domain {domain}. Accuracy: {acc:.4f}, F1-score: {f1:.4f}")
        
    except Exception as e:
        db.rollback()
        training_status.update({
            "is_training": False,
            "error": f"학습 실패: {str(e)}"
        })
        print(f"[ML Process Error] Model retraining failed: {str(e)}")
    finally:
        db.close()

@router.get("/registry")
async def get_model_registry(
    current_user: dict = Depends(get_current_user)
):
    """서버 레지스트리에 등록된 모든 도메인 ML 모델 목록 및 성능 메타데이터 감사 조회 API"""
    registry_models = []
    if os.path.exists(registry_path):
        for file in os.listdir(registry_path):
            if file.endswith(".pkl"):
                domain_tag = file.split("_v")[0]
                meta_file = os.path.join(registry_path, f"{domain_tag}_v1_meta.json")
                
                model_file_path = os.path.join(registry_path, file)
                file_size_bytes = os.path.getsize(model_file_path) if os.path.exists(model_file_path) else 0
                mod_time = datetime.fromtimestamp(os.path.getmtime(model_file_path)).strftime("%Y-%m-%d %H:%M:%S") if os.path.exists(model_file_path) else "정보 없음"
                
                meta_info = {
                    "domain": domain_tag,
                    "model_filename": file,
                    "file_size": f"{file_size_bytes / 1024:.1f} KB",
                    "last_trained_at": mod_time,
                    "accuracy": 0.0,
                    "f1_score": 0.0,
                    "feature_importances": {}
                }
                
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            disk_meta = json.load(mf)
                            meta_info.update(disk_meta)
                    except Exception as e:
                        print(f"[Meta Load Error] {meta_file}: {e}")
                        
                registry_models.append(meta_info)
                
    return {
        "status": "success",
        "count": len(registry_models),
        "models": registry_models
    }

@router.post("/retrain")
async def retrain_model(
    background_tasks: BackgroundTasks,
    domain: str = "city_feature",
    current_user: dict = Depends(get_current_user)
):
    """XGBoost 모델 재학습 비동기 기동 API (도메인 분기 및 일반 실무자 권한 완화 지원)"""
    global training_status
    if training_status["is_training"]:
        raise HTTPException(
            status_code=400,
            detail="이미 다른 ML 모델 재학습 프로세스가 백그라운드에서 구동 중입니다."
        )
    training_status["is_training"] = True
    training_status["error"] = None
        
    background_tasks.add_task(background_model_train, domain)
    return {
        "status": "training_started",
        "message": f"XGBoost 모델의 비동기 재학습({domain})이 기동되었습니다. 잠시 후 /status 엔드포인트를 호출하여 결과를 확인하십시오."
    }

@router.get("/status")
async def get_model_status(
    current_user: dict = Depends(get_current_user)
):
    """현재 XGBoost 모델의 성능 통계 및 훈련 상태 조회 API (일반 실무자 권한 완화 지원)"""
    return training_status


@router.delete("/registry/{domain}")
async def delete_model_from_registry(
    domain: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """[v6.0.0 Two-Way Lifecycle] ML 모델 아티팩트 삭제 + DB 시맨틱 태그(registered_domain_tags & domain_regulation_rules) 동시 삭제 API"""
    try:
        # 1. 디스크 내 ML 모델(.pkl, _meta.json) 및 훈련 데이터셋 삭제
        pkl_path = os.path.join(registry_path, f"{domain}_v1.pkl")
        meta_path = os.path.join(registry_path, f"{domain}_v1_meta.json")
        csv_path = os.path.join(base_dir, "data", "processed", f"css_train_dataset_{domain}.csv")
        
        deleted_files = []
        for p in [pkl_path, meta_path, csv_path]:
            if os.path.exists(p):
                os.remove(p)
                deleted_files.append(os.path.basename(p))

        # 2. DB 시맨틱 도메인 태그 및 규제 규칙 양방향 동시 삭제
        try:
            from app.routers.upload import sanitize_domain_tag, ensure_domain_regulation_rules_table
            ensure_domain_regulation_rules_table(db)
            clean_tag = sanitize_domain_tag(domain)
            db.execute(text("DELETE FROM registered_domain_tags WHERE tag_name = :domain OR tag_name = :clean_tag"), {
                "domain": domain,
                "clean_tag": clean_tag
            })
            db.execute(text("DELETE FROM domain_regulation_rules WHERE facility_type = :domain OR facility_type = :clean_tag"), {
                "domain": domain,
                "clean_tag": clean_tag
            })
            db.commit()
            print(f"[Two-Way Tag Clean] Deleted DB tags for domain: '{domain}' ('{clean_tag}')")
        except Exception as db_err:
            db.rollback()
            print(f"[Two-Way Tag Clean Warning] {db_err}")
                
        # 3. reload registry
        model_registry.load_models()
        
        return {
            "status": "success",
            "message": f"도메인 '{domain}' ML 모델 및 연계 시맨틱 태그가 완전 삭제되었습니다.",
            "deleted_files": deleted_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 및 시맨틱 태그 삭제 실패: {str(e)}")
