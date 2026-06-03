-- =============================================================================
-- SDACS P714 — 초기 스키마 마이그레이션
-- PostgreSQL + TimescaleDB 하이퍼테이블 정의
--
-- 실행 방법:
--   psql "$DATABASE_URL" -f db/migrations/001_initial_schema.sql
--
-- 사전 조건:
--   - PostgreSQL 14+ 와 TimescaleDB 2.x 확장 설치
--   - CREATE EXTENSION IF NOT EXISTS timescaledb;
-- =============================================================================

-- TimescaleDB 확장 활성화 (이미 있으면 건너뜀)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =============================================================================
-- 1. drone_telemetry — 드론 원격측정 시계열 테이블
--    각 드론의 위치·상태를 10Hz로 수신하므로 하이퍼테이블로 관리
-- =============================================================================
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time          TIMESTAMPTZ     NOT NULL,
    drone_id      TEXT            NOT NULL,
    lat           DOUBLE PRECISION NOT NULL,   -- 위도 (degrees)
    lon           DOUBLE PRECISION NOT NULL,   -- 경도 (degrees)
    alt           DOUBLE PRECISION NOT NULL,   -- 고도 (meters AGL)
    heading       DOUBLE PRECISION NOT NULL,   -- 방위각 (degrees, 0–360)
    speed         DOUBLE PRECISION NOT NULL,   -- 속도 (m/s)
    battery_pct   SMALLINT        NOT NULL,    -- 배터리 잔량 (0–100)
    status        TEXT            NOT NULL     -- 드론 상태 (flying, hovering, landing, …)
);

-- TimescaleDB 하이퍼테이블 변환 (이미 하이퍼테이블이면 오류 무시)
SELECT create_hypertable(
    'drone_telemetry',
    'time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- 자주 사용되는 쿼리 패턴: 특정 드론의 시간 범위 조회
CREATE INDEX IF NOT EXISTS idx_drone_telemetry_drone_time
    ON drone_telemetry (drone_id, time DESC);

-- 30일 데이터 보존 정책 — 오래된 청크 자동 삭제
SELECT add_retention_policy(
    'drone_telemetry',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- =============================================================================
-- 2. conflict_events — 공역 충돌 이벤트 로그
--    두 드론 간 최소 이격거리 위반 기록 (충돌 해결 여부 포함)
-- =============================================================================
CREATE TABLE IF NOT EXISTS conflict_events (
    id              BIGSERIAL       PRIMARY KEY,
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    drone_a_id      TEXT            NOT NULL,
    drone_b_id      TEXT            NOT NULL,
    separation_m    DOUBLE PRECISION NOT NULL,  -- 감지 시점의 드론 간 거리 (m)
    resolved        BOOLEAN         NOT NULL DEFAULT FALSE,
    resolution_type TEXT                        -- 'avoidance', 'atc_command', NULL=미해결
);

-- 시간 기반 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_conflict_events_time
    ON conflict_events (time DESC);

-- 특정 드론 관련 충돌 이력 조회용
CREATE INDEX IF NOT EXISTS idx_conflict_events_drone_a
    ON conflict_events (drone_a_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_conflict_events_drone_b
    ON conflict_events (drone_b_id, time DESC);

-- =============================================================================
-- 3. mission_log — 임무 이벤트 로그
--    드론별 임무 시작/종료/웨이포인트 도달 등 이벤트를 JSONB payload와 함께 기록
-- =============================================================================
CREATE TABLE IF NOT EXISTS mission_log (
    id          BIGSERIAL       PRIMARY KEY,
    time        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    drone_id    TEXT            NOT NULL,
    mission_id  TEXT            NOT NULL,
    event_type  TEXT            NOT NULL,  -- 'start', 'waypoint_reached', 'complete', 'abort', …
    payload     JSONB                      -- 이벤트별 추가 데이터 (웨이포인트 좌표, 오류 코드 등)
);

-- 임무 ID + 시간 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_mission_log_mission_time
    ON mission_log (mission_id, time DESC);

-- 드론별 최신 임무 이벤트 조회용
CREATE INDEX IF NOT EXISTS idx_mission_log_drone_time
    ON mission_log (drone_id, time DESC);

-- JSONB 필드 전체 텍스트 검색용 (GIN 인덱스)
CREATE INDEX IF NOT EXISTS idx_mission_log_payload_gin
    ON mission_log USING GIN (payload);
