-- P714: 데이터 보존 정책 + 청크 압축
-- 실행 전 001_init_schema.sql 완료 필요

-- drone_telemetry: 30일 보존
SELECT add_retention_policy(
    'drone_telemetry',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- conflict_events: 90일 보존
SELECT add_retention_policy(
    'conflict_events',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- audit_log: 365일 보존
SELECT add_retention_policy(
    'audit_log',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- 7일 이상 오래된 청크 압축 (telemetry)
ALTER TABLE drone_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'drone_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy(
    'drone_telemetry',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- 충돌 이벤트 청크 압축 (30일+)
ALTER TABLE conflict_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'scenario_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy(
    'conflict_events',
    INTERVAL '30 days',
    if_not_exists => TRUE
);
