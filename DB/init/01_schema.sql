-- Extensions 활성화
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 자치구역 마스터 테이블
CREATE TABLE districts (
    id SERIAL PRIMARY KEY,
    district_name VARCHAR(100) NOT NULL,
    sig_cd VARCHAR(5) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 서울시 행정구역 (동별) 공간정보 테이블
CREATE TABLE dong_boundaries (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_code VARCHAR(10) UNIQUE NOT NULL,
    dong_name VARCHAR(100) NOT NULL,
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_dong_geom ON dong_boundaries USING GIST(geom);

-- 3. 범용 스마트시티 제한/규제구역 테이블 (nosmoking_zones 일반화 리팩토링)
CREATE TABLE restricted_zones (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    zone_name VARCHAR(150),
    address VARCHAR(250),
    geom GEOMETRY(Point, 4326) NOT NULL,
    zone_type VARCHAR(50) NOT NULL DEFAULT 'nosmoking_zone',
    area NUMERIC,
    registered_at DATE
);
CREATE INDEX idx_restricted_geom ON restricted_zones USING GIST(geom);

-- 4. 서울 어린이집/학교 정보 테이블
CREATE TABLE childcare_centers (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    center_name VARCHAR(150) NOT NULL,
    center_type VARCHAR(50),
    address VARCHAR(250),
    geom GEOMETRY(Point, 4326) NOT NULL,
    student_count INT
);
CREATE INDEX idx_childcare_geom ON childcare_centers USING GIST(geom);

-- 5. 버스/지하철 역사 마스터 위치 테이블
CREATE TABLE transit_stations (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    station_no VARCHAR(50) UNIQUE NOT NULL,
    station_name VARCHAR(150) NOT NULL,
    transit_type VARCHAR(10) NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX idx_transit_geom ON transit_stations USING GIST(geom);

-- 6. 대중교통 이용객 통계 정보 테이블
CREATE TABLE transit_passengers (
    id SERIAL PRIMARY KEY,
    station_id INT REFERENCES transit_stations(id) ON DELETE CASCADE,
    analysis_ym VARCHAR(6) NOT NULL,
    boarding_count INT DEFAULT 0,
    alighting_count INT DEFAULT 0,
    total_volume INT DEFAULT 0
);

-- 7. 행정동단위 서울 생활인구 통계 테이블
CREATE TABLE population_stats (
    id SERIAL PRIMARY KEY,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE CASCADE,
    day_type VARCHAR(10) NOT NULL,
    time_type VARCHAR(10) NOT NULL,
    avg_population NUMERIC NOT NULL
);

-- 8. 소상공인 상가상권 정보 테이블
CREATE TABLE commercial_shops (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    shop_name VARCHAR(150) NOT NULL,
    category_code VARCHAR(10),
    category_name VARCHAR(50),
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX idx_shop_geom ON commercial_shops USING GIST(geom);

-- 9. 자치구 불법흡연 민원 통계 테이블
CREATE TABLE civil_complaints (
    id SERIAL PRIMARY KEY,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE CASCADE,
    complaint_count INT NOT NULL,
    analysis_year VARCHAR(4) NOT NULL
);

-- 10. 국토교통부 연속지적도 테이블
CREATE TABLE cadastral_lands (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    pnu VARCHAR(19) NOT NULL,
    jibun VARCHAR(100),
    land_use_code VARCHAR(5),
    ownership_type VARCHAR(10),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_cadastral_geom ON cadastral_lands USING GIST(geom);

-- 11. 전국휴지통데이터 테이블
CREATE TABLE trash_bins (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    bin_name VARCHAR(150),
    geom GEOMETRY(Point, 4326) NOT NULL,
    bin_type VARCHAR(50)
);
CREATE INDEX idx_trash_geom ON trash_bins USING GIST(geom);

-- 12. 주민등록인구 연령별 동별 통계 테이블
CREATE TABLE age_demographics (
    id SERIAL PRIMARY KEY,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE CASCADE,
    youth_population INT NOT NULL,
    total_population INT NOT NULL,
    youth_ratio NUMERIC NOT NULL
);

-- 13. 범용 상습무단투기구역 테이블 (cigarette_dumping_zones 일반화 리팩토링)
CREATE TABLE illegal_dumping_zones (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    address VARCHAR(250),
    detail_location TEXT,
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX idx_illegal_dumping_geom ON illegal_dumping_zones USING GIST(geom);

-- 14. AHP 가중치 프로파일 마스터 테이블
CREATE TABLE ahp_models (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    facility_type VARCHAR(50) NOT NULL DEFAULT 'smoking_zone',
    criteria_weights JSONB NOT NULL,
    consistency_ratio NUMERIC NOT NULL,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. 시뮬레이션 결과 리포트 캐시 테이블
CREATE TABLE conflict_simulations (
    id SERIAL PRIMARY KEY,
    cadastral_land_id INT REFERENCES cadastral_lands(id) ON DELETE CASCADE,
    facility_type VARCHAR(50) NOT NULL DEFAULT 'smoking_zone',
    css_score NUMERIC NOT NULL,
    css_vector JSONB NOT NULL,
    normal_scenario TEXT,
    optimal_scenario TEXT,
    worst_scenario TEXT,
    confidence_score NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. 실제 이행 사례 기록 테이블
CREATE TABLE verified_precedents (
    id SERIAL PRIMARY KEY,
    conflict_simulation_id INT REFERENCES conflict_simulations(id) ON DELETE SET NULL,
    document_title VARCHAR(250),
    document_ocr_text TEXT,
    actual_scenario VARCHAR(50) NOT NULL,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. 자치구별 조례 RAG 임베딩 테이블
CREATE TABLE district_regulations (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    regulation_title VARCHAR(250) NOT NULL,
    clause_number VARCHAR(50),
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'health_sanitation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_regulations_district_category_vector ON district_regulations (district_id, category) INCLUDE (embedding);

-- 17-2. 시맨틱 도메인 태그 중복 방지/병합용 메타 테이블
CREATE TABLE registered_domain_tags (
    id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) UNIQUE,
    tag_description TEXT,
    embedding VECTOR(1536)
);

-- 18. 범용 스마트시티 공간 시설물 테이블 (가/감점 요인 통합 관리용)
CREATE TABLE city_spatial_features (
    id SERIAL PRIMARY KEY,
    district_id INT REFERENCES districts(id) ON DELETE CASCADE,
    dong_id INT REFERENCES dong_boundaries(id) ON DELETE SET NULL,
    feature_type VARCHAR(50) NOT NULL, -- 'cctv', 'ev_charger', 'streetlight', 'trash_bin' 등
    feature_name VARCHAR(150),
    geom GEOMETRY(Point, 4326) NOT NULL,
    properties JSONB,                  -- 개별 시설물별 특수 데이터 유연 적재 (예: {"power_kw": 50})
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_city_features_geom ON city_spatial_features USING GIST(geom);
CREATE INDEX idx_city_features_type ON city_spatial_features (feature_type);

