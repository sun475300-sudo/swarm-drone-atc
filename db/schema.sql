-- SDACS P714 — PostgreSQL + TimescaleDB 이력 저장 스키마
-- 30일 보존 정책 적용

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─── 시뮬레이션 런 ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sim_runs (
    run_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario    TEXT        NOT NULL,
    method      TEXT        NOT NULL,
    seed        INTEGER     NOT NULL,
    n_drones    INTEGER     NOT NULL,
    duration_s  REAL        NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status      TEXT        NOT NULL DEFAULT 'running' CHECK (status IN ('running','done','failed')),
    metrics     JSONB
);

-- ─── 드론 텔레메트리 (TimescaleDB 하이퍼테이블) ─────────────────────────────
CREATE TABLE IF NOT EXISTS telemetry (
    ts          TIMESTAMPTZ NOT NULL,
    run_id      UUID        NOT NULL REFERENCES sim_runs(run_id) ON DELETE CASCADE,
    drone_id    INTEGER     NOT NULL,
    x           REAL        NOT NULL,
    y           REAL        NOT NULL,
    z           REAL        NOT NULL,
    vx          REAL,
    vy          REAL,
    vz          REAL,
    battery_pct REAL,
    state       TEXT
);

SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);

-- 30일 보존 정책
SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- ─── 충돌/갈등 이벤트 ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conflict_events (
    ts          TIMESTAMPTZ NOT NULL,
    run_id      UUID        NOT NULL REFERENCES sim_runs(run_id) ON DELETE CASCADE,
    drone_a     INTEGER     NOT NULL,
    drone_b     INTEGER     NOT NULL,
    separation  REAL        NOT NULL,
    resolved    BOOLEAN     NOT NULL DEFAULT FALSE,
    resolver    TEXT
);

SELECT create_hypertable('conflict_events', 'ts', if_not_exists => TRUE);
SELECT add_retention_policy('conflict_events', INTERVAL '30 days', if_not_exists => TRUE);

-- ─── 감사 로그 ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event       TEXT        NOT NULL,
    subject     TEXT        NOT NULL,
    detail      TEXT,
    remote_ip   TEXT
);

SELECT create_hypertable('audit_log', 'ts', if_not_exists => TRUE);
SELECT add_retention_policy('audit_log', INTERVAL '90 days', if_not_exists => TRUE);

-- ─── 인덱스 ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS telemetry_run_drone ON telemetry (run_id, drone_id, ts DESC);
CREATE INDEX IF NOT EXISTS conflicts_run ON conflict_events (run_id, ts DESC);
CREATE INDEX IF NOT EXISTS audit_subject ON audit_log (subject, ts DESC);
