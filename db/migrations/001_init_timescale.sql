-- P714: SDACS TimescaleDB 초기 스키마
-- 적용: psql $DATABASE_URL -f db/migrations/001_init_timescale.sql
-- 요구사항: PostgreSQL 14+ + TimescaleDB 2.10+

-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 사용자 / 인증
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,           -- SHA-256 hex
    role        TEXT NOT NULL DEFAULT 'viewer'
                    CHECK (role IN ('viewer', 'operator', 'admin')),
    disabled    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action      TEXT NOT NULL,
    username    TEXT NOT NULL,
    detail      TEXT DEFAULT ''
);

-- audit_log을 hypertable로 변환 (시계열 파티셔닝)
SELECT create_hypertable('audit_log', 'ts', if_not_exists => TRUE);

-- ============================================================
-- 시나리오 / 실행
-- ============================================================
CREATE TABLE IF NOT EXISTS scenarios (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    difficulty  TEXT,
    config      JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runs (
    run_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id TEXT NOT NULL REFERENCES scenarios(id),
    status      TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    method      TEXT NOT NULL DEFAULT 'hybrid',
    seed        INT NOT NULL DEFAULT 42,
    duration_s  INT NOT NULL DEFAULT 60,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    metrics     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS runs_scenario_id_idx ON runs(scenario_id);
CREATE INDEX IF NOT EXISTS runs_status_idx ON runs(status);
CREATE INDEX IF NOT EXISTS runs_created_at_idx ON runs(created_at DESC);

-- ============================================================
-- 드론 텔레메트리 (TimescaleDB hypertable)
-- 30일 보존 정책 적용
-- ============================================================
CREATE TABLE IF NOT EXISTS telemetry (
    ts          TIMESTAMPTZ NOT NULL,
    drone_id    TEXT NOT NULL,
    run_id      UUID,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    alt_m       REAL,
    vx          REAL,
    vy          REAL,
    vz          REAL,
    heading_deg REAL,
    battery_pct REAL,
    status      TEXT,
    raw         JSONB
);

SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);

-- 30일 보존 (오래된 청크 자동 삭제)
SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- 쿼리 성능 인덱스
CREATE INDEX IF NOT EXISTS telemetry_drone_id_ts_idx ON telemetry(drone_id, ts DESC);
CREATE INDEX IF NOT EXISTS telemetry_run_id_idx ON telemetry(run_id, ts DESC);

-- ============================================================
-- 충돌/근접 이벤트
-- ============================================================
CREATE TABLE IF NOT EXISTS conflict_events (
    ts          TIMESTAMPTZ NOT NULL,
    run_id      UUID,
    drone_a     TEXT NOT NULL,
    drone_b     TEXT NOT NULL,
    cpa_dist_m  REAL,
    cpa_time_s  REAL,
    severity    TEXT CHECK (severity IN ('advisory', 'warning', 'critical')),
    resolved    BOOLEAN NOT NULL DEFAULT FALSE
);

SELECT create_hypertable('conflict_events', 'ts', if_not_exists => TRUE);
SELECT add_retention_policy('conflict_events', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================
-- 연속 집계 뷰 (1분 버킷 평균)
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_1min
WITH (timescaledb.continuous) AS
    SELECT
        time_bucket('1 minute', ts) AS bucket,
        drone_id,
        AVG(alt_m)           AS avg_alt_m,
        AVG(battery_pct)     AS avg_battery_pct,
        COUNT(*)             AS sample_count
    FROM telemetry
    GROUP BY bucket, drone_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_1min',
    start_offset => INTERVAL '2 hours',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- ============================================================
-- 시드 시나리오
-- ============================================================
INSERT INTO scenarios(id, name, difficulty, config) VALUES
    ('empty_sky',          'Empty Sky',           'trivial', '{"n_drones": 0}'),
    ('light_traffic_10',   'Light Traffic (10)',   'easy',    '{"n_drones": 10}'),
    ('dense_traffic_50',   'Dense Traffic (50)',   'medium',  '{"n_drones": 50}'),
    ('stress_200',         'Stress (200)',          'hard',    '{"n_drones": 200}'),
    ('crosswind_corridor', 'Crosswind Corridor',   'medium',  '{"n_drones": 20}'),
    ('geofence_breach',    'Geofence Breach',      'hard',    '{"n_drones": 15}'),
    ('remote_id_loss',     'Remote ID Loss',       'easy',    '{"n_drones": 10}')
ON CONFLICT (id) DO NOTHING;
