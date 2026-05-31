# SDACS Database Setup (P714)

## Quick start

```bash
# 1. 컨테이너 실행
docker run -d \
  -e POSTGRES_DB=sdacs \
  -e POSTGRES_USER=sdacs \
  -e POSTGRES_PASSWORD=sdacs \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg16

# 2. 스키마 적용
psql postgresql://sdacs:sdacs@localhost:5432/sdacs -f deployment/db/001_init.sql
```

## 테이블 구조

| 테이블 | 설명 | 보존 |
|--------|------|------|
| `drone_telemetry` | 드론 위치·속도 시계열 (하이퍼테이블) | 30일 |
| `conflict_events` | 충돌 감지·해결 이벤트 | 무제한 |
| `simulation_runs` | 시뮬레이션 실행 이력 + 메트릭 JSONB | 무제한 |
| `users` | 사용자 + RBAC 역할 | 무제한 |
| `audit_log` | API 호출 감사 로그 | 90일 권장 |

## TimescaleDB 없이 사용

TimescaleDB 확장이 없는 일반 Postgres에서도 스키마가 동작합니다.  
`create_hypertable` 및 `add_retention_policy` 호출은 DO $$ 블록 안에서 조건부로 실행됩니다.
