# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, f1_score
from xgboost import XGBClassifier
import joblib

print("=== [PHASE 1: STARTING CSS ML MODEL TRAINING] ===")

# 로컬 실행과 도커 환경 실행 모두를 유연하게 방어하기 위한 지능형 경로 리졸버
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# app/scripts -> app -> backend
backend_base = os.path.dirname(os.path.dirname(current_script_dir))

if os.path.exists(os.path.join(backend_base, "data", "processed", "css_train_dataset.csv")):
    dataset_path = os.path.join(backend_base, "data", "processed", "css_train_dataset.csv")
    model_dir = os.path.join(backend_base, "app", "models", "registry")
else:
    # 로컬 작업 디렉토리 기준 폴백 지원
    dataset_path = "backend/data/processed/css_train_dataset.csv"
    model_dir = "backend/app/models/registry"

if not os.path.exists(model_dir):
    os.makedirs(model_dir)
    print(f"Created model registry folder: {model_dir}")

model_path = os.path.join(model_dir, "smoking_zone_v1.pkl")

if not os.path.exists(dataset_path):
    print(f"Error: Dataset not found at {dataset_path}")
    exit(1)

# 1. Load Dataset
print(f"Loading training dataset: {dataset_path}")
df = pd.read_sql = pd.read_csv(dataset_path)

# Drop redundant identifiers
X = df[['land_use_code', 'ownership_type', 'area', 'dist_to_school', 'dist_to_childcare']].copy()
y = df['target_label'].copy()

# Fill missing/NaN values defensively (거리 캡핑 1,000.0m 임계값 적용으로 StandardScaler 왜곡 완치)
MAX_EFFECTIVE_DISTANCE = 1000.0
X['land_use_code'] = X['land_use_code'].fillna('대')
X['ownership_type'] = X['ownership_type'].fillna('국유지')
X['area'] = X['area'].fillna(X['area'].median())
X['dist_to_school'] = X['dist_to_school'].fillna(MAX_EFFECTIVE_DISTANCE).clip(upper=MAX_EFFECTIVE_DISTANCE)
X['dist_to_childcare'] = X['dist_to_childcare'].fillna(MAX_EFFECTIVE_DISTANCE).clip(upper=MAX_EFFECTIVE_DISTANCE)

# 2. Train-Test Split (80% Train, 20% Test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

# 3. Define Preprocessing Pipeline
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

# 4. Define XGBoost Classifier Model inside Pipeline
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

# 5. Evaluate with 5-Fold Cross Validation
print("Running 5-Fold Cross Validation...")
cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='f1')
print(f"CV F1-Scores: {cv_scores}")
print(f"Mean CV F1-Score: {np.mean(cv_scores):.4f}")

# 6. Fit final model on whole Training Set
print("Fitting final XGBoost pipeline model...")
pipeline.fit(X_train, y_train)

# 7. Evaluate on Test Set
y_pred = pipeline.predict(X_test)
test_accuracy = accuracy_score(y_test, y_pred)
test_f1 = f1_score(y_test, y_pred)
print(f"\n=== TEST SET EVALUATION ===")
print(f"Accuracy: {test_accuracy:.4f}")
print(f"F1-Score: {test_f1:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 8. Extract Feature Importance
classifier = pipeline.named_steps['classifier']
onehot_cols = pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_features)
feature_names = numeric_features + list(onehot_cols)
importances = classifier.feature_importances_

print("\n=== XGBOOST FEATURE IMPORTANCE ===")
for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
    print(f"Feature: {name:<25} Importance: {imp:.4f}")

# 9. Serialize & Save Pipeline
print(f"\nSerializing and saving pipeline model to: {model_path}")
joblib.dump(pipeline, model_path)
print("SUCCESS: Model registration completed.")
