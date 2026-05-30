-- P714: 보존 정책 (30/90/365일)
-- drone_telemetry: 30일 보존 + 7일 이후 압축
-- run_records: 수동 정책 권장 (90일)
-- audit_log: 규정 준수 요구에 따라 1년 권장

-- ─────────────────────────────────────────────
-- 1. drone_telemetry 보존 및 압축 정책
-- ─────────────────────────────────────────────

-- 30일 이상 된 텔레메트리 청크 자동 삭제
SELECT add_retention_policy('drone_telemetry', INTERVAL '30 days');

-- 7일 이상 된 청크 자동 압축 (스토리지 절감)
ALTER TABLE drone_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'drone_id'
);
SELECT add_compression_policy('drone_telemetry', INTERVAL '7 days');

-- ─────────────────────────────────────────────
-- 2. run_records 보존 권장 사항 (수동 적용)
-- ─────────────────────────────────────────────
-- run_records는 일반 PostgreSQL 테이블이므로 TimescaleDB 정책 직접 적용 불가.
-- 운영 환경에서는 아래 SQL을 cron 또는 pg_cron으로 주기적으로 실행 권장:
--
--   DELETE FROM run_records
--   WHERE finished_at < NOW() - INTERVAL '90 days'
--     AND status IN ('completed', 'failed');
--
-- 또는 pg_cron 확장 사용:
--   SELECT cron.schedule(
--     'purge-old-runs',
--     '0 3 * * *',
--     $$DELETE FROM run_records
--       WHERE finished_at < NOW() - INTERVAL '90 days'
--         AND status IN ('completed', 'failed')$$
--   );

-- ─────────────────────────────────────────────
-- 3. audit_log 보존 권장 사항 (수동 적용)
-- ─────────────────────────────────────────────
-- 감사 로그는 보안 규정 준수를 위해 최소 365일 보존 권장.
-- 장기 보관이 필요한 경우 콜드 스토리지로 아카이빙 후 삭제:
--
--   DELETE FROM audit_log
--   WHERE ts < NOW() - INTERVAL '365 days';
