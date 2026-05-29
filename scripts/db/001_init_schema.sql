-- SDACS TimescaleDB 초기 스키마 (P714)
-- 30일 보존 정책 포함
-- 실행: psql -U sdacs sdacs -f 001_init_schema.sql

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 드론 위치 텔레메트리 (고주파 시계열)
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time        TIMESTAMPTZ     NOT NULL,
    drone_id    TEXT            NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    alt_m       REAL            NOT NULL,
    vx          REAL            NOT NULL,
    vy          REAL            NOT NULL,
    vz          REAL            NOT NULL,
    heading_deg REAL,
    battery_pct REAL,
    run_id      UUID,
    scenario    TEXT
);

SELECT create_hypertable(
    'drone_telemetry', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- 충돌 / 근접 이벤트
CREATE TABLE IF NOT EXISTS conflict_events (
    time        TIMESTAMPTZ     NOT NULL,
    run_id      UUID            NOT NULL,
    drone_a     TEXT            NOT NULL,
    drone_b     TEXT            NOT NULL,
    cpa_dist_m  REAL            NOT NULL,
    cpa_time_s  REAL,
    resolved    BOOLEAN         NOT NULL DEFAULT FALSE,
    method      TEXT,           -- CBS / APF / ORCA / VO
    scenario    TEXT
);

SELECT create_hypertable(
    'conflict_events', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 시뮬레이션 런 요약 (정규 테이블 — 시계열 아님)
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scenario        TEXT        NOT NULL,
    method          TEXT        NOT NULL,
    seed            INTEGER,
    n_drones        INTEGER,
    duration_s      REAL,
    near_miss_rate  REAL,
    path_efficiency REAL,
    rid_compliance  REAL,
    completed_at    TIMESTAMPTZ
);

-- WebSocket 감사 로그 (P712 RBAC 연동)
CREATE TABLE IF NOT EXISTS audit_log (
    time        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    user_id     TEXT            NOT NULL,
    role        TEXT            NOT NULL,
    action      TEXT            NOT NULL,
    resource    TEXT,
    ip_addr     INET,
    success     BOOLEAN         NOT NULL DEFAULT TRUE
);

SELECT create_hypertable(
    'audit_log', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_telemetry_drone ON drone_telemetry (drone_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_conflict_run    ON conflict_events (run_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_runs_scenario   ON simulation_runs (scenario, created_at DESC);
