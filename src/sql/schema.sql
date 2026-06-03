-- SDACS 데이터베이스 스키마 — SQL (PostgreSQL)
-- ==============================================
-- 드론 관제 데이터 영구 저장 + 분석 쿼리
--
-- 기능:
--   - 드론 등록/이력 관리
--   - 비행 로그 저장
--   - 충돌 이벤트 기록
--   - 시뮬레이션 결과 저장
--   - 성능 분석 뷰

-- ── 드론 마스터 ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS drones (
    drone_id        VARCHAR(50) PRIMARY KEY,
    drone_type      VARCHAR(30) NOT NULL DEFAULT 'DELIVERY',
    owner_id        VARCHAR(50) NOT NULL,
    model           VARCHAR(100),
    max_speed_ms    DOUBLE PRECISION DEFAULT 15.0,
    max_altitude_m  DOUBLE PRECISION DEFAULT 120.0,
    battery_wh      DOUBLE PRECISION DEFAULT 500.0,
    payload_kg      DOUBLE PRECISION DEFAULT 5.0,
    status          VARCHAR(20) DEFAULT 'REGISTERED',
    cert_status     VARCHAR(20) DEFAULT 'PENDING',
    registered_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    retired_at      TIMESTAMP WITH TIME ZONE,
    total_flight_hrs DOUBLE PRECISION DEFAULT 0,
    total_missions  INTEGER DEFAULT 0,
    violations      INTEGER DEFAULT 0
);

CREATE INDEX idx_drones_status ON drones(status);
CREATE INDEX idx_drones_owner ON drones(owner_id);

-- ── 비행 로그 ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS flight_logs (
    log_id          BIGSERIAL PRIMARY KEY,
    drone_id        VARCHAR(50) REFERENCES drones(drone_id),
    mission_id      VARCHAR(100),
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    position_x      DOUBLE PRECISION NOT NULL,
    position_y      DOUBLE PRECISION NOT NULL,
    position_z      DOUBLE PRECISION NOT NULL,
    velocity_x      DOUBLE PRECISION DEFAULT 0,
    velocity_y      DOUBLE PRECISION DEFAULT 0,
    velocity_z      DOUBLE PRECISION DEFAULT 0,
    heading_deg     DOUBLE PRECISION DEFAULT 0,
    speed_ms        DOUBLE PRECISION DEFAULT 0,
    battery_pct     DOUBLE PRECISION DEFAULT 100,
    gps_satellites  INTEGER DEFAULT 12,
    signal_strength DOUBLE PRECISION DEFAULT 100
);

CREATE INDEX idx_flight_drone ON flight_logs(drone_id, timestamp);
CREATE INDEX idx_flight_mission ON flight_logs(mission_id);

-- 파티셔닝 (시간 기반 — 일 단위)
-- CREATE TABLE flight_logs_2026_03 PARTITION OF flight_logs
--   FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- ── 충돌/분쟁 이벤트 ───────────────────────────────────

