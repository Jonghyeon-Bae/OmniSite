import os

FILE_PATH = r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype\backend\app\routers\spatial.py"

def main():
    if not os.path.exists(FILE_PATH):
        print(f"Error: {FILE_PATH} not found.")
        return

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 최상단 router 선언부 아래에 analyze_audit_document_via_llm 함수 주입
    router_decl = 'router = APIRouter(prefix="/api/v1", tags=["spatial"])'
    llm_func = """
def analyze_audit_document_via_llm(text_content: str, jibun: str, pnu: str, mock_scenario: Optional[str] = None) -> dict:
    client = get_openai_client()
    if not client:
        return {
            "scenario": "시나리오 해당 없음 (API 키 누락)",
            "match_score": 50,
            "summary": "OpenAI API 연동 실패로 인해 규제 준수 여부를 자동 감리하지 못했습니다."
        }
    
    prompt = f\"\"\"
    당신은 스마트시티 공공 인프라 입지선정 및 감리를 관장하는 행정 공무원 AI 에이전트입니다.
    다음 준공 고시문 PDF 텍스트를 정밀 분석하여, 해당 필지가 규제 조례 요건을 위배하지 않고 무사히 완공되었는지 판독하십시오.

    [대상 필지 정보]
    - 지번 주소: {jibun}
    - 필지 PNU: {pnu}
    - 기존 가상 모의 시나리오: {mock_scenario or '존재하지 않는 외부 사례'}

    [준공 텍스트 본문]
    {text_content[:4000]}

    [판독 지침]
    1. 도달 시나리오 판정:
       - 텍스트 내에서 조례 규정 위반(예: 이격거리 미달, 면적 초과 등)이 전혀 없고 완벽하게 준공되었다면 "시나리오 A (조례 규정 부합 완공)"
       - 일부 규제 저촉 사항이 존재하나 우회 타결 및 조건부 승인되었다면 "시나리오 B (규제 조건부 준수 감리)"
       - 규제를 명백히 위반했거나 검증이 불가능하다면 "시나리오 C (기준 이탈/검증 불허)"
       - 텍스트 내용상 공간 규제 분석이 불가하거나 규제 요건과 전혀 부합하지 않는 무관한 문서라면 "시나리오 해당 없음"
    2. 적합성 신뢰도 (0 ~ 100):
       - 문서의 적합도(%)를 정량 산출하십시오.
    3. 주요 감리 요약 결과:
       - 한글로 3문장 이내로 작성하십시오. 법적 근거와 수치(이격거리 등)를 인용하여 정교하게 작성하십시오.

    반드시 아래 JSON 형식으로만 응답하십시오. 다른 텍스트는 일절 배제하십시오:
    {{
        "scenario": "도달 시나리오 텍스트",
        "match_score": 85,
        "summary": "한글 감리 요약문"
    }}
    \"\"\"
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        import json
        res_json = json.loads(chat_completion.choices[0].message.content)
        return {
            "scenario": res_json.get("scenario", "시나리오 해당 없음"),
            "match_score": int(res_json.get("match_score", 50)),
            "summary": res_json.get("summary", "감리서 작성 실패")
        }
    except Exception as e:
        print(f"[LLM Audit Analysis Fail] {e}")
        return {
            "scenario": "시나리오 해당 없음 (판독 실패)",
            "match_score": 50,
            "summary": f"OpenAI 분석 중 오류가 발생했습니다: {str(e)}"
        }
"""
    if "analyze_audit_document_via_llm" not in content:
        content = content.replace(router_decl, router_decl + "\n" + llm_func)

    # 2. PrecedentRegisterRequest 모델 overwrite 필드 추가
    old_model = """class PrecedentRegisterRequest(BaseModel):
    pnu: Optional[str] = None
    jibun: str
    filename: str
    textContent: str"""
    
    new_model = """class PrecedentRegisterRequest(BaseModel):
    pnu: Optional[str] = None
    jibun: str
    filename: str
    textContent: str
    overwrite: Optional[bool] = False"""
    content = content.replace(old_model, new_model)

    # 3. register_precedent_from_audit API 내 overwrite 삭제 로직 및 LLM 판독 교체
    old_register_logic = """        # 1. verified_precedents에 매핑 적재 (외지/외부 실측 사례이므로 conflict_simulation_id는 NULL)
        prec_query = text(\"\"\"
            INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario)
            VALUES (NULL, :title, :ocr_text, '시나리오 A (정당 규정 완전 부합 준공)')
        \"\"\")
        db.execute(prec_query, {"title": req.filename, "ocr_text": req.textContent[:5000]})"""

    new_register_logic = """        # 중복 업로드 Overwrite 분기 처리
        if req.overwrite and req.pnu:
            db.execute(text("DELETE FROM verified_precedents WHERE selected_parcel_pnu = :pnu"), {"pnu": req.pnu})
            
        # LLM 지능형 한글 감리 판독 가동 (하드코딩 배제)
        llm_res = analyze_audit_document_via_llm(req.textContent, req.jibun, req.pnu or "PNU 모름")
        scenario = llm_res["scenario"]
        
        # 1. verified_precedents에 매핑 적재 (외지/외부 실측 사례이므로 conflict_simulation_id는 NULL)
        prec_query = text(\"\"\"
            INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu)
            VALUES (NULL, :title, :ocr_text, :scenario, :pnu)
        \"\"\")
        db.execute(prec_query, {"title": req.filename, "ocr_text": req.textContent[:5000], "scenario": scenario, "pnu": req.pnu})"""
        
    content = content.replace(old_register_logic, new_register_logic)

    # 4. audit_history_document (수동 업로드) LLM 통합 및 pnu SELECT 추가
    old_manual_audit = """        history_query = text("SELECT region, facility_type, infra, ahp_weights, selected_parcel_jibun, selected_parcel_css FROM decision_histories WHERE id = :id")
        history_row = db.execute(history_query, {"id": history_id}).fetchone()
        if not history_row:
            raise HTTPException(status_code=404, detail="지정된 심의 이력을 찾을 수 없습니다.")
            
        region, facility_type, infra, ahp_weights_raw, jibun, css = history_row
        ahp_weights = json.loads(ahp_weights_raw) if isinstance(ahp_weights_raw, str) else (ahp_weights_raw or {})
        
        client = get_openai_client()
        matched_regulations = []
        if client:
            try:
                query_str = f"{infra} {jibun} 설치 공시 준공 고시 조례"
                embed_res = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query_str
                )
                query_embedding = embed_res.data[0].embedding
                
                rag_query = text(\"\"\"
                    SELECT regulation_title, content, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                    FROM district_regulations
                    WHERE 1 - (embedding <=> CAST(:query_embedding AS vector)) >= 0.35
                    ORDER BY similarity DESC
                    LIMIT 3
                \"\"\")
                rag_rows = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
                for row in rag_rows:
                    matched_regulations.append(f"[{row[0]}] {row[1][:100]}...")
            except Exception as e:
                print(f"[RAG Error during history audit] {e}")
                
        match_score = 90.0
        
        if jibun and jibun.replace(" ", "") not in text_content.replace(" ", ""):
            addr_tokens = [t for t in re.sub(r'[^가-힣0-9]', ' ', jibun).split() if len(t) >= 2]
            matched_tokens = [t for t in addr_tokens if t in text_content]
            if len(matched_tokens) < len(addr_tokens) * 0.5:
                match_score -= 25.0
                
        for forbid in ["위반", "침범", "규제저촉", "이격미달"]:
            if forbid in text_content:
                match_score -= 10.0
                
        for kw in ["유동인구", "민원", "무단투기", "생활인구", "청소년"]:
            if kw in text_content:
                match_score += 2.0
                
        match_score = max(10.0, min(100.0, match_score))
        
        if match_score >= 80.0:
            scenario = "시나리오 A (정당 규정 완전 부합 준공)"
            audit_state = "검증 완료"
            summary = f"본 준공 공시 문서는 스마트 입지 의사결정의 선정지({jibun}) 정보와 RAG 조례 이격 가이드라인을 {match_score:.0f}% 수준으로 신뢰성 있게 준수하며 최종 행정 검증이 확인되었습니다."
        elif match_score >= 50.0:
            scenario = "시나리오 B (규제 조건부 준수 감리)"
            audit_state = "검증 완료"
            summary = f"준공 내용 상에서 일부분 안전 이격 요건의 보완 검토 항목이 발견되었으나, 시나리오 가중합 기준치를 {match_score:.0f}% 수준으로 방어 우회하여 조건부 타결 승인을 획득하였습니다."
        else:
            scenario = "시나리오 C (기준 이탈/검증 불허)"
            audit_state = "불가능"
            summary = f"입지 지번({jibun}) 또는 시설 이격 규정(RAG 기준치)에 대한 위배 사유가 확인되어, 공문 일치도 {match_score:.0f}% 미달로 인해 행정 검증 승인이 반려되었습니다."
 
        db.execute(
            text("UPDATE decision_histories SET audit_state = :state, audit_opinion = :opinion WHERE id = :id"),
            {"state": audit_state, "opinion": summary, "id": history_id}
        )
        
        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario)
                VALUES (:sim_id, :title, :ocr_text, :scenario)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario}
        )"""

    new_manual_audit = """        history_query = text("SELECT region, facility_type, infra, ahp_weights, selected_parcel_jibun, selected_parcel_css, selected_parcel_pnu FROM decision_histories WHERE id = :id")
        history_row = db.execute(history_query, {"id": history_id}).fetchone()
        if not history_row:
            raise HTTPException(status_code=404, detail="지정된 심의 이력을 찾을 수 없습니다.")
            
        region, facility_type, infra, ahp_weights_raw, jibun, css, pnu = history_row
        ahp_weights = json.loads(ahp_weights_raw) if isinstance(ahp_weights_raw, str) else (ahp_weights_raw or {})
        
        client = get_openai_client()
        matched_regulations = []
        if client:
            try:
                query_str = f"{infra} {jibun} 설치 공시 준공 고시 조례"
                embed_res = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query_str
                )
                query_embedding = embed_res.data[0].embedding
                
                rag_query = text(\"\"\"
                    SELECT regulation_title, content, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                    FROM district_regulations
                    WHERE 1 - (embedding <=> CAST(:query_embedding AS vector)) >= 0.35
                    ORDER BY similarity DESC
                    LIMIT 3
                \"\"\")
                rag_rows = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
                for row in rag_rows:
                    matched_regulations.append(f"[{row[0]}] {row[1][:100]}...")
            except Exception as e:
                print(f"[RAG Error during history audit] {e}")
                
        # LLM 지능형 한글 감리 판독 가동 (하드코딩 배제)
        llm_res = analyze_audit_document_via_llm(text_content, jibun or "지번 모름", pnu or "PNU 모름", mock_scenario=f"이격 {css}m 요건")
        scenario = llm_res["scenario"]
        match_score = llm_res["match_score"]
        summary = llm_res["summary"]
        audit_state = "검증 완료" if "A" in scenario or "B" in scenario else "불가능"

        db.execute(
            text("UPDATE decision_histories SET audit_state = :state, audit_opinion = :opinion WHERE id = :id"),
            {"state": audit_state, "opinion": summary, "id": history_id}
        )
        
        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu)
                VALUES (:sim_id, :title, :ocr_text, :scenario, :pnu)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario, "pnu": pnu}
        )"""

    content = content.replace(old_manual_audit, new_manual_audit)

    # 5. audit_history_document_auto (자동 매칭 업로드) 중복 필지 감지 기능 분기 처리 및 LLM 감리 교체
    old_auto_audit = """        # 1. 19자리 PNU 규격 추출 (\\d{19})
        pnu_match = re.search(r"(\\d{19})", text_content)
        parsed_pnu = pnu_match.group(1) if pnu_match else None
        
        # 2. 지번 정보 간접 추출 (예: 서빙고동 235-1)
        jibun_match = re.search(r"([가-힣]+동\\s*\\d+(?:-\\d+)?)", text_content)
        parsed_jibun = jibun_match.group(1) if jibun_match else "알 수 없는 지번"
        
        history_row = None
        if parsed_pnu:
            # PNU로 먼저 매칭 조회
            history_query = text("SELECT id, region, facility_type, infra, ahp_weights, selected_parcel_jibun, selected_parcel_css FROM decision_histories WHERE selected_parcel_pnu = :pnu LIMIT 1")
            history_row = db.execute(history_query, {"pnu": parsed_pnu}).fetchone()"""

    new_auto_audit = """        # 1. 19자리 PNU 규격 추출 (\\d{19})
        pnu_match = re.search(r"(\\d{19})", text_content)
        parsed_pnu = pnu_match.group(1) if pnu_match else None
        
        # 2. 지번 정보 간접 추출 (예: 서빙고동 235-1)
        jibun_match = re.search(r"([가-힣]+동\\s*\\d+(?:-\\d+)?)", text_content)
        parsed_jibun = jibun_match.group(1) if jibun_match else "알 수 없는 지번"

        # PNU 중복 업로드 감지 및 Overwrite 컨펌 분기 반환
        if parsed_pnu:
            exist_query = text("SELECT id, document_title FROM verified_precedents WHERE selected_parcel_pnu = :pnu LIMIT 1")
            exist_row = db.execute(exist_query, {"pnu": parsed_pnu}).fetchone()
            if exist_row:
                return {
                    "status": "already_exists",
                    "pnu": parsed_pnu,
                    "jibun": parsed_jibun,
                    "filename": filename,
                    "textContent": text_content,
                    "existing_title": exist_row[1],
                    "message": f"이미 실증 사례가 등록된 필지(PNU: {parsed_pnu})입니다. 기존 검증사례({exist_row[1]})를 덮어쓰시겠습니까?"
                }
        
        history_row = None
        if parsed_pnu:
            # PNU로 먼저 매칭 조회
            history_query = text("SELECT id, region, facility_type, infra, ahp_weights, selected_parcel_jibun, selected_parcel_css FROM decision_histories WHERE selected_parcel_pnu = :pnu LIMIT 1")
            history_row = db.execute(history_query, {"pnu": parsed_pnu}).fetchone()"""

    content = content.replace(old_auto_audit, new_auto_audit)

    # 6. audit_history_document_auto (자동 매칭 성공 시) 기존 하드코딩 판별을 LLM 한글 판독으로 대체
    old_auto_calc = """        match_score = 90.0
        
        if jibun and jibun.replace(" ", "") not in text_content.replace(" ", ""):
            addr_tokens = [t for t in re.sub(r'[^가-힣0-9]', ' ', jibun).split() if len(t) >= 2]
            matched_tokens = [t for t in addr_tokens if t in text_content]
            if len(matched_tokens) < len(addr_tokens) * 0.5:
                match_score -= 25.0
                
        for forbid in ["위반", "침범", "규제저촉", "이격미달"]:
            if forbid in text_content:
                match_score -= 10.0
                
        for kw in ["유동인구", "민원", "무단투기", "생활인구", "청소년"]:
            if kw in text_content:
                match_score += 2.0
                
        match_score = max(10.0, min(100.0, match_score))
        
        if match_score >= 80.0:
            scenario = "시나리오 A (정당 규정 완전 부합 준공)"
            audit_state = "검증 완료"
            summary = f"본 준공 공시 문서는 스마트 입지 의사결정의 선정지({jibun}) 정보와 RAG 조례 이격 가이드라인을 {match_score:.0f}% 수준으로 신뢰성 있게 준수하며 최종 행정 검증이 확인되었습니다."
        elif match_score >= 50.0:
            scenario = "시나리오 B (규제 조건부 준수 감리)"
            audit_state = "검증 완료"
            summary = f"준공 내용 상에서 일부분 안전 이격 요건의 보완 검토 항목이 발견되었으나, 시나리오 가중합 기준치를 {match_score:.0f}% 수준으로 방어 우회하여 조건부 타결 승인을 획득하였습니다."
        else:
            scenario = "시나리오 C (기준 이탈/검증 불허)"
            audit_state = "불가능"
            summary = f"입지 지번({jibun}) 또는 시설 이격 규정(RAG 기준치)에 대한 위배 사유가 확인되어, 공문 일치도 {match_score:.0f}% 미달로 인해 행정 검증 승인이 반려되었습니다."

        db.execute(
            text("UPDATE decision_histories SET audit_state = :state, audit_opinion = :opinion WHERE id = :id"),
            {"state": audit_state, "opinion": summary, "id": history_id}
        )
        
        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario)
                VALUES (:sim_id, :title, :ocr_text, :scenario)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario}
        )"""

    new_auto_calc = """        # LLM 지능형 한글 감리 판독 가동 (하드코딩 배제)
        llm_res = analyze_audit_document_via_llm(text_content, jibun or "지번 모름", parsed_pnu or "PNU 모름", mock_scenario=f"이격 {css}m 요건")
        scenario = llm_res["scenario"]
        match_score = llm_res["match_score"]
        summary = llm_res["summary"]
        audit_state = "검증 완료" if "A" in scenario or "B" in scenario else "불가능"

        db.execute(
            text("UPDATE decision_histories SET audit_state = :state, audit_opinion = :opinion WHERE id = :id"),
            {"state": audit_state, "opinion": summary, "id": history_id}
        )
        
        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu)
                VALUES (:sim_id, :title, :ocr_text, :scenario, :pnu)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario, "pnu": parsed_pnu}
        )"""

    content = content.replace(old_auto_calc, new_auto_calc)

    # 7. DELETE API 2개 추가 (맨 끝에 붙음)
    delete_endpoints = """
# ========================================================
# [Delete Endpoints for Dashboard Record Management]
# ========================================================
@router.delete("/spatial/history/{history_id}")
async def delete_decision_history(history_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM decision_histories WHERE id = :id"), {"id": history_id})
        db.commit()
        return {"status": "success", "message": f"모의 심의 이력 #{history_id} 가 삭제되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"이력 삭제 실패: {str(e)}")

@router.delete("/spatial/precedents/{precedent_id}")
async def delete_verified_precedent(precedent_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM verified_precedents WHERE id = :id"), {"id": precedent_id})
        db.commit()
        return {"status": "success", "message": f"실증 준공 사례 #{precedent_id} 가 삭제되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"실증사례 삭제 실패: {str(e)}")
"""
    if "delete_decision_history" not in content:
        content += delete_endpoints

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("Success: spatial.py fully patched!")

if __name__ == "__main__":
    main()
