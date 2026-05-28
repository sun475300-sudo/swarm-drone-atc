# SDACS 추가 작업 계획서 (2026-05-15)

> **작성일**: 2026-05-15
> **목적**: 2026-05-08 검증 결과와 2026-04-26 백로그를 기준으로, 발표 이후 실제로 남아 있는 작업을 다시 정리하고 다음 4주 실행 계획을 확정한다.
> **기준 문서**: `docs/final_status_summary.md`, `docs/verification_report.md`, `docs/MASTER_TODO_ATC.md`, `docs/TASK_LIST_2026-04-25.md`, `docs/paper/PAPER_TOPIC.md`, `docs/REPRODUCIBILITY.md`

---

## 1. 현재 상태 요약

- 발표 준비와 기본 검증은 2026-05-08 기준으로 대부분 완료되었다.
- 다만, **재현성 패키지 마감**, **논문화 실행**, **하드웨어/서비스화 착수 준비**는 아직 완결되지 않았다.
- 따라서 현재 시점의 핵심은 "기능 추가"보다 **신뢰도 회복 + 후속 산출물 완성**에 있다.

### 이미 확보된 자산

- 9개 운영 시나리오 검증 결과 문서화 완료
- Monte Carlo Quick 80회 실측 완료
- 발표/검증/FAQ/로드맵 관련 문서 다수 생성 완료
- 논문 주제 초안 및 재현성 가이드 초안 작성 완료

### 아직 남은 핵심 공백

- CPU-default 전체 테스트 재검증과 API extra 설치 환경 검증은 2026-05-15 기준으로 다시 확인되었고, GPU 경로는 `SDACS_ENABLE_TORCH=1` opt-in 으로 분리되었다.
- 재현성 문서의 TODO와 canonical run 기준 정리는 여전히 잔존
- 비교 실험 및 평가 메트릭 정형화의 기준 문서와 재현성 실행 경로는 정리되었고, 이제 남은 일은 canonical hash와 CI 검증 고정이다.
- `airspace_manager`, 하드웨어 브릿지, 대형 파일 리팩터링은 본격 작업 전

---

## 2. 추진 목표

### 목표 A. 정합성 회복

외부 평가자나 협력자가 처음 보는 문서에서 숫자와 상태가 충돌하지 않도록 맞춘다.

### 목표 B. 논문화 트랙 현실화

이미 확정된 논문 프레임을 실제 제출 가능한 형태로 전진시킨다.

### 목표 C. 서비스화 준비

대시보드/백엔드 구조를 장기적으로 확장 가능한 방향으로 정리한다.

### 목표 D. 실기 연동 준비

실하드웨어가 없어도 먼저 가능한 설계, 인터페이스, 검증 스켈레톤을 준비한다.

---

## 3. 우선순위별 추가 작업

### P0. 이번 주 즉시 처리

| ID | 작업 | 산출물 | 담당 성격 | 완료 기준 |
|----|------|--------|----------|----------|
| P0-1 | CI 재실행 및 녹색 확인 | 실행 기록 또는 결과 문서 | 코드/검증 | 주요 테스트 파이프라인 성공 확인 |
| P0-2 | README 테스트 수치 수정 | `README.md` | 문서 | 최신 CPU-default 실측 기준 반영 |
| P0-3 | 검증 문서와 공개 문서 간 숫자 정리 | `docs/roadmap_public.md` 포함 관련 문서 | 문서 | 테스트 수, 검증 범위, Quick run 수치 일관화 |
| P0-4 | `apf_engine` fallback 회귀 방지 테스트 추가 | 신규 테스트 파일 | 코드/테스트 | torch 미설치 환경 회귀 방지 가능 |
| P0-5 | 변경 내용 로그화 | `CHANGELOG.md`, 회귀 노트 | 문서 | 이번 수정 사항이 추적 가능 |

### P1. 2주 내 처리

| ID | 작업 | 산출물 | 담당 성격 | 완료 기준 |
|----|------|--------|----------|----------|
| P1-1 | `SECURITY.md` 점검 및 보강 | 보안 문서 | 문서 | 최소 위협 모델, 제보 경로, 범위 명시 |
| P1-2 | `ops_report` Traffic RED 원인 분석 | 분석 메모 | 분석 | 원인, 재현 조건, 대응 방향 정리 |
| P1-3 | `weather_disturbance` 포함 smoke run 재기록 | 실행 로그/메모 | 검증 | 대표 시나리오 최소 재검증 완료 |
| P1-4 | 논문 메트릭 정형화(P705) | 메트릭 정의 문서/코드 | 연구/코드 | NMR, PE, RTF, RID-CR 계산 기준 고정 |
| P1-5 | 재현성 패키지 TODO 정리(P704) | `docs/REPRODUCIBILITY.md` 보강 | 연구/문서 | seeds, lockfile, canonical run 기준 명시 |
| P1-6 | 벤치마크 공개 범위 정리(P703) | `benchmarks/README.md` 또는 별도 문서 | 연구/문서 | 공개 가능한 시나리오/메타데이터 확정 |

