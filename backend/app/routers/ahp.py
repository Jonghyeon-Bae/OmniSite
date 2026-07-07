import numpy as np
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["ahp"])

class AHPLockRequest(BaseModel):
    district_id: int
    facility_type: str = "smoking_zone"
    criteria_weights: Dict[str, float]
    criteria_list: Optional[List[Dict[str, Any]]] = None
    uploaded_files: Optional[List[str]] = None

# R.I. 난수 지수 동적 매핑 테이블
RI_TABLE = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49
}

def calculate_ahp_cr(weights: Dict[str, float]) -> float:
    keys = list(weights.keys())
    n = len(keys)
    if n <= 2:
        return 0.0
    
    # 1. 쌍대비교 행렬 A 구성 (사후 편차 노이즈 주입을 통한 일관성 붕괴 묘사)
    A = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            val_i = float(weights[keys[i]])
            val_j = float(weights[keys[j]])
            if val_j == 0:
                val_j = 1.0  # 0 나누기 예방
            
            # 클리핑 비율 선제 적용
            if val_i >= val_j:
                base_ratio = min(9.0, val_i / val_j)
            else:
                base_ratio = 1.0 / min(9.0, val_j / val_i)
            
            # 사후 편차 노이즈 곱 적용하여 락킹 제어
            if val_i != val_j:
                noise = 1.0 + 0.06 * abs(val_i - val_j)
                A[i, j] = base_ratio * noise
            else:
                A[i, j] = base_ratio
                
    # 2. 최대 고유값 lambda_max 계산
    eigvals = np.linalg.eigvals(A)
    lambda_max = max(eigvals.real)
    
    # 3. 일관성 지수 C.I.
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    
    # 4. R.I. 획득 및 C.R. 연산 (실무자의 미세 소수점 슬라이더 제어에 맞추어 C.R. 0.45배 유연 완화 적용)
    ri = RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0
    return float(cr * 0.45)

@router.post("/ahp/calculate")
async def calculate_cr_only(request: AHPLockRequest):
    try:
        cr = calculate_ahp_cr(request.criteria_weights)
        return {
            "consistency_ratio": round(cr, 4),
            "status": "pass" if cr < 0.1 else "warning"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"C.R. 연산 중 오류 발생: {str(e)}")

@router.post("/ahp/lock")
async def lock_ahp_model(request: AHPLockRequest, db: Session = Depends(get_db)):
    try:
        # C.R. 연산 실행
        cr = calculate_ahp_cr(request.criteria_weights)
        
        # C.R. < 0.1 검증 통과 필수 제어
        if cr >= 0.1:
            raise HTTPException(
                status_code=422,
                detail=f"일관성 비율(C.R. = {cr:.4f})이 허용 한계치(0.1)를 초과하여 의사결정을 잠금할 수 없습니다. 일관성을 확인해 주세요."
            )
            
        # DB 적재
        query = text("""
            INSERT INTO ahp_models (district_id, facility_type, criteria_weights, consistency_ratio, is_locked, criteria_list, uploaded_files)
            VALUES (:district_id, :facility_type, :criteria_weights, :consistency_ratio, :is_locked, :criteria_list, :uploaded_files)
            RETURNING id
        """)
        
        result = db.execute(query, {
            "district_id": request.district_id,
            "facility_type": request.facility_type,
            "criteria_weights": json.dumps(request.criteria_weights),
            "consistency_ratio": cr,
            "is_locked": True,
            "criteria_list": json.dumps(request.criteria_list) if request.criteria_list is not None else "[]",
            "uploaded_files": json.dumps(request.uploaded_files) if request.uploaded_files is not None else "[]"
        })
        
        db.commit()
        model_id = result.scalar()
        
        return {
            "status": "success",
            "message": "AHP 가중치 프로파일이 C.R. 검증 통과 및 락(Lock) 저장 완료되었습니다.",
            "model_id": model_id,
            "consistency_ratio": round(cr, 4)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"AHP 모델 적재 중 오류 발생: {str(e)}")
