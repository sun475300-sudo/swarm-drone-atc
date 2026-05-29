-- P714 — SDACS TimescaleDB 초기화 스크립트
-- 드론 텔레메트리 이력 30일 보존 정책 적용

-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- 드론 텔레메트리 시계열 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time        TIMESTAMPTZ NOT NULL,
    run_id      UUID        NOT NULL,
    drone_id    TEXT        NOT NULL,
    x           DOUBLE PRECISION,  -- 세계 좌표 x (m)
    y           DOUBLE PRECISION,  -- 고도 (m)
    z           DOUBLE PRECISION,  -- 세계 좌표 z (m)
    vx          DOUBLE PRECISION,  -- 속도 벡터 x (m/s)
    vy          DOUBLE PRECISION,
    vz          DOUBLE PRECISION,
    heading_deg DOUBLE PRECISION,
    battery_pct DOUBLE PRECISION,
    phase       TEXT,              -- FLYING / EVADING / HOLDING / RTL / GROUNDED / FAILED
    PRIMARY KEY (time, run_id, drone_id)
);

-- 하이퍼테이블 변환 (청크 크기 1일)
SELECT create_hypertable('drone_telemetry', 'time', if_not_exists => TRUE);

-- 30일 데이터 보존 정책
SELECT add_retention_policy('drone_telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================
-- 충돌/근접 이벤트 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS conflict_events (
    time         TIMESTAMPTZ NOT NULL,
    run_id       UUID        NOT NULL,
    drone_a      TEXT        NOT NULL,
    drone_b      TEXT        NOT NULL,
    event_type   TEXT        NOT NULL,  -- NEAR_MISS / COLLISION / ADVISORY
    distance_m   DOUBLE PRECISION,
    ttc_s        DOUBLE PRECISION,      -- Time-to-conflict (예측값)
    PRIMARY KEY (time, run_id, drone_a, drone_b)
);

SELECT create_hypertable('conflict_events', 'time', if_not_exists => TRUE);
SELECT add_retention_policy('conflict_events', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================
-- 시뮬레이션 실행 메타데이터
-- ============================================================
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,
    scenario     TEXT,
    method       TEXT,
    seed         INTEGER,
    n_drones     INTEGER,
    duration_s   DOUBLE PRECISION,
    -- KPI 요약
    nmr          DOUBLE PRECISION,  -- Near-Miss Rate
    msd_m        DOUBLE PRECISION,  -- Minimum Separation Distance (m)
    path_eff     DOUBLE PRECISION,  -- Path Efficiency [0,1]
    conflict_res DOUBLE PRECISION,  -- 충돌 해결률 [0,1]
    status       TEXT DEFAULT 'pending'
);

-- ============================================================
-- 인덱스 (조회 성능)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_telemetry_run ON drone_telemetry (run_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_drone ON drone_telemetry (drone_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_conflict_run ON conflict_events (run_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_runs_scenario ON simulation_runs (scenario, started_at DESC);

-- ============================================================
-- 연속 집계 뷰 (분 단위 KPI)
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_minutely
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    run_id,
    COUNT(DISTINCT drone_id)                       AS active_drones,
    AVG(battery_pct)                               AS avg_battery,
    COUNT(*) FILTER (WHERE phase = 'EVADING')      AS evading_count,
    COUNT(*) FILTER (WHERE phase = 'FAILED')       AS failed_count
FROM drone_telemetry
GROUP BY bucket, run_id;

SELECT add_continuous_aggregate_policy('telemetry_minutely',
    start_offset    => INTERVAL '10 minutes',
    end_offset      => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists   => TRUE
);
