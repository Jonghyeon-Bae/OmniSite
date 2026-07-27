"""
OmniSite 3-Party SSE Streaming AI Debate Service (v2.2.0-CodebaseRefactoring)
Manages dynamic persona generation and SSE token streaming for AI debate simulations.
"""
import json
import asyncio
from typing import AsyncGenerator

def generate_debate_prompt(district_name: str, facility_type: str, conflict_level: str) -> str:
    """
    Constructs 3-party debate prompt (Public Official, Resident Rep, Merchant Rep).
    """
    return f"""
[OmniSite AI 모의 심의 토론]
- 입지 지역: {district_name}
- 대상 시설: {facility_type}
- 예상 갈등 강도: {conflict_level}

3인 대립 토론자:
1. 스마트도시과 담당 공무원 (행정/법률 조항 준수 강조)
2. 인근 주민 자치 대표 (NIMBY 우려, 주거 환경 및 담배연기 피해 호소)
3. 골목 상가번영회 대표 (유동인구 유입 및 상권 활성화 기대)

현실감 높은 대립 토론 대화문을 작성하시오.
"""

async def stream_debate_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """
    Simulates SSE streaming tokens for debate modal.
    """
    sample_dialogues = [
        "[공무원] 용산구 금연구역 지정 조례 제3조에 의거하여, 본 후보지는 이격거리 10m 규정을 완벽히 충족합니다.",
        "[주민대표] 아무리 규정을 지켰다고 해도, 아파트 입구와 15m 거리면 담배 연기가 집 안으로 들어옵니다!",
        "[상인대표] 골목 무단 흡연으로 상가 영업 피해가 극심합니다. 차라리 정식 흡연부스를 설치하는 게 맞습니다.",
        "[공무원] 주민과 상인 양측 의견을 수용하여 3D 차단 가림막 및 탈취 장치를 추가 설치하는 안으로 의결하겠습니다."
    ]
    for line in sample_dialogues:
        chunk = {"event": "message", "data": json.dumps({"speaker": line.split("]")[0][1:], "text": line.split("]")[1].strip()})}
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.1)