-- P714: TimescaleDB 스키마 초기화
-- 드론 텔레메트리, 실행 기록, 감사 로그 테이블 생성

-- 확장 활성화 (TimescaleDB)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─────────────────────────────────────────────
-- 1. 드론 텔레메트리 (시계열 하이퍼테이블)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time          TIMESTAMPTZ     NOT NULL,
    drone_id      TEXT            NOT NULL,
    lat           DOUBLE PRECISION NOT NULL,
    lon           DOUBLE PRECISION NOT NULL,
    alt           DOUBLE PRECISION NOT NULL,
    vx            FLOAT,
    vy            FLOAT,
    vz            FLOAT,
    battery_pct   FLOAT,
    phase         TEXT
);

SELECT create_hypertable('drone_telemetry', 'time');

-- 빠른 드론별 시계열 조회를 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_drone_telemetry_drone_id_time
    ON drone_telemetry (drone_id, time DESC);

-- ─────────────────────────────────────────────
-- 2. 시뮬레이션 실행 기록
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS run_records (
    run_id                  UUID            PRIMARY KEY,
    scenario_id             TEXT            NOT NULL,
    started_at              TIMESTAMPTZ     NOT NULL,
    finished_at             TIMESTAMPTZ,
    drone_count             INT             NOT NULL DEFAULT 0,
    conflict_resolution_rate FLOAT,
    status                  TEXT            NOT NULL DEFAULT 'pending'
);

-- ─────────────────────────────────────────────
-- 3. 감사 로그
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id        BIGSERIAL       PRIMARY KEY,
    ts        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    user_id   TEXT            NOT NULL,
    action    TEXT            NOT NULL,
    details   JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_log_ts
    ON audit_log (ts DESC);
