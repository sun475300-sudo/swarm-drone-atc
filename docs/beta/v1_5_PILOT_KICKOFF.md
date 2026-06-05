# 🚀 SDACS v1.5.0 베타 파일럿 킥오프 가이드 (트랙 ④)

*Created: 2026-06-05 — Phase 50 (Public Beta) 격상용*

## 🎯 목표

3개 파일럿 기관에서 SDACS v1.5.0을 실 운영 데이터로 1개월 시범 가동하여 NPS 70 이상을 달성한다.

## 🏢 파일럿 후보 (`docs/beta/README.md` 명시)

| 기관 | 용도 | 시작 가능 시점 |
|---|---|---|
| KARI (한국항공우주연구원) | UAM K-Grand Challenge 사전 시뮬 | 협의 |
| 해수부 항만공사 | 항만 드론 관제 (Phase 11 해양 ATC) | 협의 |
| 산림청 (산불 감시) | 야간 IR + Phase 28 군무 (Phase 41 procedural city) | 협의 |

## 📦 1단계 — Helm 차트 배포

```bash
cd helm/sdacs
helm install sdacs-pilot ./ \
  --namespace sdacs-beta \
  --create-namespace \
  --set image.tag=v1.5.0 \
  --set ingress.hosts[0].host=sdacs.pilot.example.com \
  --set timescaledb.persistence.size=100Gi
```

차트 구성 (8 템플릿):
- Deployment (API + WebSocket)
- Service (ClusterIP + LoadBalancer)
- Ingress (TLS)
- HPA (CPU 80% threshold)
- Redis (session cache)
- TimescaleDB StatefulSet (30일 보존)
- ConfigMap (시나리오·NFZ)
- Secret (JWT key + DB password)

## 📦 2단계 — JWT 발급

```bash
# 파일럿 운영자에게 발급 (3 RBAC)
python3 -c "
from api.auth import create_token
print(create_token({'sub':'pilot-kari','role':'operator'}, exp_hours=720))
"  # 30일 유효
```

## 📦 3단계 — TimescaleDB 30일 보존 활성

`db/migrations/001_initial_schema.sql` 의 hypertable 자동 생성. `retention_policy = '30 days'` 가 ConfigMap에 명시되어 있다.

## 📦 4단계 — Grafana 대시보드 import

```bash
kubectl port-forward svc/grafana 3000:3000 -n sdacs-beta
# 브라우저 → http://localhost:3000
# JSON import: monitoring/grafana_dashboard_sdacs_v1.5.json
```

대시보드 패널:
- 활성 드론 수 (실시간 게이지)
- 충돌 해결률 (지난 1시간)
- p50/p99 simulation tick latency
- 5계층 안전망 발동 빈도 (히트맵)
- API 호출 분포 (Top 20 _sdacs 호출)

## 📦 5단계 — NPS 자동 수집

```javascript
// 시뮬 종료 후 자동 팝업
window._sdacs.publicDemoLeaderboardAdd('Pilot Operator', score);
// → leaderboard.json 30일 누적 → NPS 추출
```

설문 항목:
- "SDACS를 동료에게 추천할 의향은? (0-10)" → NPS = 추천(9-10) − 비추천(0-6)
- 자유 응답 5문항

## 🧪 검증 매트릭스 (베타 완료 기준)

| 항목 | 기준 | 측정 |
|---|---|---|
| 가동 시간 | 99% (월 7.2시간 다운 허용) | Prometheus uptime |
| API 응답 p99 | < 200 ms | Grafana histogram |
| NPS | ≥ 70 (Promoter ratio) | leaderboard.json |
| 활성 사용자 (월) | ≥ 30 | DB session count |
| 데이터 유실률 | < 0.01% | DB row count vs ingestion |

## ⏭ 후속 작업

- 파일럿 피드백 → v1.6 신규 기능 prioritization
- 3 기관 NPS 평균 산출 → 캡스톤 발표 자료
- 사고 RCA (실제 발생 시) → docs/HEALTH_CHECK.md 갱신

## 📚 관련

- [`docs/beta/README.md`](README.md) — 베타 운영 가이드 원문
- [`docs/V1_5_0_RELEASE_INSTRUCTIONS.md`](../V1_5_0_RELEASE_INSTRUCTIONS.md)
- [`helm/sdacs/`](../../helm/sdacs/) — Helm 차트
- [`monitoring/prometheus.yml`](../../monitoring/prometheus.yml) — 메트릭 수집
- [`api/auth.py`](../../api/auth.py) — JWT + RBAC
