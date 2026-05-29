-- SDACS 30일 데이터 보존 정책 (P714)
-- TimescaleDB add_retention_policy 사용
-- 실행: psql -U sdacs sdacs -f 002_retention_policy.sql

-- drone_telemetry: 30일 보존
SELECT add_retention_policy(
    'drone_telemetry',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- conflict_events: 90일 보존 (사고 분석용)
SELECT add_retention_policy(
    'conflict_events',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- audit_log: 365일 보존 (컴플라이언스)
SELECT add_retention_policy(
    'audit_log',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- 압축 정책 (7일 이상 청크 압축)
SELECT add_compression_policy(
    'drone_telemetry',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

ALTER TABLE drone_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'drone_id',
    timescaledb.compress_orderby = 'time DESC'
);
