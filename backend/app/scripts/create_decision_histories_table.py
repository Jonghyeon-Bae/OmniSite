import os
import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"

def main():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("[Migration] Dropping decision_histories if exists...")
        conn.execute(text("DROP TABLE IF EXISTS decision_histories CASCADE;"))
        
        print("[Migration] Creating table decision_histories...")
        conn.execute(text("""
            CREATE TABLE decision_histories (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                region VARCHAR(250) NOT NULL,
                facility_type VARCHAR(50) NOT NULL,
                infra VARCHAR(100) NOT NULL,
                pnu_count INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(50) NOT NULL,
                audit_state VARCHAR(50) NOT NULL,
                audit_opinion TEXT,
                inferred_purpose VARCHAR(250),
                ahp_weights JSONB,
                selected_parcel_jibun VARCHAR(250),
                selected_parcel_price BIGINT,
                selected_parcel_area NUMERIC,
                selected_parcel_css INTEGER,
                debate_logs JSONB
            );
        """))
        
        # 가상 과거 이력 4개 시드 데이터 적재
        print("[Migration] Seeding initial mock data into decision_histories...")
        
        seed_data = [
            {
                "id": 101,
                "region": "서울시 서대문구 신촌동",
                "facility_type": "city_feature",
                "infra": "다목적 방범 스마트부스",
                "pnu_count": 3,
                "status": "행정 종결",
                "audit_state": "검증 완료",
                "audit_opinion": "부스 내부 CCTV 가용 범위 및 소방도로 통행 요건 준수 확인.",
                "inferred_purpose": "다목적 방범 스마트부스 설치",
                "ahp_weights": {"traffic": 5.0, "complaint": 5.0, "density": 5.0},
                "selected_parcel_jibun": "신촌동 12-4",
                "selected_parcel_price": 12000000,
                "selected_parcel_area": 14.5,
                "selected_parcel_css": 32,
                "debate_logs": [
                    {"sender": "반대측", "text": "스마트부스가 야간 청소년 비행 장소로 오용될까 우려스럽습니다."},
                    {"sender": "찬성측", "text": "오히려 지능형 안심 벨과 연동된 스마트 부스로 우범 골목을 안심 지대로 격상시킬 수 있습니다."},
                    {"sender": "정부측", "text": "보안 연동 모니터링을 관할 지구대와 실시간 바인딩 처리하는 설계 조건 하에 최종 허가합니다."}
                ]
            },
            {
                "id": 102,
                "region": "서울시 용산구 이태원동",
                "facility_type": "ev_charging",
                "infra": "전기차 화재방지 충전소",
                "pnu_count": 2,
                "status": "심의 중",
                "audit_state": "불가능",
                "audit_opinion": "소방시설 이격거리 기준 미달로 인해 행정 반려 판정.",
                "inferred_purpose": "전기차 화재방지 충전소 설치",
                "ahp_weights": {"ev_density": 6.0, "grid_capacity": 4.0, "park_distance": 5.0},
                "selected_parcel_jibun": "이태원동 45-12",
                "selected_parcel_price": 9800000,
                "selected_parcel_area": 12.0,
                "selected_parcel_css": 82,
                "debate_logs": [
                    {"sender": "반대측", "text": "지상 변전실 인근 충전소 발화 시 불길이 인근 다세대 주택가로 번질 수 있는 리스크가 매우 다분합니다."},
                    {"sender": "찬성측", "text": "질식 소화포와 전기차용 소화전을 시유지 한계선에 함께 설계하여 선제 방어막을 갖출 것입니다."},
                    {"sender": "정부측", "text": "소방 용수 거리가 안전 기준 미달이므로 차선지 이관 또는 보행 가용폭 증설 보정을 권장합니다."}
                ]
            },
            {
                "id": 103,
                "region": "서울시 마포구 공덕동",
                "facility_type": "yellow_carpet",
                "infra": "옐로카펫 보행 정화지",
                "pnu_count": 1,
                "status": "행정 종결",
                "audit_state": "대기 중",
                "audit_opinion": "옐로카펫 횡단 신호대 보도 가시성 확보 검증 대기 상태.",
                "inferred_purpose": "어린이 보행안전 옐로카펫 구역 매핑",
                "ahp_weights": {"school_zone": 5.0, "traffic_volume": 5.0, "speed_violations": 5.0},
                "selected_parcel_jibun": "공덕동 2-14",
                "selected_parcel_price": 18500000,
                "selected_parcel_area": 18.0,
                "selected_parcel_css": 45,
                "debate_logs": [
                    {"sender": "반대측", "text": "옐로우 반사 시트가 보도폭 진입 사각에서 회전 차량들의 시야 방해를 초래하지는 않을지 걱정입니다."},
                    {"sender": "찬성측", "text": "스쿨존 보행 어린이들의 반사 시인성이 2배 이상 확보되므로 우회전 사고를 대폭 저하할 수 있습니다."},
                    {"sender": "정부측", "text": "보행 안전 패널 외곽에 반사 반경 미러를 조율 설치하는 중재 사양으로 최종 통과 처리합니다."}
                ]
            },
            {
                "id": 104,
                "region": "서울시 용산구 한강로동",
                "facility_type": "smoking_zone",
                "infra": "스마트 쉼터형 부스",
                "pnu_count": 3,
                "status": "행정 종결",
                "audit_state": "검증 완료",
                "audit_opinion": "버스정류소 및 어린이집 이격거리 제한 규정(200m/50m) 완전 우회 확인.",
                "inferred_purpose": "실외 흡연구역 입지 선정",
                "ahp_weights": {"traffic": 7.2, "complaint": 6.8, "dumping": 4.5, "population": 3.8, "youth": 1.2},
                "selected_parcel_jibun": "한강로동 42-12",
                "selected_parcel_price": 14200000,
                "selected_parcel_area": 15.0,
                "selected_parcel_css": 78,
                "debate_logs": [
                    {"sender": "반대측", "text": "부스 설치 예정 필지 인근의 좁은 인도 폭 때문에 보행 통로가 협소해져 통학 어린이들의 충돌 우려 등 보행 안전이 매우 우려됩니다."},
                    {"sender": "찬성측", "text": "상가 앞 길거리 간접 흡연 및 무분별한 꽁초 투기를 전용 스마트 부스로 유도 수용하여 미관 및 보행 환경이 훨씬 개선됩니다."},
                    {"sender": "정부측", "text": "보행 유효 통행 폭 3.0m를 확보하고, 정화 공조 필터 등급 사양을 강화하여 안전성 우려를 최소화하는 조건으로 최종 통과시킵니다."}
                ]
            }
        ]
        
        for item in seed_data:
            conn.execute(text("""
                INSERT INTO decision_histories (id, region, facility_type, infra, pnu_count, status, audit_state, audit_opinion, inferred_purpose, ahp_weights, selected_parcel_jibun, selected_parcel_price, selected_parcel_area, selected_parcel_css, debate_logs)
                VALUES (:id, :region, :facility_type, :infra, :pnu_count, :status, :audit_state, :audit_opinion, :inferred_purpose, :ahp_weights, :selected_parcel_jibun, :selected_parcel_price, :selected_parcel_area, :selected_parcel_css, :debate_logs);
            """), {
                "id": item["id"],
                "region": item["region"],
                "facility_type": item["facility_type"],
                "infra": item["infra"],
                "pnu_count": item["pnu_count"],
                "status": item["status"],
                "audit_state": item["audit_state"],
                "audit_opinion": item["audit_opinion"],
                "inferred_purpose": item["inferred_purpose"],
                "ahp_weights": json.dumps(item["ahp_weights"]),
                "selected_parcel_jibun": item["selected_parcel_jibun"],
                "selected_parcel_price": item["selected_parcel_price"],
                "selected_parcel_area": item["selected_parcel_area"],
                "selected_parcel_css": item["selected_parcel_css"],
                "debate_logs": json.dumps(item["debate_logs"])
            })
            
        conn.commit()
        print("[Migration] Migration completed successfully!")

if __name__ == "__main__":
    main()
