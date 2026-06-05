# SDACS Frontend (Phase 711)

`api/fastapi_server.py` 백엔드를 위한 React + TypeScript + Vite 대시보드.
기존 Dash 3D 시각화를 대체하는 점진적 마이그레이션 경로의 프론트엔드 파트입니다.

## 기능 (MVP)

- **시나리오 목록** — `GET /api/scenarios` 조회 및 선택
- **시나리오 실행** — `POST /api/scenarios/{id}/run` (Bearer 토큰 필요) 후
  `GET /api/runs/{run_id}` 폴링으로 완료/메트릭 표시
- **실시간 텔레메트리** — `WS /ws/telemetry` 구독 토글 (드론·충돌 수)

## 개발

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (백엔드 CORS 허용 포트)
```

백엔드는 별도로 실행:

```bash
uvicorn api.fastapi_server:app --reload --port 8000
```

백엔드 주소가 다르면 `VITE_API_BASE` 환경변수로 덮어쓸 수 있습니다.

```bash
VITE_API_BASE=http://localhost:8080 npm run dev
```

## 검증

```bash
npm run build        # tsc 타입체크 + vite 프로덕션 빌드
npm test             # vitest (API 클라이언트 봉투/URL 단위 테스트)
```

## 인증

`POST /api/scenarios/{id}/run` 은 `Authorization: Bearer <token>` 을 요구합니다
(P712 RBAC). 상단 입력란에 토큰을 붙여넣으면 실행 요청에 자동 첨부됩니다.