### P2. 3~4주 내 처리

| ID | 작업 | 산출물 | 담당 성격 | 완료 기준 |
|----|------|--------|----------|----------|
| P2-1 | `api/fastapi_server.py` TODO 연결 | API 코드 정리 | 코드 | `airspace_manager` 연동 방향 확정 |
| P2-2 | `src/hardware/onboard_bridge.py` TODO 3건 정리 | 브릿지 스켈레톤 보강 | 코드/설계 | 메시지 핸들러 매핑 초안 완성 |
| P2-3 | `visualization/simulator_3d.py` 분해 설계 | 리팩터 계획 또는 PR | 아키텍처 | 모듈 분리 기준 확정 |
| P2-4 | `simulation/simulator.py` 역할 분리 설계 | 리팩터 계획 또는 PR | 아키텍처 | 드론 에이전트 분리 경계 정의 |
| P2-5 | `logger`/`print` 혼용 정리 | 코드 정리 | 코드 품질 | 핵심 모듈 logging 일원화 |
| P2-6 | 이미지 외부 의존 제거 | 로컬 자산 정리 | 배포/문서 | imgur 링크 대체 계획 수립 또는 일부 이전 |

### P3. 장기 트랙

| 트랙 | 범위 | 현재 판단 |
|------|------|----------|
| 실기 드론 통합 | P691-P700 | 하드웨어/시설 의존이 커서 설계 선행 후 착수 |
| 연구·논문화 | P701-P710 | 가장 먼저 밀어야 하는 핵심 트랙 |
| 배포·서비스화 | P711-P720 | 구조 설계는 가능, 본격 구현은 P0/P1 안정화 이후 |

---

## 4. 4주 실행 계획

### Week 1. 정합성 및 신뢰도 복구

- README, 공개 로드맵, 검증 문서의 수치 통일
- CI 재확인 및 회귀 테스트 추가
- 변경 로그와 회귀 노트 업데이트

**주간 완료 목표**
- 외부에 보여 주는 주요 문서에서 상충 수치 제거
- CPU-default 기준과 GPU opt-in 기준을 분리 표기

### Week 2. 논문화 기반 정리

- 메트릭 정의 확정
- 재현성 문서 TODO 정리
- 벤치마크 공개 범위와 실험 프로토콜 정리

**주간 완료 목표**
- 논문 실험을 반복 실행할 수 있는 최소 기준 확정
- 실험 재현 절차를 제3자가 읽고 따라갈 수 있는 수준으로 문서화

### Week 3. 서비스화/코드 구조 정리

- FastAPI TODO 처리 범위 확정
- 시뮬레이터/시각화 대형 파일 분리 설계
- logging 일원화 착수

**주간 완료 목표**
- 이후 React/FastAPI 리팩터링을 시작할 수 있는 구조 결정
- 큰 파일을 안전하게 나눌 설계 문서 또는 작은 선행 PR 확보

### Week 4. 하드웨어 연동 준비

- `onboard_bridge.py` TODO 정리
- MAVLink 메시지 흐름/핸들러 명세 초안 작성
- HITL 이전 단계 체크리스트 작성

**주간 완료 목표**
- 실기 장비가 들어오면 바로 붙일 수 있는 문서/코드 스켈레톤 확보

---

## 5. 권장 실행 순서

1. 문서 정합성 복구
2. CI 및 회귀 테스트 확정
3. 논문 메트릭/재현성 고정
4. FastAPI 및 시뮬레이터 구조 정리
5. 하드웨어 브릿지 설계 보강

이 순서를 권장하는 이유는, 현재 가장 큰 리스크가 "기능 부족"보다 "기록과 실제 상태의 불일치"이기 때문이다. 신뢰도를 먼저 복구해야 이후 논문, 배포, 실기 트랙이 모두 안정적으로 이어진다.

---

## 6. 외부 의존 및 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| torch/GPU 환경 | 테스트 수와 일부 모듈 실행 결과가 환경에 따라 달라짐 | CPU-only / torch 포함 기준 분리 표기 |
| 하드웨어 부재 | 실기 통합 작업이 문서 수준에서 멈출 수 있음 | 인터페이스 명세와 스켈레톤 선행 |
| 대형 파일 리팩터 | 기능 회귀 위험 | 작은 단위 분리와 테스트 우선 |
| 논문 일정 | 실험/도표/리뷰에 예상보다 시간 소요 | 메트릭과 재현성부터 먼저 고정 |

---

## 7. 완료 기준

다음 조건을 만족하면 이번 추가 계획의 1차 목표가 달성된 것으로 본다.

