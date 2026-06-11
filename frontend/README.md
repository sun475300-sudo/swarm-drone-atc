# SDACS Frontend (P711 React MVP)

공역 관리자용 React 대시보드. 기존 FastAPI 백엔드(`api/fastapi_server.py`)를
그대로 소비합니다. 별도 백엔드 변경 없이 동작합니다.

## 기능

- **로그인** — `POST /auth/token` (JWT, RBAC 역할 표시). 데모 계정: `admin` / `operator` / `viewer`
- **헬스 배지** — `GET /health` 버전·상태·백엔드(GPU/CPU)
- **시나리오 실행** — `GET /api/scenarios` 목록 + `POST /api/scenarios/{id}/run` (Bearer) → `GET /api/runs/{id}` 폴링으로 결과 메트릭 표시
- **공역 스냅샷** — `GET /api/airspace/snapshot` 2초 폴링 (드론 수·충돌 경고)
- **실시간 텔레메트리** — `WS /ws/telemetry` 이벤트 피드

## 개발 실행

```bash
# 1) 백엔드 (별도 터미널, 8000 포트)
python -m api.fastapi_server         # 또는 uvicorn api.fastapi_server:app

# 2) 프론트엔드
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

`vite.config.js` 가 `/api`·`/auth`·`/health`·`/ws` 를 백엔드(8000)로 프록시합니다.
백엔드 CORS 는 이미 `http://localhost:3000` 을 허용합니다.

## 빌드 / 테스트

```bash
npm run build      # dist/ 정적 번들
npm run preview    # 빌드 산출물 미리보기
npm test           # vitest (api 클라이언트 단위 테스트)
```

## 구성

| 파일 | 역할 |
|---|---|
| `src/api.js` | FastAPI 클라이언트 + JWT 세션 + 응답 봉투 정규화 |
| `src/App.jsx` | 인증 게이트 (로그인 ↔ 대시보드) |
| `src/components/Dashboard.jsx` | 패널 레이아웃 |
| `src/components/Login.jsx` | 자격증명 → JWT |
| `src/components/ScenarioList.jsx` | 시나리오 실행 + run 폴링 |
| `src/components/SnapshotPanel.jsx` | 공역 스냅샷 폴링 |
| `src/components/TelemetryFeed.jsx` | WebSocket 텔레메트리 |
| `src/components/HealthBadge.jsx` | 백엔드 헬스 |

## 보안 참고

데모 MVP 이므로 JWT 를 `localStorage` 에 저장합니다 (XSS 노출 트레이드오프).
프로덕션 강화 시 httpOnly 쿠키 + CSRF 토큰 전환을 권장합니다.
