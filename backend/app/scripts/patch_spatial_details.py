import os

FILE_PATH = r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype\backend\app\routers\spatial.py"

def main():
    if not os.path.exists(FILE_PATH):
        print("Error: spatial.py not found.")
        return

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 수동 감리 인서트 쿼리에 match_score, audit_opinion 컬럼 추가
    old_manual_insert = """        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu)
                VALUES (:sim_id, :title, :ocr_text, :scenario, :pnu)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario, "pnu": pnu}
        )"""

    new_manual_insert = """        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu, match_score, audit_opinion)
                VALUES (:sim_id, :title, :ocr_text, :scenario, :pnu, :match_score, :audit_opinion)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario, "pnu": pnu, "match_score": match_score, "audit_opinion": summary}
        )"""

    content = content.replace(old_manual_insert, new_manual_insert)

    # 2. 자동 감리 인서트 쿼리에 match_score, audit_opinion 컬럼 추가
    old_auto_insert = """        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu)
                VALUES (:sim_id, :title, :ocr_text, :scenario, :pnu)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario, "pnu": parsed_pnu}
        )"""

    new_auto_insert = """        db.execute(
            text(\"\"\"
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu, match_score, audit_opinion)
                VALUES (:sim_id, :title, :ocr_text, :scenario, :pnu, :match_score, :audit_opinion)
            \"\"\"),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario, "pnu": parsed_pnu, "match_score": match_score, "audit_opinion": summary}
        )"""

    content = content.replace(old_auto_insert, new_auto_insert)

    # 3. 자가학습 적재 인서트 쿼리에 match_score, audit_opinion 컬럼 추가
    old_register_insert = """        # 1. verified_precedents에 매핑 적재 (외지/외부 실측 사례이므로 conflict_simulation_id는 NULL)
        prec_query = text(\"\"\"
            INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu)
            VALUES (NULL, :title, :ocr_text, :scenario, :pnu)
        \"\"\")
        db.execute(prec_query, {"title": req.filename, "ocr_text": req.textContent[:5000], "scenario": scenario, "pnu": req.pnu})"""

    new_register_insert = """        # 1. verified_precedents에 매핑 적재 (외지/외부 실측 사례이므로 conflict_simulation_id는 NULL)
        prec_query = text(\"\"\"
            INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario, selected_parcel_pnu, match_score, audit_opinion)
            VALUES (NULL, :title, :ocr_text, :scenario, :pnu, :match_score, :audit_opinion)
        \"\"\")
        db.execute(prec_query, {"title": req.filename, "ocr_text": req.textContent[:5000], "scenario": scenario, "pnu": req.pnu, "match_score": match_score, "audit_opinion": summary})"""

    content = content.replace(old_register_insert, new_register_insert)

    # 4. 코사인 유사도 쿼리 결과 콘솔에 프린트하도록 로그 추가
    old_rag_loop = """                rag_rows = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
                for row in rag_rows:
                    matched_regulations.append(f"[{row[0]}] {row[1][:100]}...")"""

    new_rag_loop = """                rag_rows = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
                for row in rag_rows:
                    matched_regulations.append(f"[{row[0]}] {row[1][:100]}...")
                    print(f"[RAG Cosine Match] 조례: {row[0]}, 유사도: {row[2]*100:.2f}%")"""

    content = content.replace(old_rag_loop, new_rag_loop)

    # 5. get_verified_precedents GET API에서 match_score와 audit_opinion 컬럼 가져오고 반환
    old_get_query = """        query = text(\"\"\"
            SELECT id, document_title, document_ocr_text, actual_scenario, TO_CHAR(verified_at, 'YYYY-MM-DD HH24:MI')
            FROM verified_precedents
            ORDER BY id DESC
        \"\"\")"""

    new_get_query = """        query = text(\"\"\"
            SELECT id, document_title, document_ocr_text, actual_scenario, TO_CHAR(verified_at, 'YYYY-MM-DD HH24:MI'), match_score, audit_opinion
            FROM verified_precedents
            ORDER BY id DESC
        \"\"\")"""

    content = content.replace(old_get_query, new_get_query)

    # 리스트 가공 매핑 교체
    old_get_map = """            result.append({
                "id": row[0],
                "title": row[1],
                "pnu": pnu_val,
                "jibun": jibun_val,
                "scenario": row[3],
                "date": row[4],
                "summary": ocr_text[:300] + "..." if len(ocr_text) > 300 else ocr_text
            })"""

    new_get_map = """            result.append({
                "id": row[0],
                "title": row[1],
                "pnu": pnu_val,
                "jibun": jibun_val,
                "scenario": row[3],
                "date": row[4],
                "summary": row[6] if row[6] else (ocr_text[:300] + "..." if len(ocr_text) > 300 else ocr_text),
                "matchScore": row[5] if row[5] is not None else 100
            })"""

    content = content.replace(old_get_map, new_get_map)

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("Success: spatial.py fully upgraded with RAG matchScore and audit_opinion!")

if __name__ == "__main__":
    main()