- README와 핵심 공개 문서의 수치가 2026-05-08 검증 결과와 일치한다.
- CI 상태와 회귀 테스트가 재확인되었다.
- 논문 메트릭 및 재현성 절차가 최소 제출 가능한 수준으로 정리되었다.
- FastAPI/시뮬레이터/하드웨어 브릿지의 다음 구현 단계를 시작할 기준 문서가 마련되었다.

---

## 8. 바로 실행할 체크리스트

- [x] `README.md` 테스트 수치 수정
- [x] `docs/roadmap_public.md` 수치 재검토
- [x] CI 재확인
- [x] `tests/test_apf_engine_fallback.py` 회귀 테스트 확인
- [x] `CHANGELOG.md` 업데이트
- [x] `docs/REPRODUCIBILITY.md` TODO 우선순위 정리
- [x] 논문 메트릭 문서 확정
- [x] `api/fastapi_server.py` 정식 백엔드 통합 및 호환 경로 정리
- [x] `src/hardware/onboard_bridge.py` 기능 공백 범위 점검

---

## 9. P1 진행 현황 (2026-05-18 업데이트)

| ID | 상태 | 산출물 / 메모 |
| -- | ---- | ------------- |
| P1-1 | ✅ 완료 | `SECURITY.md` 위협 모델, 자산별 in-scope/out-of-scope, 응답 SLA, 데이터 처리 범위 추가 |
| P1-2 | ✅ 완료 (기존) | `docs/OPS_TRAFFIC_RED_ANALYSIS_2026-05-03.md` |
| P1-3 | ✅ 완료 | `docs/WEATHER_DISTURBANCE_SMOKE_2026-05-18.md` — seed=42, 1회, 67.6s wall-clock, 99.38% resolution rate |
| P1-4 | ✅ 완료 | `docs/paper/EVALUATION_METRICS.md` §9에 10개 시나리오 모두 `d_safe=5 m` 결정 기록 |
| P1-5 | 🟡 부분 완료 | `config/canonical_hashes.yaml` (3 cells, pending), `scripts/reproduce/verify_canonical_hashes.py`, `.github/workflows/canonical_hash.yml` 도입. 실측 SHA pin은 reference hardware 캡처 대기 |
| P1-6 | ✅ 완료 (기존) | `benchmarks/README.md` |

### P1-5 남은 작업

CI 잡과 매니페스트 스켈레톤은 들어갔지만, 실제 reference hardware
(`sdacs-repro:0.1.0`)에서 캐노니컬 SHA를 캡처해서 `config/canonical_hashes.yaml`
의 3개 cell을 `status: pinned`로 바꾸는 일이 남았다. 캡처 명령은
`python scripts/reproduce/verify_canonical_hashes.py --capture`.

---

---

## 10. P2 진행 현황 (2026-05-18 업데이트)

| ID | 상태 | 산출물 / 메모 |
| -- | ---- | ------------- |
| P2-1 | ✅ 완료 | `api/fastapi_server.py` — 더미 sleep/하드코드 제거, `_live_airspace_stats()` 스텁으로 `AirspaceGrid.get_statistics()` 실제 연결 |
| P2-2 | ✅ 완료 | `src/hardware/onboard_bridge.py` — (1) 클래스 레벨 mutable state 버그 수정 → 인스턴스 레벨로 이동, (2) Remote-ID 브로드캐스트 스켈레톤 `_broadcast_remote_id()` 추가, (3) 텔레메트리 루프 런타임 오류 시 backoff 재시도 로직 추가 |
| P2-3 | ✅ 완료 | `docs/REFACTOR_DESIGN_2026-05-18.md` — `visualization/simulator_3d.py` 5-모듈 분리 계획 (1,769 lines → ~330 lines 5개 파일) |
| P2-4 | ✅ 완료 | 동 문서 — `simulation/simulator.py` `_DroneAgent` → `simulation/drone_agent.py` 분리 계획 |
| P2-5 | ✅ 완료 (변경 없음) | 핵심 모듈 분석 결과 이미 올바른 패턴: `src/` 전체 print 없음, 주변 simulation 모듈 prints는 전부 `__main__` 블록 |
| P2-6 | ✅ 완료 | `docs/images/imgur/*.png` → `docs/images/*.png` 기술적 이름으로 복사 + `README.md` 12개 참조 교체. 외부 imgur.com URL 없었음 (이미 로컬 저장 완료 상태였음) |

### P2 남은 실제 코드 작업 (P3 전환 전)

`docs/REFACTOR_DESIGN_2026-05-18.md`에 명시된 분리 PR 5건은 설계 문서만 완성된 상태다. 실제 파일 분리는 각 PR 단위로 진행하며, PR 전 반드시 `pytest tests/ -v`가 2,823+ 기준 통과 확인 필요.

---

*Last updated: 2026-05-18*
