# -*- coding: utf-8 -*-
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def get_font_name():
    font_path = "C:\\Windows\\Fonts\\malgun.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("Malgun", font_path))
        return "Malgun"
    return "Helvetica"

def build_pdf(filename, title_text, lines):
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pdf_path = os.path.join(root_dir, filename)
    
    font_name = get_font_name()
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Title
    c.setFont(font_name, 18)
    c.drawCentredString(width / 2.0, height - 80, title_text)
    
    # Subtitle
    c.setFont(font_name, 10)
    c.drawCentredString(width / 2.0, height - 110, "[서울특별시 용산구 고시 제2026-88호]")
    
    c.setLineWidth(1)
    c.line(50, height - 130, width - 50, height - 130)
    
    c.setFont(font_name, 10)
    y = height - 160
    
    for line in lines:
        c.drawString(60, y, line)
        y -= 22
        
    c.showPage()
    c.save()
    print(f"[Success] PDF generated: {pdf_path}")

def main():
    # 1. 성공 시나리오 PDF
    success_lines = [
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
    build_pdf("yongsan_completion_success_pnu11.pdf", "스마트시티 공공인프라 설치 준공 고시문 [성공사례]", success_lines)

    # 2. 실패 시나리오 PDF
    fail_lines = [
        "1. 사업의 명칭: 용산구 스마트시티 다목적 인프라(스마트 흡연부스) 설치 사업 준공",
        "2. 사업 시행자: 서울특별시 용산구청장 (스마트도시기획과)",
        "3. 준공 대상지 주소 및 필지 고유번호:",
        "   - 지번 주소: 서울특별시 용산구 서빙고동 235-1 (대지)",
        "   - 필지고유번호 (PNU): 1117012500102350001",
        "4. 행정 입지 조례 이격거리 규격 검사 결과서:",
        "   - [조례 기준]: 금연/보호법령에 의거 어린이집 및 학교 경계선으로부터 최소 10m 이상 이격 필수.",
        "   - [실측 이행거리]:",
        "     * 인근 서빙고 어린이집 경계선으로부터 실제 이격거리: 8.3m (이격미달)",
        "     * 인접 서빙고 초등학교 경계선으로부터 실제 이격거리: 9.1m (규제저촉 위반)",
        "     * 금연구역 조례 저촉 여부: 있음 (어린이집/학교 이격거리 미준수 위반 저촉)",
        "5. 설치 제원 규격:",
        "   - 총 부지 사용 면적: 24.5 ㎡ (조례상 제한 규격 20.0 ㎡ 초과 위반)",
        "   - 부스 형태: 개방형 3면 차단 에어커튼 흡연 공간",
        "6. 준공 검사 의견:",
        "   본 필지는 실측 검사 결과 아동 보호 이격 규정(10m 최소 안전거리)을 충족하지 못하였으며,",
        "   어린이집과 초등학교 정화구역을 직접 침범한 위반 사실이 확인되었습니다. 또한 설치 면적이",
        "   조례 기준을 초과하여 행정 지침을 위반하였으므로 최종 감리 검증을 불허하며 승인을 반려합니다.",
        "",
        "공고일자: 2026년 7월 21일",
        "서울특별시 용산구청장 (직인생략)"
    ]
    build_pdf("yongsan_completion_fail_pnu11.pdf", "스마트시티 공공인프라 설치 준공 고시문 [실패사례]", fail_lines)

    # 3. 애매한 조건부 시나리오 PDF
    conditional_lines = [
        "1. 사업의 명칭: 용산구 스마트시티 다목적 인프라(스마트 흡연부스) 설치 사업 준공",
        "2. 사업 시행자: 서울특별시 용산구청장 (스마트도시기획과)",
        "3. 준공 대상지 주소 및 필지 고유번호:",
        "   - 지번 주소: 서울특별시 용산구 서빙고동 235-1 (대지)",
        "   - 필지고유번호 (PNU): 1117012500102350001",
        "4. 행정 입지 조례 이격거리 규격 검사 결과서:",
        "   - [조례 기준]: 금연/보호법령에 의거 어린이집 및 학교 경계선으로부터 최소 10m 이상 이격 필수.",
        "   - [실측 이행거리]:",
        "     * 인근 서빙고 어린이집 경계선으로부터 실제 이격거리: 9.8m (보완 검토 필요)",
        "     * 인접 서빙고 초등학교 경계선으로부터 실제 이격거리: 10.1m (간신히 충족)",
        "     * 금연구역 조례 저촉 여부: 애매함 (오차 범위 내 보완 협의 조서 추가 제출 요망)",
        "5. 설치 제원 규격:",
        "   - 총 부지 사용 면적: 19.9 ㎡ (조례상 제한 규격 20.0 ㎡ 임계 충족)",
        "   - 부스 형태: 개방형 3면 차단 에어커튼 흡연 공간",
        "6. 준공 검사 의견:",
        "   실측 이격거리 9.8m로 조례 기준인 10m에 거의 육박하여 미세한 오차가 있으나,",
        "   에어커튼 집진 장치를 강화하는 방향의 보완 협의 및 안전 보완 대책을 조서로 첨부하여",
        "   기준치에 합치시키는 조율안을 채택, 조건부로 실증 준공을 승인하여 타결 처리합니다.",
        "",
        "공고일자: 2026년 7월 21일",
        "서울특별시 용산구청장 (직인생략)"
    ]
    build_pdf("yongsan_completion_conditional_pnu11.pdf", "스마트시티 공공인프라 설치 준공 고시문 [조건부사례]", conditional_lines)

if __name__ == "__main__":
    main()
