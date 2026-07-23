import os
import sys
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Add backend to sys.path for database & imports
sys.path.append("backend")
from app.database import engine

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report
from xgboost import XGBClassifier

def audit_ml_model():
    print("========================================================")
    print(" [ML Audit Engine] Overfitting & Generalization Analysis")
    print("========================================================")
    
    with engine.connect() as conn:
        # 1. Check ownership_type distribution in cadastral_lands
        ownership_dist = conn.execute(text("SELECT ownership_type, COUNT(*) FROM cadastral_lands GROUP BY ownership_type")).fetchall()
        print("\n[1] Cadastral Lands Ownership Distribution in DB:")
        for o, cnt in ownership_dist:
            print(f"  - {o}: {cnt} records")
            
        # 2. Check active zone_types
        zone_types_res = conn.execute(text("SELECT DISTINCT zone_type FROM restricted_zones")).fetchall()
        zone_types = [r[0] for r in zone_types_res if r[0]]
        if not zone_types:
            zone_types = ['school', 'childcare_center']
            
        # 3. Query dataset used for training
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
                    WHERE c.district_id = 1
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
                c.land_use_code,
                c.ownership_type,
                ST_Area(c.geom::geography) AS area,
                {select_sql},
                COALESCE(cc.complaint_count, 0) AS complaint_count,
                COALESCE(b.main_use_name, '미지정') AS building_use,
                CASE 
                    WHEN COALESCE(cc.complaint_count, 0) >= 120 THEN 1
                    WHEN COALESCE(cc.complaint_count, 0) <= 95 THEN 0
                    ELSE -1
                END AS target_label
            FROM cadastral_lands c
            {join_sql}
            LEFT JOIN civil_complaints cc ON c.dong_id = cc.dong_id
            LEFT JOIN building_ledgers b ON c.pnu = b.pnu
            WHERE c.district_id = 1
              AND ST_IsValid(c.geom);
        """)
        
        result = conn.execute(query)
        headers = list(result.keys())
        rows = [dict(zip(headers, r)) for r in result]
        
        print(f"\n[2] Total Queried Cadastral Records: {len(rows)}")
        
        labeled_rows = [r for r in rows if r["target_label"] != -1]
        print(f"    Labeled Training Rows (target_label != -1): {len(labeled_rows)}")
        
        if len(labeled_rows) < 10:
            print("❌ Insufficient labeled samples for training.")
            return

        df = pd.DataFrame(labeled_rows)
        
        print("\n[3] Target Class Distribution:")
        print(df['target_label'].value_counts(normalize=True).to_dict())
        
        numeric_features = ['area'] + [f"dist_to_{z.replace('-', '_').replace(' ', '_')}" for z in zone_types]
        categorical_features = ['land_use_code', 'ownership_type', 'building_use']
        
        X = df[numeric_features + categorical_features].copy()
        y = df['target_label'].copy()
        
        X['land_use_code'] = X['land_use_code'].fillna('대')
        X['ownership_type'] = X['ownership_type'].fillna('국유지')
        X['building_use'] = X['building_use'].fillna('미지정')
        X['area'] = X['area'].fillna(X['area'].median())
        for nf in numeric_features:
            if nf != 'area':
                X[nf] = X[nf].fillna(9999.0)
                
        # Split Train / Test (80% / 20%)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
            ]
        )
        
        model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='logloss'
            ))
        ])
        
        model.fit(X_train, y_train)
        
        # Train Predictions vs Test Predictions
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)
        
        train_acc = accuracy_score(y_train, y_train_pred)
        test_acc = accuracy_score(y_test, y_test_pred)
        
        train_f1 = f1_score(y_train, y_train_pred)
        test_f1 = f1_score(y_test, y_test_pred)
        
        y_test_proba = model.predict_proba(X_test)[:, 1]
        auc_score = roc_auc_score(y_test, y_test_proba)
        
        print("\n[4] Training Performance Metrics:")
        print(f"  - Train Accuracy : {train_acc:.4f} ({train_acc*100:.2f}%)")
        print(f"  - Test Accuracy  : {test_acc:.4f} ({test_acc*100:.2f}%)")
        print(f"  - Accuracy Gap   : {abs(train_acc - test_acc):.4f} (Overfitting indicator)")
        print(f"  - Train F1-Score : {train_f1:.4f}")
        print(f"  - Test F1-Score  : {test_f1:.4f}")
        print(f"  - ROC-AUC Score  : {auc_score:.4f}")
        
        # 5-Fold Cross Validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
        cv_f1_scores = cross_val_score(model, X, y, cv=cv, scoring='f1')
        
        print("\n[5] 5-Fold Cross Validation Scores:")
        print(f"  - CV Accuracy Mean: {cv_scores.mean():.4f} (Std: {cv_scores.std():.4f})")
        print(f"  - CV F1-Score Mean: {cv_f1_scores.mean():.4f} (Std: {cv_f1_scores.std():.4f})")
        
        # Feature Importances
        clf = model.named_steps['classifier']
        prep = model.named_steps['preprocessor']
        cat_cols = prep.named_transformers_['cat'].get_feature_names_out(categorical_features)
        all_features = list(numeric_features) + list(cat_cols)
        importances = clf.feature_importances_
        
        imp_df = pd.DataFrame({'feature': all_features, 'importance': importances})
        imp_df = imp_df.sort_values(by='importance', ascending=False)
        
        print("\n[6] Top 5 Feature Importances:")
        for _, r in imp_df.head(5).iterrows():
            print(f"  - {r['feature']}: {r['importance']:.4f}")

if __name__ == "__main__":
    audit_ml_model()
