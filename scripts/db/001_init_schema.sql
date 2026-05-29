-- P714: SDACS TimescaleDB 초기 스키마
-- 실행 순서: 001_init_schema.sql → 002_retention_policy.sql

-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 드론 원시 텔레메트리 (1초 이하 샘플링)
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time            TIMESTAMPTZ     NOT NULL,
    drone_id        TEXT            NOT NULL,
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    alt_m           REAL            NOT NULL,
    speed_ms        REAL,
    heading_deg     REAL,
    battery_pct     REAL,
    fix_type        SMALLINT,       -- RTKGPSHandler.FixType 값
    scenario_id     TEXT
);

SELECT create_hypertable(
    'drone_telemetry', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_telemetry_drone_time
    ON drone_telemetry (drone_id, time DESC);

-- 충돌 이벤트 (근접 조우·충돌 해결 기록)
CREATE TABLE IF NOT EXISTS conflict_events (
    time            TIMESTAMPTZ     NOT NULL,
    event_id        TEXT            NOT NULL DEFAULT gen_random_uuid()::TEXT,
    drone_a         TEXT            NOT NULL,
    drone_b         TEXT            NOT NULL,
    separation_m    REAL            NOT NULL,
    resolved        BOOLEAN         NOT NULL DEFAULT FALSE,
    resolution_method TEXT,         -- 'APF', 'CBS', 'CPA'
    scenario_id     TEXT
);

SELECT create_hypertable(
    'conflict_events', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 시뮬레이션 실행 메타데이터
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id          TEXT            PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    started_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    scenario_id     TEXT            NOT NULL,
    n_drones        INT             NOT NULL,
    duration_sec    REAL,
    collision_rate  REAL,           -- near-miss rate
    resolution_rate REAL,           -- 충돌 해결률
    config_json     JSONB,
    git_hash        TEXT
);

-- 감사 로그 (JWT 인증 이벤트)
CREATE TABLE IF NOT EXISTS audit_log (
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    user_id         TEXT            NOT NULL,
    action          TEXT            NOT NULL,
    detail          TEXT,
    ip_addr         INET
);

SELECT create_hypertable(
    'audit_log', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 시뮬레이션 실행 ID 인덱스
CREATE INDEX IF NOT EXISTS idx_conflict_run
    ON conflict_events (scenario_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_audit_user
    ON audit_log (user_id, time DESC);
