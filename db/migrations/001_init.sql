-- P714: SDACS 텔레메트리 이력 저장 스키마
-- TimescaleDB hypertable, 30일 보존 정책

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 드론 텔레메트리 원시 데이터
CREATE TABLE IF NOT EXISTS drone_telemetry (
    ts          TIMESTAMPTZ     NOT NULL,
    drone_id    TEXT            NOT NULL,
    run_id      TEXT            NOT NULL,
    x           DOUBLE PRECISION,
    y           DOUBLE PRECISION,
    z           DOUBLE PRECISION,
    vx          DOUBLE PRECISION,
    vy          DOUBLE PRECISION,
    vz          DOUBLE PRECISION,
    speed       DOUBLE PRECISION,
    battery_pct DOUBLE PRECISION,
    state       TEXT,
    PRIMARY KEY (ts, drone_id, run_id)
);

SELECT create_hypertable(
    'drone_telemetry', 'ts',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- 30일 보존 정책
SELECT add_retention_policy(
    'drone_telemetry',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- 충돌/위험 이벤트 로그
CREATE TABLE IF NOT EXISTS conflict_events (
    ts          TIMESTAMPTZ     NOT NULL,
    run_id      TEXT            NOT NULL,
    drone_a     TEXT            NOT NULL,
    drone_b     TEXT            NOT NULL,
    cpa_dist_m  DOUBLE PRECISION,
    resolved    BOOLEAN         DEFAULT FALSE,
    PRIMARY KEY (ts, run_id, drone_a, drone_b)
);

SELECT create_hypertable(
    'conflict_events', 'ts',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

SELECT add_retention_policy(
    'conflict_events',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- 시뮬레이션 실행 메타데이터
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id      TEXT            PRIMARY KEY,
    scenario    TEXT            NOT NULL,
    started_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    drone_count INTEGER,
    seed        INTEGER,
    metrics     JSONB
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_telemetry_run_drone ON drone_telemetry (run_id, drone_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_conflict_run ON conflict_events (run_id, ts DESC);
