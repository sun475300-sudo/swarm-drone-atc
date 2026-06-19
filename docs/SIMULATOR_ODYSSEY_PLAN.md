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

- **Phase 401** ✅ EASA U-space U1-U4 서비스 매핑 — SDACS 기능 ↔ U-space 서비스 매트릭스 (2026-06-17, `simulation/uspace_service_map.py` — EASA U-space 서비스(EU 2021/664 + CORUS ConOps U1-U4)를 SDACS 기능에 결정적으로 대응시키는 정합성 매트릭스. `USpaceService` frozen dataclass 14종 카탈로그가 각 서비스의 도입 레벨(U1-U4)·EU 의무 여부·**실재하는 리포 모듈 경로**(`sdacs_module`)를 보유 — 대응 모듈이 없는 U4 유인 항공 통합은 `None` 으로 **갭** 을 정직 표면화(`test_cited_modules_exist_on_disk` 가 12개 인용 경로의 디스크 실재를 강제). EU 2021/664 의무 4종(network identification·geo-awareness·UAS flight authorisation·traffic information)은 100% 충족(4/4)임을 `coverage_report()` 가 결정적 집계. 조회 API `services_by_level`·`mandatory_services`·`gaps`·`service_matrix`(도구 간 교환용 JSON 행)·`find_service`, `CoverageReport`(frozen, `__post_init__` 카운트 불변식 검증·`by_level` MappingProxyType 읽기 전용). 무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--matrix`·`--coverage`·`--level`·`--gaps`·`--mandatory`). code-reviewer 어드바이저 HIGH 2(by_level 가변 dict→MappingProxyType·CoverageReport 무검증 생성자→불변식)·MEDIUM 3(is_mandatory_complete 공허참·service_id 패딩·summary 빈문자) 반영. 단위 37건 PASS)
- **Phase 402** FAA UTM ConOps v2 정렬 — USS 역할 요건 갭 분석
- **Phase 403** `_sdacs.soraAssess()` EASA Open/Specific/Certified 카테고리 판정 확장
- **Phase 404** README·핵심 문서 EN 완역 (GENESIS 328 연계, 학술 인용 가능 수준)
- **Phase 405** 국제 벤치마크 제출 — BlueSky·U-TRAFMAN 비교 시나리오 공개
- **Phase 406** ✅ 다국 좌표계·시간대 지원 (UTM zone 자동 판정) (`simulation/geo_zones.py` — 전 세계 위·경도를 UTM 그리드 존(존 번호·MGRS 위도 밴드·EPSG·공칭 시간대)으로 결정적 변환. 극지(±80° 밖) 거부, Norway/Svalbard 특례 처리. 코드·테스트 main 적재 완료(추적 정정 시 39건 PASS 재검증), 2026-06-17)
- **Phase 407** ICAO UTM Framework Ed.4 적합성 자가 평가
- **Phase 408** ✅ 국제 공역 분류(A-G) 모델 — 현 9층 고도 레이어에 클래스 매핑 (`simulation/airspace_class.py` + `docs/certification/AIRSPACE_CLASS_MAPPING.md` — 고도(m AGL)와 선택적 좌표·NFZ 로부터 ICAO 공역 클래스(B·D·E·G·R)를 결정적으로 산정하는 `classify_airspace` API. SDACS 9층 고도 레이어(0~240m) 매핑 + 군 작전/공항 NFZ 판정(haversine)·특별승인 분기·클래스별 SDACS 충족 요건. `AirspaceClassification`·`NoFlyZone` frozen dataclass, 무작위성 0. 코드·테스트 main 적재 완료(추적 정정 시 25건 PASS 재검증), 2026-06-17)
- **Phase 409** ✅ 다국 규제 비교 대시보드 (한·미·EU·일 BVLOS 요건) — `simulation/bvlos_regulation_compare.py` + `docs/certification/BVLOS_REGULATION_COMPARISON.md` (2026-06-19, GENESIS 302 SORA·408 공역클래스·`faa_laanc`·`icao_doc10019` 가 *단일 관할권* 적합성을 다룬 반면 본 Phase 는 KR/US/EU/JP 4개 관할권 BVLOS 운영 요건을 **횡단 비교**. 각 관할권을 `BvlosRegulation` frozen dataclass 로 모델링 — 규제 프레임워크(KR 항공안전법 §129·US Part 107/108·EU 2019/947 SORA·JP 改正航空法 Level 4)·승인방식·조종자/기체 인증·Remote ID·DAA·보험·기본 고도상한·사람 위 비행 9개 비교 필드. `compare_field`·`comparison_matrix`(결정적·삽입순서 보존)·`assess_conformance(profile, code)`/`assess_all`(SDACS `OperationProfile` ↔ 관할권 요건 갭 산정, 관할권 차이 반영 — 예: 보험 미가입은 KR/EU/JP 갭·US 적합, 고도 130m 는 EU/US 초과·KR/JP 적합)·`to_markdown_table`(대시보드 피드)·`to_dict`(JSON export). 난수·외부호출 0, 교육·시뮬레이션용 스냅샷 모델 면책 명시. code-reviewer 어드바이저 반영, 단위 19건 PASS)
- **Phase 410** GUTMA 회원 활동 시나리오 — 글로벌 UTM 커뮤니티 기고
- **Phase 411-420** 해외 파일럿 제안서 3종 (아세안 도서 배송·EU U-space 데모·미국 대학 연구 협력)

### Track 🛰 — Federation Operations (Phase 421-440) · 연합 운영

*단일 SDACS → 다중 인스턴스 연합 (inter-USS). 기존 자산: TRANSCENDENCE 241-260 다중 사용자, Raft HA, ws_bridge*

- **Phase 421** ✅ 인스턴스 간 디스커버리 프로토콜 — ASTM F3548 DSS 유사 결정적 모델 (`simulation/federation_discovery.py` + `docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md`, 13건 PASS, 2026-06-18)
- **Phase 422** ✅ 운영 의도(Operational Intent) 교환 포맷 — 4D 볼륨 직렬화 (`simulation/operational_intent.py` + `docs/certification/OPERATIONAL_INTENT_FORMAT.md` — ASTM F3548-21 정렬 `Volume4D`/`OperationalIntent` frozen dataclass + 라운드트립 직렬화 + 보수적 4D 교차 판정, 단위 24건, 2026-06-18)
- **Phase 423** ✅ 지역 간 핸드오버 — 드론이 인스턴스 경계 통과 시 관제권 이양 (2026-06-15, `simulation/federation_handover.py` — Phase 421 점 커버리지 기반 `HandoverCoordinator`. 위치 표본마다 RETAINED/ACQUIRED/HANDOVER/CONTINGENT 결정, 중첩 구역 이력현상(hysteresis), 반열린 경계 규약, 불변 감사 로그(Phase 429 기반). 단위 16건)
- **Phase 424** ✅ 연합 충돌 해소 — 인스턴스 간 우선순위 협상 (2026-06-15, `simulation/federation_conflict_resolution.py` — Phase 422 `intents_conflict` 로 충돌 탐지 후 Phase 602 `VickreyAuction`(2위 가격제) 재사용. 우선순위→입찰가 결정적 사상(낮은 priority=높은 입찰), 동률은 `sha256(intent_id)` 안정 해시로 분리. `resolve_all` 쌍별 협상 + `apply_resolutions` 패자 CONTINGENT 불변 전환 + 불변 감사 로그. 단위 11건)
- **Phase 425** ✅ 연합 NOTAM 전파 — 동적 NFZ를 인접 인스턴스에 브로드캐스트 (2026-06-15, `simulation/federation_notam.py` — `FederationNotamBroadcaster`. Phase 421 디스커버리 `query` 로 겹치는 이웃만 선별해 결정적 전파(DELIVERED/DUPLICATE/REVOKED), NFZ 이동 시 더는 겹치지 않는 이웃에서 stale 자동 회수, 멱등 재방송(`rebroadcast`)·철회(`revoke`), 소비측 `active_volumes` 헬퍼, 불변 감사 로그. 단위 19건)
- **Phase 426** 2-인스턴스 연합 E2E (Playwright 다중 페이지 + ws 브리지 2개)
- **Phase 427** 연합 시각화 — 인접 공역 고스트 렌더링
- **Phase 428** ✅ 신뢰 모델 — 인스턴스 간 Bayesian 평판 (2026-06-15, `simulation/federation_trust.py` — Phase 608 `BayesianReputation` 의 Beta-Bernoulli 켤레 사전분포를 인스턴스 레벨로 재사용. `InstanceTrust` frozen dataclass 가 (관찰자→대상) 방향성 Beta(α,β) 믿음을 보유하고 `updated` 는 원본 불변 갱신본 반환. 핸드오버(Phase 423)·충돌 협상(Phase 424)·NOTAM 전파(Phase 425) 협조 이벤트를 `observe` 로 관찰해 성공→α·실패→β 누적. 사후 평균 `trust_score` + Beta 표준편차 `uncertainty`, `is_trusted` 는 임계값·최소 관찰(Phase 608 과 동일한 증거 게이트) 통과 요구, `untrusted` 는 저신뢰 쌍 결정적 정렬 반환. 무작위성 0·방향 비대칭·불변 감사 로그. code-reviewer 어드바이저 HIGH 3건 반영(식별자 strip 정규화로 공백 중복 슬롯 방지·`InstanceTrust.__post_init__` 불변식 검증·모델 상태성 docstring 명확화). 단위 30건)
- **Phase 429** ✅ 연합 감사 로그 — 인스턴스 경계 넘는 변조 탐지 원장 (2026-06-15, `simulation/federation_audit.py` — `FederationAuditLog` append-only SHA-256 해시 체인. 각 항목이 직전 다이제스트를 재료에 포함(길이 접두 직렬화로 구분자 주입·다이제스트 충돌 구조적 차단)해 중간 변조·삭제를 `verify()` 가 검출. 인스턴스별 단조 논리시계, 인스턴스/이벤트 쿼리. 두 인스턴스 원장은 내용 키 `(logical_clock, instance_id, event_type, detail)` 사전식 전순서로 중복 제거 후 재-체인하는 결정적 CRDT 류 `merge` — 교환·결합·흡수 멱등이라 어느 순서로 합쳐도 같은 head 다이제스트. 분기(fork)된 같은 인스턴스 항목도 보존. 단위 29건)
- **Phase 430** ✅ 분할 뇌(split-brain) 시나리오 — 연합 단절 시 안전 강하 정책 (2026-06-15, `simulation/federation_split_brain.py` — `PartitionSnapshot` 양방향 링크를 연결 요소로 분해해 과반(majority) 분파 판정 + `SafeDescentPolicy` 4단계 안전 사다리 NOMINAL/HOLD/DESCEND/LAND. 고립·커버리지 상실 지속 시 단계 상승, 정상 복귀 시 이력현상 초기화, 불변 감사 로그. Phase 423이 미룬 안전 강하 책임 구체화. 단위 20건)
- **Phase 431** ✅ 하이브리드 논리 시계(HLC) — 글로벌 시계 (2026-06-15, `simulation/federation_hybrid_clock.py` — Kulkarni et al. 2014 표준 HLC. `HLCTimestamp`(frozen, `order=True` 전순서)는 `(wall_time, counter, instance_id)` 로 결정적 정렬되고 `causal_key`·`happened_before`·`is_concurrent_with` 로 인과/동시성을 명시한다. `HybridLogicalClock.local_event`/`receive_event` 가 표준 HLC 갱신 규칙(물리 시각·지역 고점·원격 wall 의 최댓값 + 출처별 counter 결정)을 적용해, 물리 시계 동기화 없이 happened-before → 사전식 증가를 보장한다. 물리 시계 역행을 견디고(논리 고점 유지·counter 증가), cold-start sentinel(-1)로 첫 타임스탬프 counter 를 0으로 정규화. code-reviewer 어드바이저 반영(CRITICAL cold-start 모호성 -1 sentinel 해소·HIGH happened_before 부분순서/동시성 문서화 + `is_concurrent_with` 추가·cold-start receive 테스트 보강). 무작위성 0·결정적. 단위 34건)
- **Phase 432** ✅ 메시 연합 토폴로지 + 멀티홉 전파 (2026-06-15, `simulation/federation_mesh.py` — Phase 421 디스커버리 등록 상태로 공역 경계 인접 그래프를 결정적으로 구성. 타일형(비중첩) 공역도 수평(x·y) `border_tolerance_m` 이내 접촉을 이웃으로 인식하고 수직(z)·시간(t)은 엄격 4D 교차로 분리 — Phase 425 `overlaps`(엄격)가 맞닿은 타일을 비이웃으로 보는 한계 보완. 연결 요소(`components`)·연결성(`is_connected`)·동률을 정렬 이웃으로 분리하는 BFS 최단 경로(`shortest_path`) + Phase 425의 1홉 직접 전파를 메시 전역으로 일반화한 TTL 한정 멀티홉 전파(`propagate`)·중계 포워딩 테이블(`relay_table`). 디스커버리에 공개 접근자 `volume_of` 1개 추가(타일 경계 기하 직접 산정용). 단위 25건)
- **Phase 433** ✅ 신뢰 가중 메시 라우팅 (2026-06-16, `simulation/federation_trust_routing.py` — Phase 432 메시 토폴로지 위에서 Phase 428 신뢰 모델로 각 중계 후보 비용을 가중하는 결정적 최소 비용 라우터 `TrustWeightedRouter`. 간선 비용 `hop_cost + untrust_weight*(1 - trust(origin→node))` 로 신뢰하는 이웃을 우선하고, 라우팅은 항상 origin 자신의 신뢰 믿음으로 결정(연합은 중앙 신뢰 권위 없음 → 같은 토폴로지라도 인스턴스마다 다른 경로 가능). `route`(사전식 동률 분리 Dijkstra)·`route_cost`·`avoid_untrusted_route`(충분히 관찰된 불신 중계 회피 BFS, 목적지는 종단점이라 허용)·`forwarding_table`(목적지→다음 홉)·`relay_trust`. 우선순위 큐는 `(비용, 경로 튜플)` 키로 노드 첫 확정 시 최소 비용·사전식 최소 경로를 고정하고, 사전식으로 엄격히 나은 후보만 push 해 동률 경로 큐 증식 방지. 무작위성 0·기존 모듈 무수정 순수 추가. code-reviewer 어드바이저 반영(HIGH 동률 경로 큐 증식 → best-path 사전식 완화로 차단·사설 상수 import 제거 후 로컬 정의; MEDIUM trust_threshold (0,1) 범위 검증·float 동률 분리 한계 docstring 명시). 단위 37건)
- **Phase 434** ✅ HLC 통합 인과-안정 배달 (2026-06-16, `simulation/federation_causal_delivery.py` — Phase 432 메시 전파 위에 Phase 431 HLC 를 결합한 워터마크(low-water-mark) 안정 배달. CockroachDB closed-timestamp 발상: 각 출처가 FIFO 로 단조 증가하는 HLC 를 발행하므로 알려진 모든 출처 고점의 최소(워터마크) 이하 사건은 안정 — 더 앞선 사건이 미래에 도착 불가. `FederationEvent`(HLC+불투명 페이로드)·`CausalDeliveryBuffer`(출처별 FIFO 중복 멱등 무시·예상 출처 보수 워터마크 vs 관측 best-effort·HLC 전순서 안정 배달·buffer_size 로 빔/보류 구분)·`FederationDeliveryCoordinator`(메시 `propagate` 로 origin 사건을 도달 인스턴스 버퍼에 멱등 fan-out, 스냅샷 모델). 멀티홉 중복·인스턴스별 사건 순서 불일치 해소. 무작위성 0·결정적. code-reviewer 어드바이저 반영(HIGH `flush` 객체 식별자 제거→워터마크 직접 분할로 비해시 페이로드 안전·재배달 차단, buffer_size 접근자 추가, 코디네이터 스냅샷 의미 문서화). 단위 36건)
- **Phase 435** ✅ 메시 복원력 라우팅 — 절단점·브리지 + 백업 경로 (2026-06-16, `simulation/federation_resilient_routing.py` — Phase 432 `FederationMesh` 스냅샷 위에서 인스턴스(USS) 장애 내성을 구조적으로 분석. `FederationResilientRouting` 가 Hopcroft-Tarjan `disc`/`low` 반복 DFS(재귀 한계 회피·정렬 순회로 결정성) 1회로 **절단점**(제거 시 연결 요소가 늘어나는 단일 장애점)과 **브리지**(제거 시 단절되는 단일 링크 인접)를 동시 식별한다. `backup_path(src,dst)` 는 메시 주 최단 경로의 *내부 노드·연속 간선*을 그래프에서 제거한 뒤 재-BFS 해, 주 경로의 어떤 중계가 죽어도 영향 없는(엔드포인트만 공유) 이중화 경로 존재 여부를 답한다. `surviving_reach(origin, failed)` 는 임의 장애 인스턴스 집합 제거 후 origin에서 여전히 닿는 인스턴스·홉 수를 BFS로 계산. Phase 430(분할 뇌)이 *분단 발생 후* 안전 강하를 다룬다면 본 모듈은 *분단을 일으킬 구조적 취약점을 사전에* 드러낸다. 무작위성 0·정렬 출력·읽기 전용. Phase 432·433·434와 비경쟁(신규 파일만 추가). 단위 31건)
- **Phase 436** ✅ 분산 경로-벡터 라우팅 (2026-06-16, `simulation/federation_path_vector.py` — `PathVectorRouting`. Phase 432 메시 인접만으로, 각 인스턴스가 직접 이웃만 알고 도달성을 광고·교환해 먼 목적지 경로를 분산 학습한다 — 전역 스냅샷을 보는 Phase 432 BFS·Phase 433 Dijkstra의 *지역 지식* 대응물. 광고 경로에 자신이 들어 있으면 거부하는 path-vector 루프 방지(BGP AS-PATH 발상), Jacobi(동기) 라운드가 직전 스냅샷만 참조해 갱신 순서와 무관한 결정적 수렴(라운드 수 = 메시 지름), 동률 경로 사전식 분리. 수렴 홉 거리가 Phase 432 중앙 BFS와 일치함을 핵심 불변식으로 검증. 단위 23건)
- **Phase 437** ✅ 신뢰 인지 분산 경로-벡터 라우팅 (2026-06-16, `simulation/federation_trust_path_vector.py` — `TrustPathVectorRouting`. Phase 436 분산 경로-벡터(홉만)와 Phase 433 중앙 신뢰 Dijkstra의 공백을 메운다: Phase 432 메시 인접 위에서 분산 수렴하되, 각 노드가 광고된 경로를 고를 때 *자신이 직접 관찰한 다음 홉 이웃의 신뢰도*(Phase 428)를 1순위 선호로 적용한다(BGP LOCAL_PREF). 경로 나머지 신뢰는 그 구간을 고른 하류 노드들이 각자의 로컬 신뢰로 반영하므로, 한 경로의 신뢰 결정은 홉마다 분산 합성된다 — 중앙식 433과의 핵심 차이. 선호 키 `(untrust_penalty(node→next_hop), 홉 수, 경로)`, 신뢰 동률(관찰 0 → 균일 0.5)이면 키가 (상수,홉,경로)로 환원되어 **Phase 436과 정확히 동일한 경로**, 신뢰는 재배열만 할 뿐 후보를 제거하지 않아 도달성은 메시와 동일. next-hop 에만 의존하는 local-pref 라 BGP 류 진동 없이 결정적 수렴(라운드 상한 = 노드 수는 방어적 종결 캡). code-reviewer 어드바이저 HIGH 2건 반영(수렴 라운드 상한을 정리가 아닌 방어적 캡으로 정확 기술·float 동률 분리의 정수 prior 의존성 명시). 단위 19건)
- **Phase 438** ✅ 분산 경로-벡터 장애 우회 수렴 (2026-06-16, `simulation/federation_path_vector_failover.py` — `PathVectorFailover`. Phase 436/437 이 *고정* 메시 위 1회 수렴을, Phase 435 가 단일 장애점·백업 경로를 *중앙 구조 분석*으로 다룬다면, 본 모듈은 그 공백 — **인스턴스(USS) 장애 후 분산 경로-벡터가 어떻게 재수렴하고 어느 경로가 우회/단절되는지** — 를 메운다. 장애 집합을 메시에서 제거한 살아남은 인접 위에서 Phase 436 수렴을 다시 돌려(죽은 노드 경유 광고 소멸 → 이웃 대체 경로 재광고를 모사) 장애 전후를 비교: `rerouted`(전후 모두 도달하나 경로 변경)·`lost_routes`(전엔 닿았으나 후엔 단절)·`is_reroutable`·`surviving_path`·`reconvergence_rounds`·`summary`. 경로-벡터는 전체 경로 광고라 count-to-infinity 가 없어 재수렴 결과 = 살아남은 메시 콜드스타트 고정점이며, 이를 Phase 436 인접 어댑터로 무수정 재사용해 계산한다. Phase 435 와 교차 검증(백업 경로 존재 ⇒ 주 경로 내부 중계 전멸에도 우회 생존, 절단점 장애 ⇒ 일부 쌍 단절). 무작위성 0·정렬 출력·기존 모듈 무수정 순수 추가. code-reviewer 어드바이저 반영(HIGH 2건: `summary` `lost_pairs` 를 죽은 origin 단절까지 전 origin 집계·`is_reroutable` 자기경로 False 가드; MEDIUM 교차검증 테스트를 경로 동일성 대신 도달성·길이로 완화, type-ignore→assert). 단위 22건)
- **Phase 439** ✅ 신뢰 한정 도달성 통합 토폴로지 — 3+ 인스턴스 (2026-06-16, `simulation/federation_topology_view.py` — `FederationTopologyView`. Phase 432 메시 *연결성* 과 Phase 428 *신뢰* 를 합쳐, 한 origin 관점에서 연합 내 모든 목적지를 도달성 *품질*로 분류하는 읽기 전용 관측 뷰(SELF·DIRECT·RELAYED_TRUSTED·RELAYED_RISKY·UNREACHABLE). Phase 433 `TrustWeightedRouter` 가 *가장 싼 신뢰 가중 경로 하나* 를 고른다면, 본 모듈은 **신뢰할 수 있는 중계만 거치는 경로가 존재하는가** (존재성 ≠ 최소 비용) 를 답한다 — 중계가 끼어드는 3+ 인스턴스에서만 의미가 생기는 질문. Phase 433 `avoid_untrusted_route` 가 *알려진 불신* 만 회피(무죄 추정)하는 반면 본 모듈의 `trusted_path` 는 각 중계가 *적극 신뢰*(`is_trusted` 증거 게이트 통과)여야 하는 더 엄격한 포스처 — 둘은 상보적. 신뢰는 방향성이라 경로 판정은 항상 origin 자신의 믿음으로만(중앙 신뢰 권위 없음). `reachability_class`·`classify`·`trusted_path`·`trusted_reach`·`risky_reach`·`summary`. 무작위성 0·정렬 출력·기존 모듈 무수정 순수 추가. code-reviewer 어드바이저 반영(HIGH 3건: `trusted_reach` 를 단일 분류 경로 `classify` 위임·`_require_registered` 명시적 멤버십 검증·SELF 제외 문서화). 단위 27건)
- **Phase 440** ✅ 신뢰 인지 분산 경로-벡터 장애 우회 수렴 (2026-06-16, `simulation/federation_trust_path_vector_failover.py` — `TrustPathVectorFailover`. 연합 라우팅 2×2 격자(홉만/신뢰 인지 × 고정 메시/장애 후 재수렴)의 마지막 빈 칸을 메운다: Phase 438(홉만 장애 우회)과 Phase 437(신뢰 인지 고정 메시)을 결합해, 장애 집합을 메시에서 제거한 *살아남은* 인접 위에서 Phase 437 신뢰 인지 경로-벡터(BGP LOCAL_PREF 다음 홉 선호)를 다시 수렴시켜 장애 전후 *신뢰 가중* 경로를 비교한다(`rerouted`·`lost_routes`·`is_reroutable`·`surviving_path`·`reconvergence_rounds`·`summary`). 핵심 불변식: ①빈 장애 → Phase 437 항등, ②무관찰(균일 0.5) → 선호 키가 (상수,홉,경로)로 환원되어 **Phase 438 장애 분석과 정확히 동일**(2×2 격자 두 칸이 그 모서리에서 만남), ③도달성(단절·우회 가능)은 신뢰와 무관하게 Phase 438 과 동일 — 신뢰는 *어느 우회로를 고르는가* 만 바꾼다(kite 토폴로지로 검증). Phase 435 교차 검증·콜드스타트 등가성. 무작위성 0·정렬 출력·기존 모듈(437·438·432·428) 무수정 순수 추가. code-reviewer 어드바이저 반영(HIGH 서로 다른 수렴 엔진의 `reconvergence_rounds` 를 cross-engine 동일성 단언에서 제외; MEDIUM `untrust_weight` 음수 검증을 본 경계에서 fail-fast·`T2` 내부 노드화). 단위 27건. **→ 🛰 Federation Operations(421-440) 트랙 완료** — 잔여 `Phase 426-427`(E2E·고스트 렌더링)은 HTML 시뮬레이터·Playwright 환경 의존, HLC 통합 글로벌 순서 토폴로지는 차기 트랙 후보 이월)

### Track 🔬 — Formal & Research Frontier (Phase 441-460) · 형식 검증·연구 개척

*테스트를 넘어 증명으로. 기존 자산: OCaml 타입 체커, Rust safety verifier, Prolog 규칙*

- **Phase 441** ✅ 5계층 안전망 TLA+ 명세 — 충돌 회피 우선순위 불변식 (2026-06-17, `specs/SafetyNetPriority.tla` + `docs/SAFETY_NET_TLA_SPEC.md` + `simulation/safety_net_invariant.py` — 5계층 안전망(L1 분리예측·L2 APF·L3 CBS·L4 컨트롤러·L5 강하)의 *우선순위 단조성* 불변식을 TLA+ 로 명세하고, 그 핵심 안전 속성을 Python 유한 모델 검사기로 재현. `SafetyState` frozen dataclass(severity→required_level 사상 검증)·`reachable_states` BFS·`check_invariant`(위반 시 초기→반례 최단 경로) — 위협 심각도가 오르면 활성 안전 계층도 단조 상승, 컨트롤러 미개입 시 위반 상태 도달 가능성을 반례로 제시. 무작위성 0·결정적. 통합 점검 시 PR #352 흡수)
- **Phase 442** ✅ 모델 체킹 — ATC 핸드오프 데드락 부재 증명 (2026-06-17, `simulation/handoff_model_checker.py` — 인스턴스 간 관제권 핸드오프 프로토콜을 유한 상태 기계로 모델링하고 도달 가능 전 상태를 BFS 전수 탐색해 ①단일 관제권(공백·이중 금지) 불변식과 ②교착 부재(후속 없는 비종료 상태 부재)를 증명. `HandoffState`(order=True 결정적 확장)·`check_model`(불변식/교착 반례 최단 경로)·`verify_handoff_safe`/`verify_handoff_deadlock_free`. 무작위성 0·결정적 반례. 통합 점검 시 PR #353 흡수. code-reviewer 어드바이저 반영(이중 속성 단일 BFS 계약 명시))
- **Phase 443** ✅ APF 수렴성 수학 증명 문서화 (Lyapunov 후보 함수) (2026-06-16, `simulation/apf_lyapunov.py` + `docs/APF_CONVERGENCE_PROOF.md` — APF 힘 법칙이 보존 포텐셜의 음의 기울기 `F = -∇U` 임을 명시: 인력 포텐셜 `V_att`(piecewise 이차/원뿔, C¹)·FIRAS 척력 `(k/2)(1/d−1/d0)²`, `total_potential`·`conservative_force`·`lyapunov_derivative`. 형식 증명: 양정치·C¹·radially unbounded, 과감쇠 흐름 `dU/dt = −‖∇U‖² ≤ 0`, LaSalle 전역 수렴(콤팩트 레벨집합), 국소 최소·속도 증폭 비보존항 한계와 상위 계층(CBS·교착 탈출) 완화 명시. `apf.py` 무수정 순수 추가, 무작위성 0. code-reviewer 어드바이저 HIGH 2건 반영(속도 증폭 비보존성으로 "하강 무보증" 정정·엔진 0.1m 인력 데드밴드 정합). 단위 16건)
- **Phase 444** ✅ CBS 완전성·최적성 조건 정리 (논문 §보강) (2026-06-17, `simulation/cbs_optimality.py` + `docs/CBS_COMPLETENESS_OPTIMALITY.md` — CBS 의 완전성·최적성 보장 조건(허용 휴리스틱·정점 분기 건전성·저수준 A* 비용 최적성)을 독립 BFS 기준해로 표본 검증하고, `cbs.py` 실제 구현이 충족/완화하는 보장을 정직 공시(`audit_sdacs_cbs`: 간선 충돌 정점 제약 한계·노드/A* 상한·tiebreak). `reference_optimal_steps`(BFS 최단)·`heuristic_is_admissible`·`low_level_is_optimal`·`vertex_branching_is_sound`. 무작위성 0. 통합 점검 시 PR #351·#352 흡수. code-reviewer 어드바이저 HIGH 2건 반영(BFS 목표 반환 전 t=0 forbidden 검사로 위양성 차단·A* 타임아웃 vs 도달불가 미구별 한계 공시) + 회귀 테스트 1건 추가)
- **Phase 445** ✅ 불확실성 정량화 — Monte Carlo 신뢰구간 자동 리포트 (`simulation/uncertainty.py` — 부트스트랩/정규근사 신뢰구간 자동 산출. 코드·테스트 main 적재 완료, 추적 정정 시 16건 PASS 재검증, 2026-06-17)
- **Phase 446** ✅ 충돌 해결률 공식의 통계적 검정력 분석 (`simulation/power_analysis.py` — 충돌 해결률 차이 검정의 검정력·표본수 산출. 코드·테스트 main 적재 완료, 추적 정정 시 15건 PASS 재검증, 2026-06-17)
- **Phase 447** ✅ 적대적 시나리오 fuzzing — 시드 기반 시나리오 변이 생성기 (`simulation/scenario_fuzzer.py` — `np.random.default_rng` 결정적 변이 + `adversarial` 부하↑·안전마진↓ 편향 모드, 출력은 `scenario_schema.validate_scenario` 계약 충족, 단위 14건 PASS, 2026-06-15)
- **Phase 448** ✅ 속성 기반 테스트(Hypothesis) — 시뮬 코어 불변식 1,000+케이스 (2026-06-16, 두 코어 동시 커버 — `tests/test_property_deconflict.py`: 4D 경로 충돌 감지 코어 `PathDeconflict` 의 9개 불변식(결정성·삽입순서 무관·보간 볼록성/클램프·충돌 술어 일관·시각 정렬·수직 분리 보장·단일/동일 경로, 9속성×130예제=1,170+케이스) + `tests/test_scenario_fuzzer_property.py`: Phase 447 적대적 퍼저 계약을 "고정 시나리오 통과"에서 "근방 시나리오 공간 전역 통과"로 격상하는 6개 불변식(스키마 보존·입력 불변성·시드 결정성·분포 재정규화·route 순서·adversarial 단방향 편향, max_examples 합 1,350케이스). 기존 APF(`test_apf_property.py`)·텔레메트리 압축(`test_property_telemetry.py`) property 자산이 안 다루던 충돌 감지·퍼저 코어를 덮음. 대상 `.py` 무수정(테스트 순수 추가), code-reviewer 어드바이저 반영, 15건 PASS)
- **Phase 449** ✅ 시뮬-실측 갭 모델 — DR 파라미터 보정 자동화 (`src/training/sim_real_gap.py`·`domain_rand.py` — Domain Randomization 파라미터 자동 보정. 코드·테스트 main 적재 완료, 추적 정정 시 7건 PASS 재검증, 2026-06-17)
- **Phase 450** ✅ 재현성 10년 보장 — 의존성 핀 + 컨테이너 다이제스트 고정 (`requirements.lock.txt`·`Dockerfile.reproducible`·`scripts/independent_reproduction.sh`·`docs/REPRODUCIBILITY.md` — 의존성 핀 + 컨테이너 다이제스트 고정 인프라 main 적재 완비, 2026-06-17)
- **Phase 451-460** RL 일반화 연구 (미학습 시나리오 전이) + 인증 가능 ML 조사 (EASA AI Roadmap)

### Track 🏛 — Standards & Policy (Phase 461-480) · 표준·정책 기여

*사용자에서 기여자로. 기존 자산: K-UTM 모듈, GENESIS 인증 트랙, IROS 논문*

- **Phase 461** ASTM F38 위원회 기고 초안 — 군집 관제 시험 방법 제안
- **Phase 462** ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스
- **Phase 463** K-드론 시스템 고도화 정책 제안서 (국토부 제출 형식)
- **Phase 464** 군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구
- **Phase 465** ✅ 공역 통합 시뮬레이션 표준 시나리오 셋 제안 (10종 공개) (2026-06-17, `simulation/standard_scenarios.py` + `config/scenario_params/nominal_baseline.yaml` + `docs/standards/SDACS_BENCHMARK_SUITE.md` — 도구 간 교차 벤치마크용 **공개 표준 스위트** `SDACS-SBS-10` 큐레이션. Phase 405(BlueSky·U-TRAFMAN 비교)·410(GUTMA 기고)이 전제하는 "같은 10개 시나리오를 같은 정의로 돌려 비교한다" 는 공통 기준선 제공. 핵심 설계: 시나리오 *정의* 는 기존 `config/scenario_params/*.yaml` 이 유일 출처(SSoT)이며 본 모듈은 정의를 복제하지 않고 통제 축(axis)·범주·표제 KPI 메타데이터만 덧붙여 YAML 을 가리킨다(`BenchmarkScenario` frozen dataclass). 10개 항목 B01..B10 은 서로 다른 운용 차원 하나씩을 통제(밀도·장애·이륙 서지·경로 충돌·통신 두절·기상·침입·다지역·자율 편대·공칭 기준선) — 통제 축 상호 배타. 검증되는 핵심 9종(s01-s09)에 더해 다른 9종 지표를 정규화하는 *대조(control)* 케이스인 신규 10번째 `nominal_baseline.yaml`(s10 공칭 저밀도) 추가. `validate_suite()` 가 10종 전부 `scenario_schema.validate_scenario` 계약 충족(러너 호환)을 결정적 재검증, `benchmark_manifest()` 가 도구 간 교환용 JSON 매니페스트 생성. 무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--list`·`--validate`·`--manifest`). 단위 17건 PASS)
- **Phase 466** ✅ 오픈 데이터 표준 — 텔레메트리 스키마 공개 (JSON Schema + 검증기) (2026-06-17, JSON Schema `docs/schemas/telemetry.schema.json`(draft-07, 2026-06-12 적재)에 더해 **검증기** `simulation/telemetry_validator.py` 신규: 임의 스냅샷이 표준 계약을 충족하는지 `validate_telemetry`/`validate_telemetry_file` 로 검사. `jsonschema` 설치 시 `Draft7Validator` 정본 검증, 미설치 시 스키마 제약(필수 키·길이 3 pos/vel·battery 0~100·stats 0 이상 정수·bool 배제)을 직접 구현한 순수 파이썬 폴백 — 두 경로 동일 판정. `simulation/scenario_schema.py`(GENESIS 322) `ValidationResult` 규약 준수, `CANONICAL_EXAMPLE` 표준 예제 + CLI(`--example`·파일 인자). 무작위성 0·기존 모듈 무수정 순수 추가. 단위 37건 PASS)
- **Phase 467** 사고 조사 데이터 표준 — 시뮬 로그 → 표준 양식 변환기 ✅ ([standards/INCIDENT_INVESTIGATION_REPORT.md](standards/INCIDENT_INVESTIGATION_REPORT.md))
- **Phase 468** 대학 캡스톤 표준 커리큘럼 제안 (GENESIS 383 확장)
- **Phase 469** ✅ 정책 영향 시뮬레이션 — 규제 파라미터(고도 상한·이격 거리) 변경 효과 자동 비교 (2026-06-17, `simulation/policy_impact.py` — 결정적 해석 용량 모델. 공역을 수직 분리 고도층의 적층으로 보고 `layers = floor(band/vertical_min_m)+1`, 층당 수평 용량은 이격 `s` 의 육각 최밀 충전 셀 면적 `(√3/2)s²` 로 `floor(area/cell)`, `capacity = layers × per_layer`. `PolicyConfig`(frozen, `__post_init__` 양수·고도 상하한·면적≥단일셀 불변식 검증)·`PolicyConfig.from_config`(`config/default_simulation.yaml` 적재 — 고도 바닥은 z[0] 과 drones.min_altitude_m 중 제약적인 쪽으로 과대계상 방지)·`compare_policies`(baseline vs proposed 의 `capacity_delta`·`capacity_pct_change`·`utilization`·`is_oversaturated`·`summary`). 이격 50→70m 강화 시 용량 −49%(≈50²/70²) 정량화. *정적 기하 용량 상한* 임을 정직 공시(동역학 미포함 → 절대값은 낙관적, 가치는 동일 모델 하 두 정책의 *상대 변화*). 무작위성 0·기존 모듈 무수정 순수 추가. code-reviewer 어드바이저 HIGH 2·MEDIUM 3·LOW 3 반영. 단위 33건 PASS)
- **Phase 470** 표준화 기고 추적 대시보드
- **Phase 471-480** 국내 표준(KS) 제안 1건 + 국제 워킹그룹 의견서 3건

### Track ♾️ — Continuum (Phase 481-500) · 10년 지속 가능성

*졸업 후 10년. 기존 자산: GENESIS 🎓 레거시 트랙, 재현성 패키지*

- **Phase 481** 의존성 자동 갱신 파이프라인 — Dependabot + 회귀 게이트 자동 머지 정책
- **Phase 482** 브라우저 API 폐기 감시 — WebGPU/WebXR 스펙 변경 카나리 테스트
- **Phase 483** Three.js 메이저 업그레이드 리허설 (r162 → 최신) + 호환 셰임
- **Phase 484** Electron LTS 추적 정책 (현 32→39 교훈 문서화)
- **Phase 485** ✅ 데이터 마이그레이션 도구 — 시나리오/미션 포맷 버전 변환기 (2026-06-17, `simulation/scenario_migration.py` — 시나리오 포맷의 역사적 변종을 단일 canonical v2.0 으로 정규화하는 결정적 버전 변환기. 실측 분기: 러너 `_translate_scenario` 가 관용하는 `simulation_duration_min`/`_s`(리포 5:5 혼재)·`drone_count`/`base_drone_count`/`base_traffic.drone_count` 에 더해, 스키마는 유효로 보나 *러너가 읽지 않는* `total_drone_count`(예: `multi_city.yaml`)가 잠재 불일치. canonical v2.0: 시간은 초(`simulation_duration_s`)·드론 수는 단일 `drone_count`·`schema_version: "2.0"` 명시 스탬프로 통일. `detect_version`(미스탬프=레거시 1.0)·`migrate_scenario`(멱등·원본 무변형·결정적, 모든 잉여 키 제거를 `changes`/`migrated` 에 표면화)·`migrate_file`(YAML 라운드트립). 정규화 결과는 항상 `scenario_schema.validate_scenario`(GENESIS 322) 계약을 경고 없이 충족 — 이를 위해 `_KNOWN_KEYS` 에 `schema_version` 1키 추가(수술적). **multi_city 의 `total_drone_count → drone_count` 정규화로 러너가 드론 수를 읽을 수 있게 복원**(실제 가치). 미션 포맷은 영속 버전 YAML 이 없어(코드 내 처리) 대상 외, `uam/` 하위는 별도 풍부 포맷이라 범위 외임 명시. 무작위성 0·CLI(`--detect`·`--all` dry-run·`--migrate -o`). code-reviewer 어드바이저 HIGH 3(잉여 키 무음 삭제 changes 미반영·float count 무음 절삭·테스트 갭)·MEDIUM 4·LOW 2 반영. 단위 33건 PASS)
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
| 422 운영의도 4D 볼륨 직렬화 | 🛰 | 🔥🔥🔥🔥 | ⭐⭐ | ✅ (2026-06-14) |

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
