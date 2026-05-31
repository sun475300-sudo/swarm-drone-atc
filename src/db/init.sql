-- P714 — TimescaleDB 초기화 스키마 (드론 텔레메트리 + 이벤트 + 감사 로그)

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── 드론 텔레메트리 하이퍼테이블 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time        TIMESTAMPTZ     NOT NULL,
    drone_id    TEXT            NOT NULL,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    alt         DOUBLE PRECISION,
    vx          DOUBLE PRECISION,
    vy          DOUBLE PRECISION,
    vz          DOUBLE PRECISION,
    battery_pct SMALLINT,
    status      TEXT
);

SELECT create_hypertable('drone_telemetry', 'time', if_not_exists => TRUE);

-- 30일 보존 정책
SELECT add_retention_policy('drone_telemetry', INTERVAL '30 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_telemetry_drone_time
    ON drone_telemetry (drone_id, time DESC);

-- ── 충돌 / 갈등 이벤트 ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS airspace_events (
    time        TIMESTAMPTZ     NOT NULL,
    event_type  TEXT            NOT NULL,  -- 'conflict' | 'collision' | 'resolution'
    drone_a     TEXT,
    drone_b     TEXT,
    resolution  TEXT,
    severity    SMALLINT DEFAULT 1,
    detail      JSONB
);

SELECT create_hypertable('airspace_events', 'time', if_not_exists => TRUE);
SELECT add_retention_policy('airspace_events', INTERVAL '30 days', if_not_exists => TRUE);

-- ── 감사 로그 (P712) ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    time        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    event       TEXT            NOT NULL,
    user_id     TEXT,
    resource    TEXT,
    success     BOOLEAN         DEFAULT TRUE,
    detail      TEXT
);

SELECT create_hypertable('audit_log', 'time', if_not_exists => TRUE);
SELECT add_retention_policy('audit_log', INTERVAL '30 days', if_not_exists => TRUE);
