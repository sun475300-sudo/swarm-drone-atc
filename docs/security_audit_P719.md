# P719 보안 감사 보고서

**감사 일시:** 2026-05-31  
**감사 범위:** `api/`, `simulation/db_store.py`, `scripts/load_test.py`  
**도구:** bandit 1.9.x (OWASP 기반 Python 정적 분석)

---

## 요약

| 심각도 | 건수 | 처리 |
|--------|------|------|
| High   | 0    | —    |
| Medium | 1    | 수용 (개발 서버 의도된 동작) |
| Low    | 1    | 수용 |

**High 이슈 없음 — 배포 차단 없음.**

---

## 발견 사항

### M01 — B104 hardcoded_bind_all_interfaces (MEDIUM)

- **파일:** `api/fastapi_server.py:823`
- **코드:** `run_dev_server(host: str = "0.0.0.0", ...)`
- **CWE:** CWE-605
- **평가:** 개발 서버 전용 함수. 프로덕션에서는 Helm/Docker로 포트 제한. 수용.

### L01 — B603 subprocess_without_shell_equals_true (LOW)

- 해당 없음 (이번 감사 범위에서 미발생)

---

## 보안 체크리스트

- [x] 하드코딩된 시크릿 없음 (`SDACS_JWT_SECRET` 환경변수 사용)
- [x] JWT 서명 검증 (HS256, `api/auth.py`)
- [x] RBAC 역할 분리 (admin / operator / viewer)
- [x] 감사 로그 (`logs/audit.jsonl`)
- [x] SQL Injection 없음 (asyncpg 파라미터 바인딩 사용)
- [x] CORS 허용 도메인 제한 (localhost:3000, localhost:5173)
- [x] 권한 없는 토큰 → 401/403 반환 확인
- [ ] OWASP ZAP 동적 스캔 (프로덕션 배포 후 수행)
- [ ] 의존성 CVE 스캔 (pip-audit, P720 전 수행)

---

## 의존성 CVE 스크리닝

```
pip install pip-audit
pip-audit -r requirements.txt
```

*현재 컨테이너 환경에서 pip-audit 실행 불가 (네트워크 제한). 프로덕션 배포 시 CI에서 수행.*

---

## 권장 사항

1. `SDACS_JWT_SECRET`을 최소 32바이트 랜덤 값으로 설정 (Kubernetes Secret 또는 Vault)
2. `SDACS_ADMIN_SECRET`을 환경변수로 주입 (빈 값이면 admin/operator 토큰 발급 차단)
3. 프로덕션 배포 전 OWASP ZAP 자동화 스캔 추가 (`deployment/helm/` 배포 후 CI 단계)
4. PostgreSQL 연결 TLS 활성화 (`sslmode=require` in DSN)
