# 🧭 SDACS ODYSSEY Plan — Phase 401-500 초대규모 신규 계획

*Created: 2026-06-12 — GENESIS Phase 302(SORA)·388(부채 대장) 선행 착수 직후*

> **철학 전환 3단계**: TRANSCENDENCE(201-300)는 *"이것은 진짜인가"*, GENESIS(301-400)는 *"이것은 세상에 남는가"* 에 답한다.
> ODYSSEY(401-500)는 **"이것은 국경과 세대를 넘는가"** 에 답한다 — 국제 표준에 기고하고,
> 다중 운영자가 연합하고, 형식적으로 검증되고, 10년 뒤에도 빌드되는 시스템.

---

## 📊 시작점 (2026-06-12 실측 기준선)

| 지표 | 값 | 출처 |
|---|:-:|---|
| `_sdacs` API | 404 (분류 404 = 90/98/110/103 + 헬퍼 3) | `scripts/extract_sdacs_api.py` 라이브 실측 |
| 종합 자동 검증 | 4,443 pass / 9 skip / 0 fail | 회귀 4,180 + E2E 263 |
| 선행 계획 | GENESIS 301-400 (2% — 302·388 완료) | [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) |
| 기술 부채 공시 | mock 110 + speculative 103 = 213 | [`TECH_DEBT_LEDGER.md`](TECH_DEBT_LEDGER.md) |

**전제**: ODYSSEY는 GENESIS Track 🏭(인증)·🌍(생태계) 1차 완료 후 본격 착수. 🔬 형식 검증·🏛 표준 조사는 즉시 병행 가능.

---

## 🎯 5대 ODYSSEY 트랙 (각 20 Phase)

### Track 🌏 — Global Expansion (Phase 401-420) · 국제 확장

*K-UTM 정렬을 넘어 EASA U-space·FAA UTM 3대 체계 동시 호환. 기존 자산: `src/utm/`(LAANC·ICAO), GENESIS 🏭*

- **Phase 401** EASA U-space U1-U4 서비스 매핑 — SDACS 기능 ↔ U-space 서비스 매트릭스
- **Phase 402** FAA UTM ConOps v2 정렬 — USS 역할 요건 갭 분석
- **Phase 403** `_sdacs.soraAssess()` EASA Open/Specific/Certified 카테고리 판정 확장
- **Phase 404** README·핵심 문서 EN 완역 (GENESIS 328 연계, 학술 인용 가능 수준)
- **Phase 405** 국제 벤치마크 제출 — BlueSky·U-TRAFMAN 비교 시나리오 공개
- **Phase 406** 다국 좌표계·시간대 지원 (UTM zone 자동 판정)
- **Phase 407** ICAO UTM Framework Ed.4 적합성 자가 평가
- **Phase 408** 국제 공역 분류(A-G) 모델 — 현 9층 고도 레이어에 클래스 매핑
- **Phase 409** 다국 규제 비교 대시보드 (한·미·EU·일 BVLOS 요건)
- **Phase 410** GUTMA 회원 활동 시나리오 — 글로벌 UTM 커뮤니티 기고
- **Phase 411-420** 해외 파일럿 제안서 3종 (아세안 도서 배송·EU U-space 데모·미국 대학 연구 협력)

### Track 🛰 — Federation Operations (Phase 421-440) · 연합 운영

*단일 SDACS → 다중 인스턴스 연합 (inter-USS). 기존 자산: TRANSCENDENCE 241-260 다중 사용자, Raft HA, ws_bridge*

