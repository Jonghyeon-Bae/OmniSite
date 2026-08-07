# -*- coding: utf-8 -*-
import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, f1_score
from xgboost import XGBClassifier
import joblib
from sqlalchemy import create_engine, text

print("=== [PHASE 1: STARTING AWS DYNAMIC CSS ML MODEL TRAINING] ===")

# 경로 설정 (로컬 / 도커 컨테이너 환경 호환 지원)
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# app/scripts -> app -> backend
backend_base = os.path.dirname(os.path.dirname(current_script_dir))

# sys.path에 backend 디렉토리 추가하여 app 모듈 임포트 확보
if backend_base not in sys.path:
    sys.path.append(backend_base)
if os.path.dirname(backend_base) not in sys.path:
    sys.path.append(os.path.dirname(backend_base))

try:
    from app.config import settings
    DATABASE_URL = settings.DATABASE_URL
    print(f"DATABASE_URL successfully resolved from config: {DATABASE_URL[:25]}...")
except Exception as e:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres")
    print(f"Fallback to environment or default DATABASE_URL: {DATABASE_URL[:25]}... (Error: {e})")

# 모델 및 백업 데이터셋 경로 구성
model_dir = os.path.join(backend_base, "app", "models", "registry")
if not os.path.exists(model_dir):
    os.makedirs(model_dir)
model_path = os.path.join(model_dir, "smoking_zone_v1.pkl")

backup_dataset_path = os.path.join(backend_base, "data", "processed", "css_train_dataset.csv")

# 1. Load Data from PostgreSQL Database
df = None
use_fallback = False

