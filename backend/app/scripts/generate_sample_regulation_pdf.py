# -*- coding: utf-8 -*-
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_sample_pdf():
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "yongsan_smart_infra_completion_notice_sample.pdf")
    
    # 윈도우 시스템 한글 폰트 등록 (Malgun Gothic)
    font_path = "C:\\Windows\\Fonts\\malgun.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("Malgun", font_path))
        font_name = "Malgun"
    else:
        # Fallback to Helvetica if font doesn't exist
        font_name = "Helvetica"
        print("[Warning] Malgun Gothic font not found. Falling back to Helvetica.")

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Title
    c.setFont(font_name, 20)
    c.drawCentredString(width / 2.0, height - 80, "스마트시티 공공인프라 설치 준공 고시문")
    
    # Subtitle
    c.setFont(font_name, 11)
    c.drawCentredString(width / 2.0, height - 110, "[서울특별시 용산구 고시 제2026-88호]")
    
    # Line divider
    c.setLineWidth(1)
    c.line(50, height - 130, width - 50, height - 130)
    
    # Content body
    c.setFont(font_name, 11)
    y = height - 170
    
    lines = [
        "1. 사업의 명칭: 용산구 스마트시티 다목적 인프라(스마트 흡연부스) 설치 사업 준공",
        "2. 사업 시행자: 서울특별시 용산구청장 (스마트도시기획과)",
        "3. 준공 대상지 주소 및 필지 고유번호:",
        "   - 지번 주소: 서울특별시 용산구 서빙고동 235-1 (대지)",
        "   - 필지고유번호 (PNU): 1117012500102350001",
        "4. 행정 입지 조례 이격거리 규격 검사 결과서:",
        "   - [조례 기준]: 금연/보호법령에 의거 어린이집 및 학교 경계선으로부터 최소 10m 이상 이격 필수.",
        "   - [실측 이행거리]:",
        "     * 인근 서빙고 어린이집 경계선으로부터 실제 이격거리: 15.2m (적합)",
        "     * 인접 서빙고 초등학교 경계선으로부터 실제 이격거리: 22.8m (적합)",
        "     * 금연구역 조례 저촉 여부: 없음 (이격거리 10m 이상 완전 확보 준수)",
        "5. 설치 제원 규격:",
        "   - 총 부지 사용 면적: 18.5 ㎡ (조례상 제한 규격 20.0 ㎡ 이하 충족)",
        "   - 부스 형태: 개방형 3면 차단 에어커튼 흡연 공간",
        "6. 준공 검사 의견:",
        "   본 준공 대상 필지는 최초 의사결정 계층분석(AHP) 단계에서 가결 승인된 입지 가중 요건을",
        "   충족하고 있으며, 조례상 명시된 아동/청소년 보호구역 10m 이격거리를 완벽하게 준수하여",
        "   이상 없이 완공되었음을 검사조서에 따라 최종 고시합니다.",
        "",
        "공고일자: 2026년 7월 21일",
        "서울특별시 용산구청장 (직인생략)"
    ]
    
    for line in lines:
        c.drawString(60, y, line)
        y -= 25  # Line spacing
        
    c.showPage()
    c.save()
    print(f"[Success] Sample PDF created at: {pdf_path}")

if __name__ == "__main__":
    create_sample_pdf()
