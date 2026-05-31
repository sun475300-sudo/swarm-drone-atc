-- P714 — SDACS PostgreSQL + TimescaleDB 초기 스키마
-- 실행: psql -U sdacs -d sdacs -f 001_init.sql

-- TimescaleDB 확장 (TimescaleDB 없이 일반 Postgres로도 동작)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── 드론 텔레메트리 (시계열) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    drone_id    TEXT        NOT NULL,
    x_m         DOUBLE PRECISION,
    y_m         DOUBLE PRECISION,
    z_m         DOUBLE PRECISION,
    vx_m_s      DOUBLE PRECISION,
    vy_m_s      DOUBLE PRECISION,
    vz_m_s      DOUBLE PRECISION,
    battery_pct REAL,
    status      TEXT
);

-- TimescaleDB 하이퍼테이블 변환 (없으면 일반 테이블로 유지)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable(
            'drone_telemetry', 'time',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_telemetry_drone_time
    ON drone_telemetry (drone_id, time DESC);

-- ── 충돌 이벤트 ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conflict_events (
    id          BIGSERIAL   PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    drone_a_id  TEXT        NOT NULL,
    drone_b_id  TEXT        NOT NULL,
    separation_m DOUBLE PRECISION,
    resolved    BOOLEAN     DEFAULT FALSE,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conflicts_time ON conflict_events (detected_at DESC);

-- ── 시뮬레이션 실행 이력 ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id TEXT,
    method      TEXT,
    seed        INTEGER,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status      TEXT        NOT NULL DEFAULT 'running',
    metrics     JSONB,
    error_msg   TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_scenario ON simulation_runs (scenario_id, started_at DESC);

-- ── 사용자 / RBAC ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL   PRIMARY KEY,
    username    TEXT        UNIQUE NOT NULL,
    password_hash TEXT      NOT NULL,
    role        TEXT        NOT NULL DEFAULT 'viewer',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login  TIMESTAMPTZ,
    active      BOOLEAN     NOT NULL DEFAULT TRUE
);

-- ── 감사 로그 ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL   PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id     BIGINT      REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT        NOT NULL,
    resource    TEXT,
    detail      JSONB,
    ip_addr     TEXT
);

-- 30일 보존 정책 (TimescaleDB 있을 때만)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM add_retention_policy(
            'drone_telemetry',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );
    END IF;
END;
$$;
