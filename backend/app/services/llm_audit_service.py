"""
LLM RAG Audit Service for OmniSite
"""
from typing import List, Optional
from app.routers.upload import get_openai_client

def analyze_audit_document_via_llm(
    text_content: str, 
    jibun: str, 
    pnu: str, 
    mock_scenario: Optional[str] = None, 
    matched_regulations: Optional[List[str]] = None
) -> dict:
    """
    RAG 코사인 유사도와 OpenAI LLM을 사용하여 준공 고시문 PDF 텍스트를 감리 판독하는 지능형 서비스
    """
    client = get_openai_client()
    if not client:
        return {
            "scenario": "시나리오 해당 없음 (API 키 누락)",
            "match_score": 50,
            "summary": "OpenAI API 연동 실패로 인해 규제 준수 여부를 자동 감리하지 못했습니다."
        }
    
    matched_regulations_str = "\n".join(matched_regulations) if matched_regulations else "매칭된 조례 조항 없음"
    prompt = f"""
    당신은 스마트시티 공공 인프라 입지선정 및 감리를 관장하는 행정 공무원 AI 에이전트입니다.
    다음 준공 고시문 PDF 텍스트를 정밀 분석하여, 해당 필지가 규제 조례 요건을 위배하지 않고 무사히 완공되었는지 판독하십시오.

    [대상 필지 정보]
    - 지번 주소: {jibun}
    - 필지 PNU: {pnu}
    - 기존 가상 모의 시나리오: {mock_scenario or '존재하지 않는 외부 사례'}

    [RAG 코사인 유사도 기반 매칭 조례 조항]
    {matched_regulations_str}

    [준공 텍스트 본문]
    {text_content[:4000]}

    [판독 지침]
    1. 도달 시나리오 판정:
       - 텍스트 내에서 조례 규정 위반(예: 이격거리 미달, 면적 초과 등)이 전혀 없고 완벽하게 준공되었다면 "시나리오 A (조례 규정 부합 완공)"
       - 일부 규제 저촉 사항이 존재하나 우회 타결 및 조건부 승인되었다면 "시나리오 B (규제 조건부 준수 감리)"
       - 규제를 명백히 위반했거나 검증이 불가능하다면 "시나리오 C (기준 이탈/검증 불허)"
       - 텍스트 내용상 공간 규제 분석이 불가하거나 규제 요건과 전혀 부합하지 않는 무관한 문서라면 "시나리오 해당 없음"
    2. 적합성 신뢰도 match_score (0 ~ 100):
       - 시나리오 A (부합 완공): 90 ~ 100점 산출.
       - 시나리오 B (조건부 준수): 60 ~ 75점 산출.
       - 시나리오 C (기준 이탈/검증 불허/위반): 규제 저촉 상태이므로 10 ~ 40점 이하의 낮은 부합도 점수를 산출하십시오. (절대로 100점을 부여하지 마십시오)
    3. 주요 감리 요약 결과:
       - 한글로 3문장 이내로 작성하십시오. 법적 근거와 수치(이격거리 등)를 인용하여 정교하게 작성하십시오.

    반드시 아래 JSON 형식으로만 응답하십시오. 다른 텍스트는 일절 배제하십시오:
    {{
        "scenario": "도달 시나리오 텍스트",
        "match_score": 30,
        "summary": "한글 감리 요약문"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional urban infrastructure audit AI agent. Output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        import json
        res_json = json.loads(response.choices[0].message.content)
        return {
            "scenario": res_json.get("scenario", "시나리오 해당 없음"),
            "match_score": int(res_json.get("match_score", 50)),
            "summary": res_json.get("summary", "감리 판독 요약문 생성 완료.")
        }
    except Exception as e:
        return {
            "scenario": "시나리오 해당 없음 (LLM 처리 오류)",
            "match_score": 40,
            "summary": f"LLM 판독 중 예외가 발발하여 자동 감리를 완공하지 못했습니다: {str(e)}"
        }