try:
    print("Attempting to query real-time spatial parcel features from database...")
    engine = create_engine(DATABASE_URL)
    
    # [Column Existence Guard] 컬럼 존재 여부 체크
    check_cols_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='cadastral_lands' AND column_name IN ('dist_to_school_m', 'dist_to_childcare_m');
    """
    with engine.connect() as conn:
        existing_cols = [r[0] for r in conn.execute(text(check_cols_query)).fetchall()]
        
    if len(existing_cols) == 2:
        print("Optimized distance columns exist. Executing fast query...")
        query = """
            SELECT land_use_code, ownership_type, 
                   ST_Area(geom::geography) AS area,
                   COALESCE(dist_to_school_m, 9999.0) AS dist_to_school,
                   COALESCE(dist_to_childcare_m, 9999.0) AS dist_to_childcare
            FROM cadastral_lands;
        """
    else:
        print("Optimized distance columns missing. Executing real-time spatial joins (This may take a few seconds)...")
        query = """
            SELECT c.land_use_code, c.ownership_type, 
                   ST_Area(c.geom::geography) AS area,
                   COALESCE((
                       SELECT ST_Distance(c.geom::geography, r.geom::geography)
                       FROM restricted_zones r
                       WHERE r.zone_type = 'school'
                       ORDER BY c.geom <-> r.geom
                       LIMIT 1
                   ), 9999.0) AS dist_to_school,
                   COALESCE((
                       SELECT ST_Distance(c.geom::geography, r.geom::geography)
                       FROM restricted_zones r
                       WHERE r.zone_type = 'childcare'
                       ORDER BY c.geom <-> r.geom
                       LIMIT 1
                   ), 9999.0) AS dist_to_childcare
            FROM cadastral_lands c;
        """
        
    df_db = pd.read_sql(query, con=engine)
    
    if len(df_db) < 50:
        print(f"Warning: Database parcel count ({len(df_db)}) is too small. Falling back to static CSV.")
        use_fallback = True
    else:
        print(f"Successfully loaded {len(df_db)} records from database.")
        
        # [Closed-Loop Dynamic Labeling] 
        # 실시간 DB 필지의 속성 및 거리 규제를 활용한 정답 타겟 레이블 생성 규칙 정의
        # 규칙: 학교/어린이집 경계 200m 밖(정화구역 탈출)이면서, 가용 지목(대, 잡, 주)이고 국공유지인 곳은 적합(1), 아니면 부적합(0)
        df_db['target_label'] = (
            (df_db['dist_to_school'] >= 200.0) & 
            (df_db['dist_to_childcare'] >= 200.0) & 
            (df_db['ownership_type'].isin(['국유지', '시유지', '구유지'])) & 
            (df_db['land_use_code'].isin(['대', '잡', '주', '체']))
        ).astype(int)
        
        # [Class Balancing] 국공유지 적격지는 전체 필지 대비 극소수이므로 Down-sampling을 통해 학습 균형 유지
        df_pos = df_db[df_db['target_label'] == 1]
        df_neg = df_db[df_db['target_label'] == 0]
        
        print(f"Class distribution - Eligible (1): {len(df_pos)}, Ineligible (0): {len(df_neg)}")
        
        if len(df_pos) < 10:
            print(f"Warning: Eligible positive samples ({len(df_pos)}) is too small. Forcing fallback to static CSV.")
            use_fallback = True
        elif len(df_neg) > len(df_pos):
            # 1:1.5 비율로 다운샘플링하여 훈련 세트 밸런싱
            sample_size = min(len(df_neg), int(len(df_pos) * 1.5))
            df_neg_sampled = df_neg.sample(n=sample_size, random_state=42)
            df = pd.concat([df_pos, df_neg_sampled]).sample(frac=1, random_state=42).reset_index(drop=True)
            print(f"Balanced Dataset size: {len(df)} (Pos: {len(df_pos)}, Neg: {len(df_neg_sampled)})")
        else:
            df = df_db.copy()
            
except Exception as db_err:
    print(f"Database query failed: {db_err}")
    print("Falling back to static local CSV dataset...")
    use_fallback = True

# Fallback: 로컬 백업 CSV 로딩
if use_fallback or df is None:
    if os.path.exists(backup_dataset_path):
        print(f"Loading fallback dataset from: {backup_dataset_path}")
        df = pd.read_csv(backup_dataset_path, encoding='utf-8-sig')
    else:
        # 2차 비상 폴백
        alt_backup_path = "backend/data/processed/css_train_dataset.csv"
        if os.path.exists(alt_backup_path):
            print(f"Loading alternative fallback dataset from: {alt_backup_path}")
            df = pd.read_csv(alt_backup_path, encoding='utf-8-sig')
        else:
            print("CRITICAL ERROR: No training dataset available (DB empty & CSV missing).")
            sys.exit(1)

# 2. Preprocessing & Feature Engineering
X = df[['land_use_code', 'ownership_type', 'area', 'dist_to_school', 'dist_to_childcare']].copy()
y = df['target_label'].copy()

# Fill missing/NaN values defensively
MAX_EFFECTIVE_DISTANCE = 1000.0
X['land_use_code'] = X['land_use_code'].fillna('대')
X['ownership_type'] = X['ownership_type'].fillna('국유지')
X['area'] = X['area'].fillna(X['area'].median())
X['dist_to_school'] = X['dist_to_school'].fillna(MAX_EFFECTIVE_DISTANCE).clip(upper=MAX_EFFECTIVE_DISTANCE)
X['dist_to_childcare'] = X['dist_to_childcare'].fillna(MAX_EFFECTIVE_DISTANCE).clip(upper=MAX_EFFECTIVE_DISTANCE)

# 3. Train-Test Split (80% Train, 20% Test)
try:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
except Exception as split_err:
    print(f"Warning: Stratified split failed ({split_err}). Falling back to non-stratified split...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

# 4. Define Preprocessing Pipeline
numeric_features = ['area', 'dist_to_school', 'dist_to_childcare']
numeric_transformer = Pipeline(steps=[
    ('scaler', StandardScaler())
])

categorical_features = ['land_use_code', 'ownership_type']
categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ])

# 5. Define XGBoost Classifier Model inside Pipeline
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', XGBClassifier(
        n_estimators=80,
        max_depth=3,
        learning_rate=0.08,
        reg_lambda=10.0,
        reg_alpha=2.0,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    ))
])

# 6. Evaluate with 5-Fold Cross Validation
print("Running 5-Fold Cross Validation...")
try:
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='f1')
    print(f"CV F1-Scores: {cv_scores}")
    print(f"Mean CV F1-Score: {np.mean(cv_scores):.4f}")
except Exception as cv_err:
    print(f"Cross Validation warning (likely too few positive samples in DB subset): {cv_err}")

# 7. Fit final model on whole Training Set
print("Fitting final XGBoost pipeline model...")
pipeline.fit(X_train, y_train)

# 8. Evaluate on Test Set
y_pred = pipeline.predict(X_test)
test_accuracy = accuracy_score(y_test, y_pred)
test_f1 = f1_score(y_test, y_pred)
print(f"\n=== TEST SET EVALUATION ===")
print(f"Accuracy: {test_accuracy:.4f}")
print(f"F1-Score: {test_f1:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 9. Extract Feature Importance
try:
    classifier = pipeline.named_steps['classifier']
    onehot_cols = pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_features)
    feature_names = numeric_features + list(onehot_cols)
    importances = classifier.feature_importances_

    print("\n=== XGBOOST FEATURE IMPORTANCE ===")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
        print(f"Feature: {name:<25} Importance: {imp:.4f}")
except Exception as feat_err:
    print(f"Could not extract feature importances: {feat_err}")

# 10. Serialize & Save Pipeline
print(f"\nSerializing and saving pipeline model to: {model_path}")
joblib.dump(pipeline, model_path)
print("SUCCESS: Dynamic Model registration completed.")