CREATE TABLE IF NOT EXISTS conflict_events (
    event_id        BIGSERIAL PRIMARY KEY,
    drone_a         VARCHAR(50) REFERENCES drones(drone_id),
    drone_b         VARCHAR(50) REFERENCES drones(drone_id),
    event_type      VARCHAR(30) NOT NULL,  -- CONFLICT, COLLISION, NEAR_MISS
    severity        VARCHAR(20) NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    cpa_distance_m  DOUBLE PRECISION,
    cpa_time_sec    DOUBLE PRECISION,
    position_a      JSONB,  -- {"x": 0, "y": 0, "z": 0}
    position_b      JSONB,
    advisory_type   VARCHAR(30),  -- CLIMB, DESCEND, TURN, etc.
    resolved        BOOLEAN DEFAULT FALSE,
    resolution_ms   DOUBLE PRECISION,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conflict_time ON conflict_events(timestamp);
CREATE INDEX idx_conflict_severity ON conflict_events(severity);

-- ── 시뮬레이션 결과 ────────────────────────────────────

CREATE TABLE IF NOT EXISTS simulation_results (
    result_id       BIGSERIAL PRIMARY KEY,
    scenario_name   VARCHAR(100) NOT NULL,
    run_seed        INTEGER NOT NULL,
    drone_count     INTEGER NOT NULL,
    duration_sec    DOUBLE PRECISION NOT NULL,
    wind_speed      DOUBLE PRECISION DEFAULT 0,
    failure_rate    DOUBLE PRECISION DEFAULT 0,
    total_conflicts INTEGER DEFAULT 0,
    total_collisions INTEGER DEFAULT 0,
    collision_rate  DOUBLE PRECISION,
    resolution_rate DOUBLE PRECISION,
    avg_response_ms DOUBLE PRECISION,
    p50_latency_ms  DOUBLE PRECISION,
    p99_latency_ms  DOUBLE PRECISION,
    avg_battery     DOUBLE PRECISION,
    min_separation  DOUBLE PRECISION,
    sla_pass        BOOLEAN DEFAULT FALSE,
    config_json     JSONB,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sim_scenario ON simulation_results(scenario_name);
CREATE INDEX idx_sim_sla ON simulation_results(sla_pass);

-- ── 경보 이력 ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts (
    alert_id        BIGSERIAL PRIMARY KEY,
    drone_id        VARCHAR(50),
    alert_type      VARCHAR(50) NOT NULL,
    severity        VARCHAR(20) NOT NULL,
    title           VARCHAR(200),
    message         TEXT,
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(50),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at     TIMESTAMP WITH TIME ZONE
);

-- ── 감사 로그 ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_log (
    log_id          BIGSERIAL PRIMARY KEY,
    actor           VARCHAR(100) NOT NULL,
    action          VARCHAR(100) NOT NULL,
    target_type     VARCHAR(50),
    target_id       VARCHAR(100),
    details         JSONB,
    ip_address      INET,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_time ON audit_log(timestamp);
CREATE INDEX idx_audit_actor ON audit_log(actor);

-- ── 분석 뷰 ────────────────────────────────────────────

-- 시나리오별 SLA 요약
CREATE OR REPLACE VIEW v_scenario_sla AS
SELECT
    scenario_name,
    drone_count,
    COUNT(*) AS total_runs,
    ROUND(AVG(collision_rate)::numeric, 6) AS avg_collision_rate,
    ROUND(STDDEV(collision_rate)::numeric, 6) AS std_collision_rate,
    ROUND(100.0 * SUM(CASE WHEN sla_pass THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric, 1) AS sla_pass_pct,
    ROUND(AVG(avg_response_ms)::numeric, 2) AS avg_response_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY p99_latency_ms)::numeric, 2) AS p99_latency_ms
FROM simulation_results
GROUP BY scenario_name, drone_count
ORDER BY scenario_name, drone_count;

-- 드론별 성능 요약
CREATE OR REPLACE VIEW v_drone_performance AS
SELECT
    d.drone_id,
    d.drone_type,
    d.status,
    d.total_flight_hrs,
    d.total_missions,
    d.violations,
    COUNT(DISTINCT ce.event_id) AS conflict_count,
    AVG(fl.battery_pct) AS avg_battery_during_flight,
    AVG(fl.speed_ms) AS avg_speed
FROM drones d
LEFT JOIN conflict_events ce ON d.drone_id = ce.drone_a OR d.drone_id = ce.drone_b
LEFT JOIN flight_logs fl ON d.drone_id = fl.drone_id
GROUP BY d.drone_id, d.drone_type, d.status, d.total_flight_hrs, d.total_missions, d.violations;

-- 시간대별 교통량
CREATE OR REPLACE VIEW v_hourly_traffic AS
SELECT
    EXTRACT(HOUR FROM timestamp) AS hour,
    COUNT(DISTINCT drone_id) AS unique_drones,
    COUNT(*) AS telemetry_points,
    AVG(speed_ms) AS avg_speed,
    AVG(battery_pct) AS avg_battery
FROM flight_logs
GROUP BY EXTRACT(HOUR FROM timestamp)
ORDER BY hour;

-- ── 유용한 쿼리 ────────────────────────────────────────

-- 최근 24시간 충돌 이벤트
-- SELECT * FROM conflict_events
-- WHERE timestamp > NOW() - INTERVAL '24 hours'
-- ORDER BY severity DESC, timestamp DESC;

-- Monte Carlo SLA 통과율 (95% 신뢰구간)
-- SELECT
--     scenario_name,
--     AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END) AS pass_rate,
--     AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END)
--       - 1.96 * SQRT(AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END)
--       * (1 - AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END)) / COUNT(*)) AS ci_lower,
--     AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END)
--       + 1.96 * SQRT(AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END)
--       * (1 - AVG(CASE WHEN sla_pass THEN 1.0 ELSE 0.0 END)) / COUNT(*)) AS ci_upper
-- FROM simulation_results
-- GROUP BY scenario_name;