- **Phase 421** ✅ 인스턴스 간 디스커버리 프로토콜 — `docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md` (ASTM F3548 DSS·8 메시지 유형·핸드오버·mTLS+JWT) (2026-06-17)
- **Phase 422** 운영 의도(Operational Intent) 교환 포맷 — 4D 볼륨 직렬화
- **Phase 423** 지역 간 핸드오버 — 드론이 인스턴스 경계 통과 시 관제권 이양
- **Phase 424** 연합 충돌 해소 — 인스턴스 간 우선순위 협상 (Vickrey 경매 재사용)
- **Phase 425** 연합 NOTAM 전파 — 동적 NFZ를 인접 인스턴스에 브로드캐스트
- **Phase 426** 2-인스턴스 연합 E2E (Playwright 다중 페이지 + ws 브리지 2개)
- **Phase 427** 연합 시각화 — 인접 공역 고스트 렌더링
- **Phase 428** 신뢰 모델 — 인스턴스 간 Bayesian 평판 (기존 reputation 재사용)
- **Phase 429** 연합 감사 로그 — 관제권 이양 불변 기록
- **Phase 430** 분할 뇌(split-brain) 시나리오 — 연합 단절 시 안전 강하 정책
- **Phase 431-440** 3+ 인스턴스 메시 연합 + 글로벌 시계(hybrid logical clock)

### Track 🔬 — Formal & Research Frontier (Phase 441-460) · 형식 검증·연구 개척

*테스트를 넘어 증명으로. 기존 자산: OCaml 타입 체커, Rust safety verifier, Prolog 규칙*

- **Phase 441** 5계층 안전망 TLA+ 명세 — 충돌 회피 우선순위 불변식
- **Phase 442** 모델 체킹 — TLC로 ATC 핸드오프 데드락 부재 증명
- **Phase 443** APF 수렴성 수학 증명 문서화 (Lyapunov 후보 함수)
- **Phase 444** CBS 완전성·최적성 조건 정리 (논문 §보강)
- **Phase 445** 불확실성 정량화 — Monte Carlo 신뢰구간 자동 리포트
- **Phase 446** 충돌 해결률 공식의 통계적 검정력 분석
- **Phase 447** 적대적 시나리오 fuzzing — 시드 기반 시나리오 변이 생성기
- **Phase 448** 속성 기반 테스트(Hypothesis) — 시뮬 코어 불변식 1,000케이스
- **Phase 449** 시뮬-실측 갭 모델 — DR 파라미터 보정 자동화
- **Phase 450** 재현성 10년 보장 — 의존성 핀 + 컨테이너 다이제스트 고정
- **Phase 451-460** RL 일반화 연구 (미학습 시나리오 전이) + 인증 가능 ML 조사 (EASA AI Roadmap)

### Track 🏛 — Standards & Policy (Phase 461-480) · 표준·정책 기여

*사용자에서 기여자로. 기존 자산: K-UTM 모듈, GENESIS 인증 트랙, IROS 논문*

- **Phase 461** ASTM F38 위원회 기고 초안 — 군집 관제 시험 방법 제안
- **Phase 462** ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스
- **Phase 463** K-드론 시스템 고도화 정책 제안서 (국토부 제출 형식)
- **Phase 464** 군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구
- **Phase 465** 공역 통합 시뮬레이션 표준 시나리오 셋 제안 (10종 공개)
- **Phase 466** 오픈 데이터 표준 — 텔레메트리 스키마 공개 (JSON Schema + 검증기)
- **Phase 467** 사고 조사 데이터 표준 — 시뮬 로그 → 표준 양식 변환기
- **Phase 468** 대학 캡스톤 표준 커리큘럼 제안 (GENESIS 383 확장)
- **Phase 469** 정책 영향 시뮬레이션 — 규제 파라미터(고도 상한·이격 거리) 변경 효과 자동 비교
- **Phase 470** 표준화 기고 추적 대시보드
- **Phase 471-480** 국내 표준(KS) 제안 1건 + 국제 워킹그룹 의견서 3건

### Track ♾️ — Continuum (Phase 481-500) · 10년 지속 가능성

*졸업 후 10년. 기존 자산: GENESIS 🎓 레거시 트랙, 재현성 패키지*

