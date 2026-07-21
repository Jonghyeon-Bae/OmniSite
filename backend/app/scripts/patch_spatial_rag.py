import os

FILE_PATH = r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype\backend\app\routers\spatial.py"

def main():
    if not os.path.exists(FILE_PATH):
        print("Error: spatial.py not found.")
        return

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. analyze_audit_document_via_llm 함수 매개변수 및 프롬프트에 matched_regulations 추가
    old_llm_def = """def analyze_audit_document_via_llm(text_content: str, jibun: str, pnu: str, mock_scenario: Optional[str] = None) -> dict:
    client = get_openai_client()"""

    new_llm_def = """def analyze_audit_document_via_llm(text_content: str, jibun: str, pnu: str, mock_scenario: Optional[str] = None, matched_regulations: Optional[List[str]] = None) -> dict:
    client = get_openai_client()"""

    content = content.replace(old_llm_def, new_llm_def)

    # 프롬프트 내부 조례 매칭 컨텍스트 바인딩
    old_prompt_bind = """    [대상 필지 정보]
    - 지번 주소: {jibun}
    - 필지 PNU: {pnu}
    - 기존 가상 모의 시나리오: {mock_scenario or '존재하지 않는 외부 사례'}

    [준공 텍스트 본문]
    {text_content[:4000]}"""

    new_prompt_bind = """    [대상 필지 정보]
    - 지번 주소: {jibun}
    - 필지 PNU: {pnu}
    - 기존 가상 모의 시나리오: {mock_scenario or '존재하지 않는 외부 사례'}

    [RAG 코사인 유사도 기반 매칭 조례 조항]
    {matched_regulations_str}

    [준공 텍스트 본문]
    {text_content[:4000]}"""

    content = content.replace(old_prompt_bind, new_prompt_bind)

    # prompt f-string 안의 matched_regulations_str 변수 처리 주입
    old_prompt_call = """    prompt = f\"\"\""""
    new_prompt_call = """    regulations_ctx = "\\n".join(matched_regulations) if matched_regulations else "매칭된 조례 조항 없음"
    prompt = f\"\"\""""
    # matched_regulations_str을 채워주기 위해 variables 바인딩 영역 추가
    
    # regulations_ctx 정의 부분을 함수 상단에 꼽습니다.
    # prompt = f""" 바로 위에 regulations_ctx를 삽입
    content = content.replace("    prompt = f\"\"\"", '    matched_regulations_str = "\\n".join(matched_regulations) if matched_regulations else "매칭된 조례 조항 없음"\n    prompt = f\"\"\"')

    # 2. audit_history_document (수동 업로드) API 호출 시 matched_regulations 전달
    old_manual_call = """        # LLM 지능형 한글 감리 판독 가동 (하드코딩 배제)
        llm_res = analyze_audit_document_via_llm(text_content, jibun or "지번 모름", pnu or "PNU 모름", mock_scenario=f"이격 {css}m 요건")"""

    new_manual_call = """        # LLM 지능형 한글 감리 판독 가동 (RAG 코사인 유사도 조례 매칭 컨텍스트 주입)
        llm_res = analyze_audit_document_via_llm(text_content, jibun or "지번 모름", pnu or "PNU 모름", mock_scenario=f"이격 {css}m 요건", matched_regulations=matched_regulations)"""

    content = content.replace(old_manual_call, new_manual_call)

    # 3. audit_history_document_auto (자동 매칭) API 호출 시 matched_regulations 전달
    old_auto_call = """        # LLM 지능형 한글 감리 판독 가동 (하드코딩 배제)
        llm_res = analyze_audit_document_via_llm(text_content, jibun or "지번 모름", parsed_pnu or "PNU 모름", mock_scenario=f"이격 {css}m 요건")"""

    new_auto_call = """        # LLM 지능형 한글 감리 판독 가동 (RAG 코사인 유사도 조례 매칭 컨텍스트 주입)
        llm_res = analyze_audit_document_via_llm(text_content, jibun or "지번 모름", parsed_pnu or "PNU 모름", mock_scenario=f"이격 {css}m 요건", matched_regulations=matched_regulations)"""

    content = content.replace(old_auto_call, new_auto_call)

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("Success: RAG Cosine Similarity context integrated into LLM Audit Analyzer!")

if __name__ == "__main__":
    main()