- **Phase 481** 의존성 자동 갱신 파이프라인 — Dependabot + 회귀 게이트 자동 머지 정책
- **Phase 482** 브라우저 API 폐기 감시 — WebGPU/WebXR 스펙 변경 카나리 테스트
- **Phase 483** Three.js 메이저 업그레이드 리허설 (r162 → 최신) + 호환 셰임
- **Phase 484** Electron LTS 추적 정책 (현 32→39 교훈 문서화)
- **Phase 485** 데이터 마이그레이션 도구 — 시나리오/미션 포맷 버전 변환기
- **Phase 486** 연 1회 건전성 리허설 자동화 — 신규 컨테이너 독립 재현 스크립트
- **Phase 487** 거버넌스 문서 — 유지보수자 승계 규약 (BDFL → 위원회)
- **Phase 488** 보안 장기 지원 — CVE 대응 SLA + 핀 갱신 절차
- **Phase 489** 아카이브 이중화 — Zenodo + Software Heritage + 대학 리포지터리
- **Phase 490** 디지털 유산 선언 — 10년 후 재현 가능성 체크리스트
- **Phase 491-499** 차세대(2027+ 기수) 주도 신규 트랙 공모·선정·이양
- **Phase 500** **= SDACS Centennial 선언** — Phase 1-500 통합 회고 + 영구 아카이브 동결

---

## 🎯 우선순위 매트릭스 (즉시 착수 가능 Top 8)

| Phase | 트랙 | 임팩트 | 난이도 | sandbox 가능 |
|---|---|:-:|:-:|:-:|
| 403 SORA 카테고리 확장 | 🌏 | 🔥🔥🔥🔥 | ⭐⭐ | ✅ (302 위에) |
| 408 공역 클래스 매핑 | 🌏 | 🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 447 시나리오 fuzzing | 🔬 | 🔥🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 448 속성 기반 테스트 | 🔬 | 🔥🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 466 텔레메트리 JSON Schema | 🏛 | 🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 469 정책 영향 시뮬 | 🏛 | 🔥🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 486 독립 재현 자동화 | ♾️ | 🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 421 디스커버리 프로토콜 | 🛰 | 🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |

**권장 즉시 착수**: Phase 448(속성 기반 테스트)·447(fuzzing) — 기존 4,443 검증 자산을 증명 수준으로 격상, 전부 sandbox 가능.

---

## 📈 누적 KPI 목표 (ODYSSEY)

| 지표 | Phase 400 (목표) | Phase 440 | Phase 480 | Phase 500 |
|---|:-:|:-:|:-:|:-:|
| 형식 명세 커버 불변식 | 0 | 5 | 12 | 20 |
| 연합 인스턴스 | 1 | 2 | 3+ | 메시 |
| 표준 기고 | 0 | 1 | 4 | 6 |
| 속성 테스트 케이스 | 0 | 1,000 | 5,000 | 10,000 |
| 재현 보장 연한 | 1년 | 3년 | 5년 | 10년 |

## 🔁 거버넌스 (ODYSSEY 추가 게이트)

GENESIS 게이트(규제 정합·하위 호환·실증 안전·교육 검증)에 추가:

1. **증명 우선**: 안전 불변식 변경은 TLA+ 명세 갱신 동반
2. **연합 호환**: 인스턴스 간 프로토콜은 버전 협상 필수
3. **표준 인용**: 기고 문서는 대상 표준 문서 번호·개정판 명시
4. **세대 이양**: 491+ 신규 트랙은 차세대 주도, 현 세대는 리뷰만

## 🗺 전체 Phase 지도 (1-500)

| 구간 | 계획 | 상태 |
|---|---|:-:|
| 1-10 MEGA ~ 151-200 POST-UNIVERSE | 5개 계획 문서 | ✅ 𝟏 Unity |
| 201-300 TRANSCENDENCE | [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) | 🟡 8% (201-203·206-208) |
| 301-400 GENESIS | [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) | 🟡 2% (302·388) |
| **401-500 ODYSSEY** | **본 문서** | ⬜ 수립 완료 |
| 실행 일정 | [`MASTER_PLAN_2026H2.md`](MASTER_PLAN_2026H2.md) | 🟢 가동 |
