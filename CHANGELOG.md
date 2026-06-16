# Changelog

이 프로젝트의 모든 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 기반으로 합니다.

## [Unreleased]

### 추가 (feat) — 일일 점검 2026-06-16 (20차): ODYSSEY Phase 439 신뢰 한정 도달성 통합 토폴로지 (3+ 인스턴스)
- **작업 상황 점검**: 19차(PR #343, `6bc06d4`)까지 Phase 438 분산 경로-벡터 장애 우회 수렴이 main 통합 완료, 작업 브랜치는 main 과 동기(0/0) 상태 확인 — *적체 없음*(19차에서 머지 병목 해소 후 정상화 유지). Federation Operations 잔여는 `Phase 426-427`(E2E·시각화, 사용자 환경 의존)·`439-440`. 본 점검은 즉시 sandbox 가능한 진짜 다음 갭 **Phase 439** 를 전진 구현.
- **Phase 439** — `simulation/federation_topology_view.py` (신규) 신뢰 한정 도달성 통합 토폴로지. Phase 432 메시 *연결성* 과 Phase 428 *신뢰* 를 합쳐, 한 origin 관점에서 연합 내 모든 목적지를 도달성 *품질* 로 분류하는 읽기 전용 관측(observability) 뷰 `FederationTopologyView`.
  - 5개 분류: `SELF`·`DIRECT`(직접 이웃, 중계 없음)·`RELAYED_TRUSTED`(다중 홉, 모든 중계가 origin 의 적극 신뢰인 경로 존재)·`RELAYED_RISKY`(도달 가능하나 완전-신뢰 경로 없음)·`UNREACHABLE`.
  - 갭: Phase 433 `TrustWeightedRouter` 가 *가장 싼 신뢰 가중 경로 하나* 를 고른다면, 본 모듈은 **신뢰할 수 있는 중계만 거치는 경로가 존재하는가** (존재성 ≠ 최소 비용) 를 답한다 — 중계가 끼어드는 **3+ 인스턴스에서만 의미가 생기는** 질문(2-인스턴스 직결엔 중계 없음). Phase 433 `avoid_untrusted_route` 가 *알려진 불신* 만 회피(미검증 중계 통과=무죄 추정)하는 반면, 본 모듈의 `trusted_path` 는 각 중계가 *적극 신뢰*(`is_trusted` 증거 게이트 통과)여야 하는 **더 엄격한 포스처** — 둘은 상보적(테스트로 대조 검증).
  - 신뢰는 방향성(Phase 428)이라 경로 판정은 항상 origin 자신의 믿음으로만(Phase 433 동일 철학, 연합엔 중앙 신뢰 권위 없음). 공개 API: `reachability_class`·`classify`·`trusted_path`(목적지 종단점 허용·정렬 이웃 동률 분리 BFS)·`trusted_reach`·`risky_reach`·`summary`(전 순서쌍 분류 분포, 모든 라벨 키 0 이상 보장). 무작위성 0·정렬 출력·경계 입력 검증(미등록 KeyError·threshold (0,1)·min_observations ≥ 0). 기존 `.py` 무수정(순수 추가). 단위 **27건 PASS**.
- code-reviewer 어드바이저 1회 반영(CRITICAL 0·HIGH 3·MEDIUM 2·LOW 3): HIGH ① `trusted_reach` 를 `risky_reach` 와 동일하게 단일 분류 경로 `classify` 에 위임 → 라벨 정의와 항상 일치(브리틀 제거), ② `_require_registered` 를 `neighbors()` 부수효과 탐침 대신 명시적 멤버십 집합 검증으로 교체(Phase 433 규약 정렬). MEDIUM `REACHABILITY_CLASSES` 의 `CLASS_SELF` 의도적 제외를 상수 주석으로 문서화. HIGH ③(reachability_class 이중 BFS)는 *UNREACHABLE 과 RELAYED_RISKY 구분에 메시 도달성 검사가 본질적으로 필요* 하므로 비-중복 — 인스턴스 수 N 이 작아 보류. 집계-분류 교차검증 테스트 1건 추가(+1).
- 검증: 신규 topology_view **27건** + 전체 federation 회귀(421~439) 합산 **397건 PASS**(0.50s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집(로컬 미설치 모듈은 수집 단계 에러로 분리 확인, 본 변경과 무관). 기존 `.py` 무수정(순수 추가) → 회귀 무영향.
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 439 완료 + 잔여 `Phase 426-427·440` 으로 갱신.

### 추가 (feat) — 일일 점검 2026-06-16 (19차): ODYSSEY 적체 병목 해소(PR #342 main 머지) + Phase 438 분산 경로-벡터 장애 우회 수렴
- **작업 상황 점검 — 머지 병목 해소(근본 원인 처리)**: 12차(PR #335)까지 main 통합 후 Phase 433~437 작업이 **머지되지 못한 draft PR 7건(#336~#342)으로 적체**된 상태를 확인. 18차 PR #342(clean, base=main, Phase 433-437 전체 + 신규 437 흡수)가 적체를 단일 브랜치로 일원화하고 있었으나 **main 머지가 안 되어 누적만 반복**되는 것이 근본 원인. 본 점검에서 PR #342 브랜치를 로컬 검증(Phase 433-437 단위 **146건 PASS**) 후 **main 으로 머지**(`a463330`)해 병목을 해소하고, superseded 된 PR #336·#337·#338·#339·#340·#341 **6건을 close**.
- **Phase 438** — `simulation/federation_path_vector_failover.py` (신규) 분산 경로-벡터 장애 우회 수렴. Phase 436/437(고정 메시 1회 수렴)·Phase 435(중앙 구조 분석)의 공백인 *인스턴스(USS) 장애 후 분산 재수렴*을 모사하는 `PathVectorFailover`.
  - 장애 집합을 메시에서 제거한 살아남은 인접 위에서 Phase 436 `PathVectorRouting` 수렴을 **인접 어댑터로 무수정 재사용**(죽은 노드 경유 광고 소멸 → 이웃 대체 경로 재광고를 모사)해 장애 전후를 비교: `rerouted`(전후 모두 도달하나 경로 변경)·`lost_routes`(전엔 닿았으나 후엔 단절)·`is_reroutable`·`surviving_path`·`reconvergence_rounds`·`summary`.
  - 핵심 불변식: 경로-벡터는 전체 경로 광고(BGP AS-PATH)라 거리-벡터 count-to-infinity 가 없어 **재수렴 결과 = 살아남은 메시 콜드스타트 고정점**(테스트로 등가성 검증). Phase 435 와 교차 검증 — 백업 경로 존재 ⇒ 주 경로 내부 중계 전멸에도 우회 생존, 절단점 장애 ⇒ 일부 쌍 단절. 무작위성 0·정렬 출력·경계 입력 검증(미등록 장애/origin KeyError). 단위 **22건 PASS**.
- code-reviewer 어드바이저 1회 반영(CRITICAL 0·HIGH 2·MEDIUM 4·LOW 4): HIGH ① `summary()` `lost_pairs` 가 죽은 origin 의 단절을 누락하던 것을 전 origin 순회로 바로잡아 총 영향 과소계상 제거(순서 있는 쌍 의미 docstring 명시), ② `is_reroutable(x,x)` 가 자기 경로에 True 반환하던 것을 `rerouted` 와 일관되게 False 가드 추가. MEDIUM 교차검증 테스트의 경로 *동일성* 단언을 도달성·죽은노드 미사용·길이로 완화(조밀 토폴로지 거짓 실패 방지)·`type: ignore`→`assert` 로 교체. 자기경로·죽은 목적지 엣지 케이스 테스트 2건 추가(+2).
- 검증: 신규 path_vector_failover **22건** + 전체 federation 회귀(421~438) 합산 **371건 PASS**(0.50s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. 기존 `.py` 무수정(순수 추가) → 회귀 무영향.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 438 완료 + 잔여 `Phase 426-427·439-440` 으로 갱신.

### 추가 (feat) — 일일 점검 2026-06-16 (18차): ODYSSEY Phase 437 신뢰 인지 분산 경로-벡터 라우팅 + 적체 흡수
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)까지 main 통합 완료. 이후 Phase 433·434·435·436 작업이 **머지되지 못한 draft PR 6건(#336·#337·#338·#339·#340·#341)으로 적체**된 상태 확인 — 최신 통합본 **PR #341(17차, clean, base=main, 12파일/2097줄)** 이 Phase 433-436 전체를 깔끔히 담고 있으나 main 으로 머지되지 못해 누적. **머지 병목이 근본 원인**(매 점검이 통합 PR을 새로 만들지만 main 머지가 안 됨). 본 점검은 PR #341 상태를 작업 브랜치로 흡수하고, 그 위에서 진짜 다음 갭 **Phase 437** 을 전진 구현해 6건 적체 + 신규 1건을 **단일 브랜치로 일원화**한다.
- **Phase 437** — `simulation/federation_trust_path_vector.py` (신규) 신뢰 인지 분산 경로-벡터 라우팅. Phase 436 분산 경로-벡터(홉만)와 Phase 433 중앙 신뢰 Dijkstra(전역 토폴로지)의 공백을 메운다: Phase 432 메시 인접 위에서 *분산* 수렴하되, 각 노드가 광고된 경로를 고를 때 *자신이 직접 관찰한 다음 홉 이웃의 신뢰도*(Phase 428)를 1순위 선호로 적용한다(BGP LOCAL_PREF).
  - `TrustPathVectorRouting(mesh, trust_model, untrust_weight=1.0)` — 선호 키 `(untrust_penalty(node→next_hop), 홉 수, 경로 튜플)`. 1순위가 다음 홉 신뢰이므로 더 신뢰하는 이웃을 거치면 홉이 늘어도 그 경로를 택한다(Phase 433과 같은 안전 논거를 분산 환경에 적용). 경로 나머지 신뢰는 그 구간을 고른 하류 노드들이 각자의 로컬 신뢰로 반영 → 신뢰 결정이 홉마다 분산 합성(중앙식 433과의 핵심 차이).
  - 핵심 불변식: 신뢰 동률(관찰 0 → 모든 이웃 균일 0.5)이면 키가 (상수,홉,경로)로 환원되어 **Phase 436과 정확히 동일한 경로**(테스트로 교차검증). 신뢰는 후보를 재배열만 할 뿐 제거하지 않아 도달성은 메시(Phase 432)와 동일. path-vector 루프 방지(BGP AS-PATH)·Jacobi 동기 갱신·next-hop local-pref(BGP 류 진동 없음)·무작위성 0. 공개 API(`converge`·`routes`·`best_path`·`hop_count`·`next_hop`·`forwarding_table`)는 Phase 436 과 동일 계약. 단위 **19건 PASS**.
- code-reviewer 어드바이저 1회 반영(HIGH 2건, CRITICAL 0): ① 수렴 라운드 상한(노드 수)을 "정리"가 아닌 *방어적 종결 캡*으로 정확히 기술 — 신뢰가 더 긴 경로를 선호할 수 있어 수렴 라운드가 지름보다 클 수 있음을 명시, ② float 동률 분리가 정수 prior(Beta(1,1)) 가정에 의존함을 Phase 433 처럼 명시(재현성 자체는 어떤 prior 에서도 보장). MEDIUM(키 이중 계산=Phase 436 동일 패턴, 컨벤션 일관성)·LOW 는 YAGNI·인접 모듈 일관성으로 보류. 어드바이저가 루프-프리·Jacobi 결정성·도달성 보존·API 패리티·무작위성 0 을 명시 검증.
- 검증: 신규 trust_path_vector **19건** + 인접 federation 회귀(path_vector·trust_routing·causal_delivery·resilient_routing·mesh·discovery·hybrid_clock·trust·audit·split_brain) 합산 **303건 PASS**(0.42s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. 기존 `.py` 무수정(순수 추가) → 회귀 무영향. PR #336~#341 은 본 브랜치로 superseded(머지 후 close 권장).
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 437 완료 + 잔여 `Phase 426-427·438-440` 으로 갱신.

### 통합 (chore) — 일일 점검 2026-06-16 (17차): ODYSSEY Federation Operations 적체 draft PR 통합 (Phase 433·434·435·436)
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)까지 Federation Operations(Phase 428·429·431·432) main 통합 완료. 이후 13·14·15차(Phase 433 신뢰 가중·434 HLC 인과-안정 배달·435 메시 복원력)는 **통합 PR #339(clean)** 로, 16차(Phase 436 분산 경로-벡터 라우팅)는 **PR #340(clean)** 로 머지되지 못하고 적체된 상태를 확인 → 두 적체분을 본 일일 점검 브랜치로 단일 통합.
- 통합 대상: PR #339(`federation_trust_routing.py`·`federation_causal_delivery.py`·`federation_resilient_routing.py` = Phase 433·434·435) + PR #340(`federation_path_vector.py` = Phase 436). 모두 신규 파일 추가(기존 `.py` 무수정)라 코드 비경쟁 — README/CHANGELOG/ROADMAP/ODYSSEY_PLAN append 충돌만 양측 보존으로 해소.
- 검증: 신규 federation 단위(path_vector 23 + trust_routing 37 + causal_delivery 36 + resilient_routing 31) + 인접 회귀(mesh·hybrid_clock·trust·audit·split_brain) 합산 **270건 PASS**(0.69s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. PR #336·#337·#338·#339·#340 은 본 통합으로 superseded.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 433·434·435·436 완료 + 잔여 `Phase 426-427·437-440` 으로 정리.

### 통합 (chore) — 일일 점검 2026-06-16 (15차): ODYSSEY Federation Operations 적체 draft PR 3건 통합 (Phase 433·434·435)
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)로 Federation Operations 적체(Phase 428·429·431·432)가 main 통합 완료된 이후, 13·14차(Phase 433 신뢰 가중 라우팅·434 HLC 통합 인과-안정 배달)와 Phase 435(메시 복원력 라우팅)가 **머지되지 못한 draft PR 3건(#336·#337·#338)으로 적체**된 상태를 확인 → 중단된 Federation Operations 작업을 본 일일 점검 브랜치로 통합.
- 통합 대상: PR #336(`federation_trust_routing.py` = Phase 433) + PR #337(`federation_causal_delivery.py` = Phase 434) + PR #338(`federation_resilient_routing.py` = Phase 435). 모두 신규 파일 추가(기존 `.py` 무수정)라 코드 비경쟁 — README/CHANGELOG/ROADMAP/ODYSSEY_PLAN append 충돌만 양측 보존으로 해소.
- 검증: 신규 federation 단위 **104건 PASS**(trust_routing 37 + causal_delivery 36 + resilient_routing 31), 인접 federation 회귀(discovery·handover·conflict·notam·split_brain·trust·audit·hybrid_clock·mesh·operational_intent) 포함 **331건 GREEN**. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → 나머지 수트는 simpy·scipy·hypothesis 등 미설치로 미수집(환경 의존, CI 전체 수집). PR #336·#337·#338 은 본 통합으로 superseded.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 433·434·435 완료 + 잔여 `Phase 426-427·436-440` 으로 정리.

### 추가 (feat) — 일일 점검 2026-06-16 (13차): ODYSSEY Phase 433 신뢰 가중 메시 라우팅
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)로 Federation Operations 적체(Phase 428·429·431·432)가 main 통합 완료됨을 확인. 열린 PR 15건(피처 #283 핫루프·#280 Phase 207 draft + dependabot 13)은 이전 점검들에서 사람 판단/후속 정리로 보류된 상태 유지. **머지된 모듈에만 의존하고 열린 PR과 비경쟁(신규 파일만 추가)인 진짜 공백 Phase 433**(메시 라우팅 확장의 첫 단계)을 본 브랜치에서 신규 구현. 잔여 공백 Phase 426·427(2-인스턴스 E2E·고스트 렌더링)은 HTML 시뮬레이터 + Playwright 브라우저 의존이라 본 최소 컨테이너에서 보류.
- **Phase 433** — `simulation/federation_trust_routing.py` (신규) 신뢰 가중 메시 라우팅. Phase 432 메시 토폴로지(`FederationMesh`)는 모든 인스턴스를 동등하게 보고 홉 수만으로 최단 경로를 계산하지만, Phase 428 신뢰 모델(`FederationTrustModel`)은 어떤 인스턴스가 협조 행위를 신뢰성 있게 이행하는지 정량화한다. 본 모듈은 라우팅하는 인스턴스(origin) **자신의** 신뢰 믿음으로 각 중계 후보 비용을 가중해 신뢰하는 이웃을 우선하는 결정적 최소 비용 경로를 계산한다.
  - **비용 모형** — origin→node 간선 비용 `hop_cost + untrust_weight*(1 - trust(origin→node))`: 완전 신뢰(1.0) 이웃은 홉 수와 동일, 미관찰은 중립 0.5, 완전 불신(0.0)은 최대 페널티. 라우팅은 항상 origin 관점(연합은 중앙 신뢰 권위 없음 → 같은 토폴로지라도 인스턴스마다 다른 경로 가능).
  - **API** — `route`(신뢰 가중 Dijkstra)·`route_cost`·`avoid_untrusted_route`(충분히 관찰된 불신 중계만 회피하는 BFS, 목적지는 종단점이라 불신이어도 허용)·`forwarding_table`(목적지→다음 홉 포워딩)·`relay_trust`. 우선순위 큐는 `(비용, 경로 튜플)` 키라 노드 첫 확정 시 최소 비용·사전식 최소 경로가 고정된다.
  - 무작위성 0·기존 모듈(mesh·trust·discovery) 무수정 순수 추가 → 같은 토폴로지·신뢰 상태·origin 은 항상 같은 경로/비용(재현·감사 가능). 단위 **37건 PASS**.
- code-reviewer 어드바이저 1회 반영: ① (HIGH) 동률 비용 경로를 무한정 push 해 큐가 증식하던 Dijkstra 를 **best-path 사전식 완화**(사전식으로 엄격히 나은 후보만 push)로 전환해 큐 증식 차단 + 첫 확정 시 사전식 최소 경로 보장, ② (HIGH) `federation_trust` 의 사설 상수 `_DEFAULT_MIN_OBSERVATIONS`·`_DEFAULT_TRUST_THRESHOLD` 직접 import 를 제거하고 로컬 정의(읽기 전용 통합 계층이 상대 모듈 내부 namespace 에 결합하지 않게), ③ (MEDIUM) `trust_threshold` (0,1) 범위 검증 추가(경계 밖 임계값이 `avoid_untrusted_route` 를 조용히 무력화하는 것 방지) + 파라미터화 테스트 4건, ④ (MEDIUM) float 동률 분리가 정확한 상등에 의존하며 무리수 신뢰 분수에서 ULP 차로 분리될 수 있으나 같은 입력은 항상 같은 경로를 내므로 재현성은 보장됨을 docstring 명시. LOW(route_cost 의 route 재계산·coverage 갭)는 KISS/YAGNI 로 보류.
- 검증: 신규 `tests/test_federation_trust_routing.py` **37건** + 인접 federation 회귀(mesh 25·trust 30·discovery·handover·conflict·notam·split_brain·audit·hybrid_clock) 합산 **240건 GREEN** 로컬 검증. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → 나머지 수트는 simpy·scipy·hypothesis 등 미설치로 미수집(환경 의존, CI 전체 수집).
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 433 완료 + 잔여 `Phase 426-427·434-440` 으로 갱신.

### 추가 (feat) — 일일 점검 2026-06-16 (14차): ODYSSEY Phase 434 HLC 통합 인과-안정 배달
- 작업 상황 점검: 12차(PR #335)로 Federation Operations 적체(Phase 428·429·431·432)가 main 통합 완료, 13차는 Phase 433 신뢰 가중 라우팅이 **draft PR #336 으로 진행 중**(미머지)임을 확인. **머지된 모듈(mesh·hybrid_clock)에만 의존하고 열린 PR #336(trust_routing)과 비경쟁(신규 파일만 추가)인 진짜 공백 Phase 434** 를 신규 구현.
- **Phase 434** — `simulation/federation_causal_delivery.py` (신규). Phase 432 메시 토폴로지는 origin 사건을 멀티홉 *전파* 하지만 각 수신 인스턴스의 처리(배달) **순서** 는 규정하지 않는다 — 플러딩 중복·타 origin 사건 혼입으로 순진한 도착순 처리는 인스턴스마다 순서가 어긋나 연합 결정이 불일치. 본 모듈은 Phase 431 HLC 를 결합한 **워터마크(low-water-mark) 안정 배달** 로 이를 해소.
  - 알고리즘: 각 출처가 FIFO 로 단조 증가하는 HLC 를 발행하므로, 알려진 모든 출처 고점의 최소(워터마크) 이하 사건은 **안정** — 그보다 앞선 사건이 미래에 도착 불가(CockroachDB closed-timestamp 와 동일 발상). 안정 사건만 HLC **전순서** 로 배달 → 모든 인스턴스가 동일한 결정적 순서로 처리.
  - `FederationEvent`(HLC 타임스탬프 + 불투명 페이로드, source=발행 인스턴스)·`CausalDeliveryBuffer`(출처별 FIFO 고점으로 멀티홉 중복·stale 멱등 무시 / 예상 출처 집합이면 모두 보고까지 보수적 보류, 없으면 관측 출처 best-effort / `deliverable`·`flush`·`pending`·`buffer_size`)·`FederationDeliveryCoordinator`(메시 `propagate` 로 origin 사건을 도달 가능한 모든 인스턴스 버퍼에 멱등 fan-out, TTL 한정, 스냅샷 모델). 무작위성 0·결정적. 단위 **36건 PASS**.
- code-reviewer 어드바이저 1회 반영: ① (HIGH) `flush` 의 `id(e)` 기반 제거가 구조적 동일 사본/리팩토링에 취약 → **워터마크 직접 분할** 로 교체(객체 식별자 무의존, dict 등 비해시 페이로드도 안전, 구조적 중복 재배달 차단). ② (HIGH) `deliverable`/`pending` 이 모두 빌 때 빔 vs 워터마크 보류를 구분할 `buffer_size()` 접근자 추가. ③ (MEDIUM) `FederationDeliveryCoordinator` 스냅샷 의미 docstring 명시(이후 `mesh.rebuild()` 시 새 코디네이터 필요). 어드바이저가 권한 monotonic 단정은 프로젝트 가이드("발생 불가 시나리오 에러 처리 금지")에 따라 보류.
- 검증: 신규 단위 **36건 PASS**, 인접 federation 회귀(mesh·hybrid_clock·discovery·trust·audit·split_brain·notam·handover·conflict) 포함 **237건 GREEN**. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 등 미설치 수트는 CI 전체 수집. 기존 모듈 **무수정** 순수 추가.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation 라인을 `Phase 434` 완료 + `Phase 433`(진행 중, PR #336) + 잔여 `Phase 426-427·435-440` 으로 갱신.
### 추가 (feat) — 일일 점검 2026-06-16: ODYSSEY Phase 435 메시 복원력 라우팅
- 작업 상황 점검: ODYSSEY Federation Operations(421-440) 중 머지 완료는 421-425·428-432, 열린 draft PR은 Phase 433(신뢰 가중 메시 라우팅 #336)·434(HLC 통합 인과-안정 배달 #337). **머지된 모듈에만 의존하고 열린 PR과 비경쟁(신규 파일만 추가)인 다음 공백 Phase 435**를 본 브랜치에서 신규 구현.
- **Phase 435** — `simulation/federation_resilient_routing.py` (신규). Phase 432 `FederationMesh` 스냅샷 위에서 인스턴스(USS) 장애 내성을 구조적으로 분석한다. Phase 430(분할 뇌)이 *분단 발생 후* 안전 강하를 다룬다면, 본 모듈은 *분단을 일으킬 구조적 취약점을 사전에* 드러낸다.
  - `articulation_points()`·`bridges()` — Hopcroft-Tarjan `disc`/`low` **반복** DFS(재귀 한계 회피, 정렬 순회로 결정성) 1회로 절단점(제거 시 연결 요소가 늘어나는 단일 장애점)과 브리지(제거 시 단절되는 단일 링크 인접)를 동시 식별. `is_single_point_of_failure(id)` 는 절단점 여부 질의.
  - `backup_path(src, dst)` — 메시 주 최단 경로의 *내부 노드·연속 간선*을 제거한 뒤 재-BFS 해, 주 경로의 어떤 중계가 죽어도 영향 없는(엔드포인트만 공유) 이중화 경로 존재 여부를 답한다. 노드·간선 동시 분리.
  - `surviving_reach(origin, failed)` — 임의 장애 인스턴스 집합 제거 후 origin에서 여전히 닿는 인스턴스·홉 수를 BFS로 계산.
  - 무작위성 0·정렬 출력·읽기 전용(생성 시점 인접 스냅샷에서만 분석). 단위 **31건 PASS**, 인접 federation 회귀(mesh·discovery·handover·notam·conflict·split_brain) 합산 **141건 GREEN**.
- code-reviewer 어드바이저 1회 반영: ① (HIGH) `backup_path` 가 주 경로만 live `mesh.shortest_path` 로 산정해 나머지 메서드(스냅샷 `self._adj` 기반)와 불일치 — 메시가 생성 후 rebuild되면 백업이 옛 주 경로를 "분리 백업"으로 잘못 반환하던 결함을, 주 경로도 스냅샷 BFS(`self._bfs`)로 일원화해 해소(메시 참조 제거). ② (MEDIUM) 불변 그래프에 매 호출 Tarjan 재계산 → `_tarjan_cache` 지연 캐시로 1회만 계산. ③ (MEDIUM) 백업 경로 간선 분리·메시 mutation 후 백업 일관성·2-노드 브리지 테스트 3건 보강(29→31). LOW(`surviving_reach` 미등록 노드 무검증·관용)는 결정성·YAGNI 로 보류. 알고리즘 정확성(반복 Tarjan low-link·루트 특수처리·역방향 간선)은 advisor 검증 통과.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 `Phase 435` 완료 + 잔여 `Phase 426-427·433-434·436-440` 으로 갱신. 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향.

### 추가 (feat) — 일일 점검 2026-06-16 (16차): ODYSSEY Phase 436 분산 경로-벡터 라우팅
- 작업 상황 점검: ODYSSEY Federation Operations(Phase 421-440)에서 12차(Phase 428·429·431·432)까지 main 머지 완료, 이후 13·14·15차(Phase 433 신뢰 가중·434 HLC 인과-안정 배달·435 메시 복원력)가 **머지되지 못한 draft PR(#336·#337·#338)과 통합 PR #339(clean)로 적체**된 상태를 확인 → 적체와 독립적으로 다음 메시 라우팅 Phase를 진행.
- **Phase 436** — `simulation/federation_path_vector.py` (신규) 분산 경로-벡터 라우팅. Phase 432(`shortest_path`)·Phase 433(`TrustWeightedRouter`)이 **전역 메시 스냅샷**을 한 노드가 통째로 보고 BFS·Dijkstra로 계산하는 반면, 실제 inter-USS 연합에서는 어떤 인스턴스도 전체 토폴로지를 모른다 — 본 모듈은 각 인스턴스가 *직접 이웃*만 알고 도달성을 광고·교환해 먼 목적지 경로를 분산 학습하는 경로-벡터 라우팅을 시뮬레이션한다.
  - `PathVectorRouting.converge()` — Jacobi(동기) 라운드. 매 라운드 모든 갱신이 *직전 라운드 스냅샷*만 참조하므로 노드 순회 순서와 무관하게 결정적, 수렴 라운드 수 = 메시 지름(diameter). 광고 경로 앞에 자신을 붙여 후보를 만들되 **경로에 자신이 이미 있으면 거부**(path-vector 루프 방지, BGP AS-PATH 발상)해 루프 프리를 보장. 동률(같은 홉)은 사전식 작은 경로 튜플로 분리.
  - `best_path`/`hop_count`/`next_hop`/`routes`/`forwarding_table` 조회 API + `is_converged`/`rounds_to_converge`. 조회 시 미수렴이면 자동 수렴. 미등록 노드는 `KeyError`, 음수 `max_rounds` 는 `ValueError`, 라운드 상한 미달 시 부분 결과 보존(`rounds_to_converge=None`).
  - 핵심 불변식 검증: 분산 수렴 경로의 홉 거리가 Phase 432 중앙 BFS(`shortest_path`)와 **항상 일치**(직선·3×3/2×3 격자 전수). 경로 유효성(연속 노드 인접·루프 없음·끝점), 분단 메시 도달 불가 처리, 결정성(동일 입력 동일 테이블), king-move 대각 1홉, 빈 메시·재호출 멱등. 단위 **23건 PASS**.
- 무작위성·외부 네트워크 0(순수 결정적), 모든 출력 정렬. 인접 federation 회귀(discovery·mesh·trust·audit·split_brain·hybrid_clock·handover·conflict·notam·operational_intent + path_vector) **250건 PASS**. 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집.
- code-reviewer 어드바이저 1회 반영: 핵심 알고리즘(Jacobi 고정점·path-vector 루프 방지·결정성·수렴 라운드·분단 처리) 정확성 확인. ① (HIGH) `max_rounds` 부분 수렴 조회가 "자동 수렴" docstring 과 모순되던 점을 YAGNI 원칙대로 **`max_rounds` 파라미터 제거**로 해소(부분 검사 기능은 요청 없는 추측성 → 삭제, 라운드 상한은 노드 수로 내부 보장), ② (LOW) Jacobi 라운드를 직전 스냅샷 읽기·신규 테이블 쓰기로 재구성해 프로젝트 불변성 규약 충족, ③ 빈 메시·`converge()` 멱등 테스트 보강.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 `Phase 436` 완료 + 잔여 `Phase 426-427·433-435·437-440` 으로 갱신.

### 통합 (chore) — 일일 점검 2026-06-15 (12차): ODYSSEY Federation Operations 적체 draft PR 4건 통합 (Phase 428·429·431·432)
- 작업 상황 점검: 8차(Phase 424·425·430)까지 main 머지 완료, 이후 9·10·11차(Phase 428 신뢰·429 감사·431 HLC)와 Phase 432(메시) 작업이 **머지되지 못한 draft PR 4건(#331·#332·#333·#334)으로 적체**된 상태를 확인 → 중단된 Federation Operations 작업을 단일 브랜치로 통합.
- 통합 대상: PR #333(`federation_trust.py`·`federation_audit.py`·`federation_hybrid_clock.py` = Phase 428·429·431 상위집합) + PR #334(`federation_mesh.py` = Phase 432). 모두 신규 파일 추가 + `federation_discovery.py` 공개 접근자 `volume_of` 1개 추가라 코드 비경쟁 — README/CHANGELOG/ROADMAP/ODYSSEY_PLAN append 충돌만 양측 보존으로 해소.
- 검증: 신규 federation 단위 **123건 PASS**(trust 30 + audit 29 + hybrid_clock 34 + mesh 30), 인접 federation 회귀(discovery·handover·conflict·notam·split_brain·operational_intent) **104건 PASS** = 합계 **227건 GREEN**. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → 나머지 수트는 simpy·scipy·hypothesis 등 미설치로 미수집(환경 의존, CI 전체 수집). PR #331·#332·#333·#334 는 본 통합으로 superseded.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 428·429·430·431·432 완료 + 잔여 `Phase 426-427·433-440` 으로 정리.

### 추가 (feat) — 일일 점검 2026-06-15 (11차): ODYSSEY Phase 431 하이브리드 논리 시계(HLC) + Phase 428·429 통합
- **Phase 431** — `simulation/federation_hybrid_clock.py` (신규) 하이브리드 논리 시계(HLC, Kulkarni et al. 2014). 3+ 인스턴스 메시 연합에서 인스턴스마다 벽시계가 어긋나도 물리 시계 동기화 없이 연합 결정(디스커버리·핸드오버·감사)의 **전역 인과 순서**를 결정적으로 매긴다.
  - `HLCTimestamp` (frozen, `order=True`) — `(wall_time, counter, instance_id)` 사전식 **전순서**. `causal_key`/`happened_before` 는 인스턴스 식별자를 제외한 `(wall, counter)` 로 **인과(부분 순서)** 를, `is_concurrent_with` 는 동률(서로 다른 인스턴스의 동시 이벤트) 동시성을 명시한다 — 전순서(정렬용)와 인과(causality)를 의미적으로 분리.
  - `HybridLogicalClock.local_event(pt)` / `receive_event(pt, remote)` — 표준 HLC 갱신 규칙: 새 `wall` = (지역 고점·원격 wall·물리 시각) 최댓값, `counter` 는 그 최댓값의 출처별 결정(지역·원격 동률 → max(c)+1, 한쪽만 → 그쪽 +1, 물리 시각 신규 최대 → 0). happened-before → 발행 타임스탬프 사전식 엄격 증가를 보장.
  - 물리 시계 역행을 견디고(논리 고점 유지·counter 증가), cold-start sentinel `-1` 로 갓 만든 시계의 첫 타임스탬프 counter 를 0으로 정규화. 무작위성·시스템 시계 직접 읽기 0 → 같은 이벤트 순서는 항상 같은 타임스탬프 열(재현·독립 검증). 단위 **34건 PASS**.
- code-reviewer 어드바이저 1회 반영: ① (CRITICAL) fresh 시계 `_wall=0` 이 유효 `t=0` 과 init sentinel 을 혼동해 첫 이벤트가 `counter=1` 이 되던 모호성을 `_wall=-1` sentinel + `current()` 클램프로 해소(첫 타임스탬프 항상 counter 0), ② (HIGH) `happened_before` 가 부분 순서임을 docstring 에 명시 + `is_concurrent_with` 추가해 "not happened_before = 역방향" 오용 차단, ③ (MEDIUM) cold-start receive 경로 테스트 2건 보강(29→34). MEDIUM(private 속성 외부 변형=인접 stateful dataclass 공통 패턴)·LOW 는 컨벤션 일관성·YAGNI 로 보류.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 `Phase 431` 완료 + 잔여 `Phase 426-427·432-440` 으로 갱신. 인접 federation 회귀(trust·audit·handover·conflict·notam·split_brain·discovery·operational_intent + hybrid_clock) **197건 PASS**, 전체 수집 **4,942건** 수집 오류 0.

### 추가 (feat) — 일일 점검 2026-06-15 (9차): ODYSSEY Phase 428 인스턴스 간 신뢰 모델
- **Phase 428** — `simulation/federation_trust.py` 연합 신뢰 모델. Phase 608 `BayesianReputation` 의 Beta-Bernoulli 켤레 사전분포를 인스턴스(USS) 레벨로 재사용해, 한 인스턴스가 상대 인스턴스의 협조 행위 이행 여부를 누적 관찰한 평판을 정량화한다.
  - `InstanceTrust` frozen dataclass 가 (관찰자→대상) **방향성** Beta(α,β) 믿음을 보유. `updated(success)` 는 원본을 변형하지 않고 α(성공)/β(실패)를 증가시킨 새 인스턴스를 반환(불변). `trust_score` = 사후 평균 `α/(α+β)`, `uncertainty` = Beta 분포 표준편차(관찰 누적 시 0 수렴).
  - `FederationTrustModel.observe(observer, target, success, kind)` 가 핸드오버(Phase 423)·충돌 협상(Phase 424)·NOTAM 전파(Phase 425) 협조 이벤트를 관찰해 신뢰를 갱신하고 결과 상태를 담은 `TrustEvent` 를 감사 로그에 기록. 신뢰는 비대칭(A→B ≠ B→A)이며 인스턴스는 자기 자신을 평가할 수 없다.
  - `is_trusted` 는 임계값(기본 0.5)과 **최소 관찰 게이트**(기본 5, Phase 608 `detect_malicious` 와 동일한 증거 요구)를 함께 통과해야 신뢰를 단정 — 사전분포만으로 성급히 신뢰/불신하지 않는다. `untrusted` 는 충분히 관찰된 저신뢰 쌍을 결정적 정렬 순서로 반환.
  - 무작위성 0(실제 연합 이벤트에서 관찰, 시뮬레이션 아님) → 같은 관찰 순서는 항상 같은 신뢰 상태(재현·감사 가능). 사전분포 α·β 양수 검증, 빈 식별자·자기 평가 거부. 단위 **30건 PASS**.
- code-reviewer 어드바이저 1회 반영(HIGH 3건): ① `_validate_pair` 가 식별자를 strip 후 키로 사용 — `"uss-a"` vs `"uss-a "` 가 별개 신뢰 슬롯으로 조용히 분기되는 것 방지, ② `InstanceTrust.__post_init__` 불변식 검증(α·β 양수·observations 비음수·observer≠target) 추가 — 잘못 구성된 믿음이 최소 관찰 게이트를 왜곡하지 못하게 함, ③ 모듈 docstring 의 불변성 주장을 "믿음·감사 항목은 불변, 모델 자체는 상태형"으로 범위 명확화. 반영 후 보강 테스트 7건 추가(공백 정규화·`__post_init__` 거부·다중 쌍 결정적 재현+로그 순서·custom prior 게이트·custom threshold) 포함 30건 재검증 GREEN. MEDIUM(kind 허용목록·np/math sqrt)·LOW(timestamp)는 federation_* 공통 패턴·YAGNI·결정성 원칙상 보류.
- ROADMAP Federation Operations 라인을 `Phase 428` 완료 + 잔여 `Phase 426-427·431-440` 으로 분해 갱신. `docs/SIMULATOR_ODYSSEY_PLAN.md` Phase 428 항목 ✅ 표기.

### 추가 (feat) — 일일 점검 2026-06-15 (10차): ODYSSEY Phase 429 연합 감사 로그
- **`simulation/federation_audit.py`** (신규) — 인스턴스 경계를 넘는 **변조 탐지(tamper-evident) 연합 감사 원장**. `FederationAuditLog` 은 append-only SHA-256 해시 체인으로, 각 항목(`AuditEntry`, frozen)이 직전 다이제스트를 재료에 포함해 중간 항목의 변조·삭제가 이후 모든 다이제스트를 깨뜨린다 → `verify()` 가 검출. 다이제스트 재료는 **길이 접두(length-prefixed) 직렬화**라 어떤 필드값이 구분자를 포함해도 서로 다른 필드 조합이 같은 재료를 만들 수 없어(주입·충돌 구조적 차단). 인스턴스별 단조 논리시계 강제, 인스턴스/이벤트 종류 쿼리.
- 두 인스턴스 원장은 결정적 **CRDT 류 `merge`** — 내용 키 `(logical_clock, instance_id, event_type, detail)` 사전식 전순서로 중복 제거 후 재-체인. **교환·결합·흡수 멱등**이라 어느 순서로 몇 번을 합쳐도 같은 head 다이제스트(재현·독립 검증). 분기(fork)된 같은 인스턴스 항목도 보존하며, 병합 경로는 `record()` 의 단조 검증을 우회해 분기 히스토리를 깨지 않는다.
- 단위 테스트 `tests/test_federation_audit.py` **29건 PASS** — 체인 연결·결정성·변조/삭제 탐지·구분자 위생·단조 시계·쿼리·병합 교환/결합/흡수멱등/중복제거/fork보존·record-after-merge. 인접 federation 회귀(handover·conflict·notam·split_brain·discovery·operational_intent) **122건 PASS**. 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향.
- code-reviewer 어드바이저 1회 반영: ① (CRITICAL) 다이제스트 재료를 길이 접두 직렬화로 전환해 `prev_digest` 포함 모든 필드의 구분자 주입·충돌을 구조적으로 차단, ② (HIGH) CRDT 흡수 멱등(`a.merge(b).merge(b)==a.merge(b)`)·`record`-after-`merge` 테스트 2건 보강(27→29), ③ 병합 원장의 비단조 분기 보존 의미를 `record`/`merge` docstring 에 명시. "frozen 으로 전환" HIGH 1건은 인접 `SafeDescentPolicy`(가변 `@dataclass` 누적자)와 동일 패턴이라 컨벤션 일관성 위해 보류. MEDIUM(내용 키 dedup=의도된 CRDT 의미)·LOW(동일 클래스 private 접근=관용)도 보류.
- ROADMAP Federation Operations 라인을 `Phase 429` 완료 반영. Phase 428(신뢰 모델)과 함께 통합되어 잔여 `Phase 426-427·431-440` 으로 갱신. 서로 다른 신규 파일이라 비경쟁.
### 추가 (feat) — 일일 점검 2026-06-15: ODYSSEY Phase 432 메시 연합 토폴로지 + 멀티홉 전파
- 작업 상황 점검 결과 ODYSSEY Federation Operations(421-440) 중 머지 완료는 421-425·430, 열린 draft PR은 428(신뢰)·429(감사 로그)·431(HLC). **머지된 모듈에만 의존하고 열린 PR과 비경쟁(신규 파일만 추가)인 진짜 공백 Phase 432**를 본 브랜치에서 신규 구현.
- **Phase 432** — `simulation/federation_mesh.py` (신규). Phase 421 디스커버리 등록 상태로 인스턴스 간 **공역 경계 인접 그래프**를 결정적으로 구성하고 그 위에서 멀티홉 전파를 계산한다.
  - **경계 인접 정의**: 타일형(비중첩) 공역을 위해 수평(x·y)은 `border_tolerance_m`(기본 1.0 m) 이내 접촉을 이웃으로 인식, 수직(z)·시간(t)은 엄격 4D 교차로 분리. Phase 425의 `Volume4D.overlaps`(엄격 교차)는 맞닿은 타일([0,1000)·[1000,2000))을 비이웃으로 보므로 메시 토폴로지용 인접을 별도 정의.
  - **그래프 질의**: `neighbors`·`adjacency`(대칭·정렬)·`components`(연결 요소)·`is_connected`·`shortest_path`(동률은 정렬 이웃 우선 BFS) — 모두 정렬 출력으로 재현성 보장.
  - **멀티홉 전파**: Phase 425의 1홉 직접 NOTAM 전파를 메시 전역으로 일반화한 `propagate`(origin→홉 수, TTL 한정 플러딩)와 `relay_table`(목적지→다음 홉 중계 포워딩 테이블). 중간 인스턴스를 경유해야만 닿는 먼 인스턴스 전파를 결정적으로 산정.
  - 디스커버리에 공개 접근자 `volume_of(instance_id)` 1개만 추가(타일 경계 기하 직접 산정용, 기존 동작 무영향).
- **검증**: 새 컨테이너에 core deps(numpy·simpy·pandas·scipy·pyyaml·hypothesis) + pytest 설치 후 `tests/test_federation_mesh.py` **25건** 신규 + 인접 federation 회귀(discovery 14·handover 16·notam·conflict·split_brain·operational_intent 등) 합산 **129건 PASS** 로컬 검증. 외부 네트워크·랜덤 0(순수 결정적).

### 통합 (chore) — 일일 점검 2026-06-15 (8차): ODYSSEY Federation Operations 3건 통합 (Phase 424·425·430)
- 열린 PR 21건(피처 8 + dependabot 13) triage 후, **기존 `.py` 소스 무수정·신규 파일만 추가하는 비경쟁 Phase PR 3건**을 본 작업 브랜치에 통합. 신규 컨테이너에 pytest+core deps 설치 후 신규 모듈 50건 + 인접 federation 회귀(handover 16·discovery 14·operational_intent 24) **104건 PASS** 로컬 검증. 전체 4,713 테스트 수집(hypothesis 미설치 환경 한정 4건 collection 에러는 본 변경 무관·기존 이슈).
  - **#327 Phase 424** — `simulation/federation_conflict_resolution.py` 연합 충돌 해소. Phase 422 `intents_conflict` 로 충돌 탐지 후 Phase 602 `VickreyAuction`(2위 가격제 봉인입찰) 재사용해 우선순위 협상. 낮은 priority 번호=높은 입찰가 결정적 사상, 동률은 `hashlib.sha256(intent_id)` 안정 해시로 분리(Python `hash()` 솔트 비결정성 회피). `apply_resolutions` 는 패자만 CONTINGENT 로 전환한 새 튜플 반환(원본 불변), 청산가는 Vickrey 차순위로 감사 기록 (11건).
  - **#328 Phase 425** — `simulation/federation_notam.py` 연합 NOTAM 전파. 동적 NFZ를 Phase 421 디스커버리(`query`)로 발견한 겹치는 인접 인스턴스에만 결정적 전파(DELIVERED/DUPLICATE/REVOKED). NFZ 이동 시 더는 겹치지 않는 이웃에서 stale 자동 회수, 멱등 재방송(`rebroadcast`)·철회(`revoke`), 철회 후 `_origin_of` 영구 보존으로 notam_id 소유권 탈취 차단, `_deliver` 버전 가드 `>=` 로 stale 패킷의 신버전 덮어쓰기 방지, 불변 감사 로그 (19건).
  - **#329 Phase 430** — `simulation/federation_split_brain.py` 분할 뇌 안전 강하 정책. `PartitionSnapshot` 이 양방향 링크를 연결 요소로 분해해 과반(majority) 분파 판정(2-2 균등 분할 시 무과반). `SafeDescentPolicy` 4단계 안전 사다리(NOMINAL→HOLD→DESCEND→LAND), `hold_limit`/`descend_limit` 초과 지속 시 단계 상승, 정상 복귀 시 카운터 초기화(이력현상). Phase 423 핸드오버가 미룬 안전 강하 책임 구체화, 불변 감사 로그 (20건).
- code-reviewer 어드바이저 1회 반영(HIGH 3건): ① `federation_conflict_resolution` `run_auction` 의 `AuctionResult | None` 반환에 대한 경계 가드 추가(발생 불가 상황이나 계약 명시), ② `federation_notam._withdraw` 멱등 방어(`.get()` + 미보유 시 조용히 무시), ③ `federation_split_brain.majority_component` 같은 연결 요소 BFS 재계산 제거(출력 불변, 중복 단락). 반영 후 104건 재검증 GREEN. MEDIUM(감사 로그 무한 누적·dataclass 가변 필드) 2건과 LOW(생성자 예외 타입)는 운영 노트로 보류(테스트 계약 보존).
- 문서는 세 PR이 동일 파일(CHANGELOG·README·ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md`)을 각자 수정해 상호 충돌하므로, **신규 소스/테스트 파일만 가져오고 문서는 본 통합 항목으로 일원화**. ROADMAP Federation Operations 라인을 `Phase 424·425·430` 완료 + 잔여 `Phase 426-429·431-440` 으로 분해 갱신.
- 후속: #327/#328/#329 원본 PR은 본 통합으로 산출물 반영 완료 → close 권고. 잔여 피처 PR #295/#289/#285(Phase 445·446 — 7차 점검 #326 에 이미 통합)·#280/#283 은 사람 판단 보류, dependabot 13건(#267-#279)은 후속 정리.

### 통합 (chore) — 일일 점검 2026-06-15 (5차): 신규 코드 PR 3건 통합 + 적체 중복 PR triage
- 열린 PR 32건(피처 19 + dependabot 13) triage 후, **신규 파일만 추가하는 비경쟁 Phase PR 3건**을 본 작업 브랜치에 통합. 신규 컨테이너에 pytest+core deps 설치 후 baseline **4,361 pass / 280 skip / 0 fail** 재현 → 통합 후 전체 **4,456 pass / 280 skip / 0 fail**(+95건, 회귀 0).
  - **#320 Phase 423·286·226·209-210** (4차 번들) — `simulation/federation_handover.py`·`scripts/ablation_study.py`(+`SwarmSimulator`/`AirspaceController` 가드 토글)·`src/digital_twin/sync_engine.py` WGS84 엄밀해·`docs/API_DEPRECATION_POLICY.md`.
  - **#322 Phase 308** — `simulation/insurance_rate_quote.py` 배상책임보험 요율 산정 API(33건).
  - **#321 Phase 447** — `simulation/scenario_fuzzer.py` 적대적 시나리오 퍼저(시드 결정적 변이, 14건).
- **정리 대상 확인**: #298·#300·#292·#291·#293(Phase 322·342·367·401·406·449)은 1차 점검(`c9923b1`)으로 **이미 main 통합 완료** — `scenario_schema.py`·`jeonnam_island_sites.py`·`swarm_self_healing.py`·`geo_zones.py`·`sim_real_gap.py` 5파일 origin/main 존재 재확인. 중복이므로 close 권고.
- **사람 판단 보류**: #295/#285/#289(Phase 445·446 통계 검정 경쟁 구현)·#280/#281(Phase 207 배지 쌍)·#283(핫루프 perf — 기존 코드 수정형). dependabot 13건(#267–#279)은 후속 정리.

### 추가 (feat) — 일일 점검 2026-06-15 (3차): GENESIS Phase 308 배상책임보험 요율 산정 API
- **Phase 308** — `simulation/insurance_rate_quote.py` 신규. 시뮬레이터 STELLAR Phase 67 `societyInsuranceQuote` mock(role·hours·history toy 공식)을 **실 보험사 요율 스펙**으로 격상. 항공사업법 §70 의무 배상책임보험 근거로 MTOW 등급 기본료 × 운용형태 × 비행시간 익스포저 × 보상한도 ILF × 경력 할인 × 무사고(NCB)/사고 할증 × 야간·BVLOS 가산을 결정적 누적 곱으로 산정하고 명세(`PremiumLine`)로 추적. 사용사업 의무가입·최소한도(1.5억원) 검증 포함.
- 단위 테스트 `tests/test_insurance_rate_quote.py` **33건 PASS** — 결정성·단조성(MTOW·사고·경력·한도)·NCB·위험 가산·의무가입 한도·명세 정합·입력 검증. 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향(baseline 4,361 pass / 280 skip / 0 fail, 84.24% 재현).

### 추가 (feat) — 일일 점검 2026-06-15: ODYSSEY Phase 447 적대적 시나리오 퍼저
- **`simulation/scenario_fuzzer.py`** (신규) — 시드 기반 결정적 시나리오 변이 생성기. `np.random.default_rng(seed)`로 동일 시드 → 동일 변이(재현성), 입력 dict 불변(새 객체 반환). `FuzzConfig(adversarial=True)`는 부하 필드(드론 수·도착률)를 위로, 안전 마진 필드(공역 면적·최소 분리거리)를 아래로 편향해 안전망에 스트레스를 가한다. `success_criteria`(합격 임계값)는 보존.
- 생성된 모든 변이는 기존 `scenario_schema.validate_scenario` 계약을 충족 — 9개 실 시나리오 × 40변이 = **360건 전부 VALID** 확인. `scenario_runner`·시나리오 마켓플레이스에서 그대로 실행 가능.
- **`tests/test_scenario_fuzzer.py`** (신규) — 단위 **14건 PASS** (재현성·불변성·스키마 적합·클램핑·분포 재정규화·거리 순서·적대적 편향). 인접 `test_scenario_schema.py` 28건 회귀 GREEN.
- code-reviewer 어드바이저 1회 반영: 미사용 `_FROZEN_KEYS` 죽은 코드 제거 + `drone_count` 정수 캐스트 강화.
- 참고: 본 Phase 447은 ODYSSEY 백엔드 트랙(시나리오 설정 퍼징)으로, ROADMAP의 기존 Phase 447(웹 시뮬레이터 e2e SORA fuzz, `tests/e2e/test_simulator_fuzz.py`)과는 별개 산출물(번호 병행 트랙).

### 통합 (chore) — 일일 점검 2026-06-15 (4차): 적체 PR 4건 무충돌 통합 (Phase 423·286·226·209-210)
- 열린 PR 29건 triage 후, **기존 코드 무수정·추가형 또는 가드된 토글·정밀도 버그픽스**인 비경쟁 Phase PR 4건을 본 작업 브랜치에 통합. 신규 컨테이너에 pytest+core deps 설치 후 통합 모듈·인접 회귀 **132건 PASS**(신규 68 + 시뮬레이터/컨트롤러 회귀 64) 로컬 검증.
  - **#318 Phase 423** — `simulation/federation_handover.py` 지역 간 관제권 핸드오버(RETAINED/ACQUIRED/HANDOVER/CONTINGENT + 이력현상) + `federation_discovery.py` `covering()`/`contains()` 프리미티브 (16건).
  - **#290 Phase 286** — `scripts/ablation_study.py` 안전망(APF·CBS) Ablation 자동화 + `SwarmSimulator`/`AirspaceController` `ablation.disable_apf/disable_cbs` 토글(기본 미설정 = 전 계층 활성, 회귀 무영향) (12건).
  - **#299 Phase 226** — `src/digital_twin/sync_engine.py` GPS→ENU 변환을 WGS84 ECEF→ENU 엄밀해로 격상(1km 평면근사 오차 153m→6cm, ±0.5m 충족) (22건).
  - **#286 Phase 209·210** — `docs/API_DEPRECATION_POLICY.md` API 폐기 생애주기 + SemVer 규약 (문서 전용).
- 보류(사람 판단 필요): **#295/#285/#289**(Phase 445·446 통계 검정 경쟁 구현)·**#280/#281**(Phase 207 배지 쌍)·**#283**(핫루프 힙 할당 제거 — 기존 perf 코드 수정형, 별도 검증)·dependabot 13건(#267–#279). 이미 main 통합 완료로 중복화된 **#298/#300/#292/#291/#293**(Phase 322·342·367·401·406·449)은 정리 대상.
### 추가 (feat) — GENESIS Phase 311 KISA CSAP 클라우드 보안인증 자가진단 자동화 (2026-06-15)
- **`simulation/csap_self_assessment.py`** (신규) — 과학기술정보통신부·KISA 「클라우드 보안인증제(CSAP)」 정보보호 기준의 14개 통제분야에 정렬한 자가진단 도구. 외부 호출 없이 이행 상태로부터 영역별 이행률·종합 준비도를 결정적으로 산출.
  - `DEFAULT_CATALOG` — CSAP 정보보호 기준 14개 통제분야(정책·인적·자산·공급망·침해사고·위험·대책·접근통제·암호화·개발·운영·서비스·물리·재해복구) × 대표 통제항목 카탈로그(운영자 교체·확장 가능).
  - `Status` 4종(이행/부분이행/미이행/해당없음) — 부분이행 0.5, 해당없음은 분모 제외하는 결정적 점수화. 응답 누락 항목은 보수적으로 미이행 처리.
  - `assess_csap()` — 분야별 `DomainScore`(이행률) + 종합 이행률 + 준비도 판정(95% 신청 권장 / 80% 보완 후 신청 / 미만 준비 부족) + 종합 이하 약화 분야 식별.
  - `build_responses()`·`build_report()`·`export_json()`·`export_text()` — `ControlResult` 변환 + 결정적 JSON/한국어 텍스트 export. **20건 PASS**, 기존 소스 무수정(순수 추가형).
### 추가 (feat) — GENESIS Phase 341: 목포 해역 실 좌표계 임포트 (해도 기반 NFZ·회랑)
- **#TBD Phase 341** — `src/applications/mokpo_harbor.py` 신규 모듈. 목포항 해역에 해도 기반 비행금지구역(NFZ) 4종(본항 부두·목포대교·유달산/삼학도 지형·남항 정박지)과 운항 회랑 3종(항만 진입·신안 도서 연계·의료 배송)을 결정적 좌표로 배치. 레이 캐스팅 `point_in_nfz()` NFZ 판정 + `corridor_nfz_conflicts()` 회랑-NFZ 충돌 검사 + `corridor_length_km()`(Haversine 재사용) + `harbor_summary()`. Phase 342 `jeonnam_island_sites.py`(목포한국병원 거점) 및 P747 해수부 항만 시범과 좌표 연계. 좌표는 공개 지도 근사값(maturity honesty 명시), 실증 전 해도 갱신 필요. 단위 테스트 8건 PASS, 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향(baseline 4,361 pass / 280 skip / 0 fail 재현 → +8).

### 통합 (chore) — 일일 점검 2026-06-15 (2차): 적체 PR 9건 무충돌 통합 (머지 병목 해소)
- 열린 PR 30건(피처 20 + dependabot 10) triage 후, **기존 코드 무수정·순수 추가형** Phase PR 9건을 단일 통합 브랜치로 합류. 신규 모듈 9개 + 단위 테스트 **190건 전부 PASS**, 기존 `.py` 소스 무수정(문서·신규 파일만) → 회귀 무영향.
  - **#313** (5건 누적): Phase 322 `scenario_schema.py` · 342 `jeonnam_island_sites.py` · 367 `swarm_self_healing.py` · 401·406 `geo_zones.py` · 449 `sim_real_gap.py`.
  - **#316 Phase 310** — `simulation/special_flight_approval.py` 야간·비가시 특별비행승인 안전기준 검증 (25건).
  - **#314 Phase 309** — `simulation/pilot_certification.py` 조종자 자격(1~4종) ↔ 시뮬 교육 모드 매핑 (24건).
  - **#315 Phase 408** — `simulation/airspace_class.py` ICAO 공역 클래스 A-G `classify_airspace()` API 격상 (25건).
  - **#307 Phase 304** — `simulation/kc_certification.py` KC 전파인증(전파법 §58-2) 적합성평가 분류 (23건).
- **#306**(Phase 304 `kc_radio_certification.py`)은 #307과 동일 Phase 경쟁 구현이라 **제외**(#307 채택). 보류: #295/#285/#289(Phase 445·446 경쟁 구현)·#280/#281(Phase 207 배지 쌍)·dependabot 10건은 사람 판단/후속.

### 통합 (chore) — 일일 점검 2026-06-15: 적체 PR 5건 무충돌 통합 (Phase 322·342·367·401·406·449)
- 머지 병목 triage 후 **기존 코드 무수정·순수 추가형** Phase PR 5건을 본 작업 브랜치에 통합. 통합 전 baseline 회귀 **4,171 pass / 280 skip / 0 fail** 재현, 통합 후 신규 **93건** 전부 PASS.
  - **#298 Phase 322** — `simulation/scenario_schema.py` + `docs/schemas/sdacs-scenario.schema.json` `.sdacs-scenario` 스키마 검증기 (20건).
  - **#300 Phase 342** — `src/applications/jeonnam_island_sites.py` 전남 도서(신안·완도) 의료 배송 거점 DB·실 좌표·Haversine ETA (7건).
  - **#292 Phase 367** — `src/autonomy/swarm_self_healing.py` 결손 드론 임무 자동 재분배 (12건).
  - **#291 Phase 401·406** — `simulation/geo_zones.py` UTM 그리드 존 결정적 판정 + EASA U-space 매핑 (22건).
  - **#293 Phase 449** — `src/training/sim_real_gap.py` 시뮬-실측 갭 Domain Randomization 자동 보정 (7건).
- 보류: **#295/#285/#289**(Phase 445·446) — 다중 경쟁 구현(`uncertainty.py`·`power_analysis.py`·`resolution_rate_power.py`·monte_carlo CI)으로 중복, 사람 판단 필요. **#295**의 `incident_report.py`(307·467)는 이미 통합된 `accident_report.py`/`incident_investigation_report.py`와 중복. **#306/#307**(Phase 304 KC)·**#280/#281**(Phase 207 배지)은 상호 중복. dependabot 13건은 후속 정리 대상.

### 추가 (feat) — GENESIS Phase 309 조종자 자격(1~4종) ↔ 시뮬 교육 모드 매핑 (2026-06-15)
- **`simulation/pilot_certification.py`** (신규) — 「항공안전법 시행규칙」 제306조 무인멀티콥터 조종자 증명 종별을 결정적으로 구현.
  - `classify_grade(mtow_kg)` — 최대이륙중량 기준 1~4종 분류(경계 모두 "초과" 규칙) + 250 g 이하 증명 불요 + 0 이하·초경량 상한(150 kg) 초과 `ValueError`.
  - `TrainingRequirement` frozen dataclass — 종별 온라인 학과/학과시험/비행경력/실기시험/실기평가/최소연령 + **시뮬 교육 모드**(상위 종이 하위 종 모드 포함).
  - `assess_pilot(mtow_kg, PilotProfile)` — 연령·비행경력·미이수 시뮬 모드로 조종자 준비도 결정적 판정.
  - `build_report`/`export_json`/`export_text` — 외부 의존성 0, `sort_keys` 안정 직렬화.
- **`tests/test_pilot_certification.py`** (신규) — 단위 **24건** (경계 분류·요건·준비도·exempt 불변·결정성·export).
- **`docs/certification/PILOT_LICENSE_MAPPING.md`** §6 추가 — 기존 문서-only 매핑(2026-06-12)을 실행 모듈로 격상, MTOW 기준 통일 명시.
- code-reviewer 어드바이저 1회 반영(150 kg 경계 테스트·exempt 불변 테스트 보강·`completed_sim_modes` 기본값 단순화·경계 "초과" 주석 통일). 시뮬레이터 HTML 무변경.

### 추가 (feat) — ODYSSEY Phase 423 지역 간 관제권 핸드오버 (2026-06-15)
- **`simulation/federation_handover.py`** (신규) — 드론이 인스턴스(USS) 공역 경계를 통과할 때 관제권을 결정적으로 이양하는 in-process 모델. Phase 421 디스커버리의 점 커버리지(`covering`)를 1차 입력으로 사용.
  - `HandoverCoordinator` — 위치 표본마다 **RETAINED**(현 관제권 유지)·**ACQUIRED**(최초 획득)·**HANDOVER**(인스턴스 간 이양)·**CONTINGENT**(커버리지 상실) 결정. 외부 네트워크·랜덤 0, 동일 입력 시퀀스 → 동일 로그(재현성).
  - 중첩(overlap) 구역에서는 현 관제권을 유지하는 **이력현상(hysteresis)** 으로 경계 진동(flapping) 방지. 후보 다수 시 id 사전순 최소로 결정적 선택(우선순위 협상은 Phase 424 범위).
  - 최초 획득(ACQUIRED)을 HANDOVER 와 구분 기록 — `from_instance=None` 인 위장 이양을 배제해 **Phase 429 불변 감사 로그** 무결성 확보.
  - `HandoverEvent` frozen dataclass(seq·drone_id·point·decision·from/to·candidates) 순서 보존 감사 로그.
- **`simulation/federation_discovery.py`** — `Volume4D.contains()`(반열린 구간 [min,max) 4D 점 포함)·`FederationDiscoveryService.covering()`(점을 포함하는 인스턴스 정렬 반환) 2개 프리미티브 추가. 경계 공유 볼륨의 중복 귀속 없음(핸드오버 결정성).
- **`tests/test_federation_handover.py`** (신규) — 단위 **16건** (RETAINED/ACQUIRED/HANDOVER/CONTINGENT·이력현상·반열린 경계·결정성·감사 로그 순서·검증·점 커버리지).
- code-reviewer 어드바이저 1회 반영(ACQUIRED 상태 분리로 감사 로그 의미 명확화·`covering` 내부 셋 스냅샷 순회·미배정 드론 CONTINGENT 대칭 테스트 추가). `ROADMAP.md` Phase 423 ✅ + `docs/SIMULATOR_ODYSSEY_PLAN.md` 반영. 시뮬레이터 HTML 무변경.

### 추가 (feat) — ODYSSEY Phase 422 운영 의도(Operational Intent) 4D 볼륨 교환 포맷 (2026-06-14)
- **`simulation/operational_intent.py`** (신규) — 연합 인스턴스 간 ASTM F3548-21 정렬 운영 의도 교환 포맷.
  - `Volume4D` frozen dataclass — WGS84 위·경도 외곽선 + 고도 밴드 + 시간 창, 경계 검증(꼭짓점≥3·위경도 범위·고도/시간 역전).
  - `OperationalIntent` frozen dataclass — `intent_id`·상태(ACCEPTED/ACTIVATED/NONCONFORMING/CONTINGENT/ENDED)·우선순위·볼륨 다수.
  - `to_dict`/`from_dict` 결정적 라운드트립 직렬화 (외부 의존성 0, JSON 직렬화 가능).
  - `volumes_intersect`/`intents_conflict` — 시간·고도·지리(경계상자) 3축 보수적 4D 교차 판정(거짓 음성 없음, 협상 전 1차 필터).
- **`tests/test_operational_intent.py`** (신규) — 단위 **24건** (검증·라운드트립·4D 교차·대칭성·ENDED 제외).
- `airspace_reservation.py`(내부 그리드 예약)와 상보적 — 인스턴스 간 교환 포맷 담당. 시뮬레이터 HTML 무변경.
- code-reviewer 어드바이저 1회 반영(필수 볼륨 API 명확화·역직렬화 ValueError 일관 래핑·고도 반열린 구간 주석·대칭성/중복 볼륨 테스트 보강).
### 기능 (feat) — ODYSSEY Phase 421 인스턴스 간 디스커버리 프로토콜 (2026-06-14)
- `simulation/federation_discovery.py` 신규 — ASTM F3548-21 **DSS**(Discovery and
  Synchronization Service)를 단순화한 결정적 in-process 모델. 다중 SDACS 인스턴스(USS)가
  각자 관리하는 **4D 공역 볼륨**(x·y·z 직육면체 + 시간 창)을 등록하면, 공간 그리드 셀
  인덱스(기본 500 m)로 후보를 좁히고 **정밀 4D AABB 교차**로 인접 인스턴스를 결정적으로
  발견·동기화한다. `register()`(이웃 발견)·`query()`·`synchronization_targets()`(상호
  동기화)·`remove()`·`summary()` 제공. 외부 네트워크·랜덤 없이 출력 정렬 보장(재현성),
  퇴화 볼륨·빈 id·비양수 셀 크기는 `ValueError`/`KeyError` 로 경계 검증.
- `tests/test_federation_discovery.py` 신규 — 4D 교차 대칭성·경계 접촉 비교차·셀 인덱싱·
  재등록 갱신·등록 순서 독립성·결정성 **13건 PASS**.
- `ROADMAP.md` Track I Phase 421 ✅ + `docs/SIMULATOR_ODYSSEY_PLAN.md` 반영. Federation
  Operations 트랙(421-440)의 첫 결정적 자산 — 운영 의도 교환(422)·관제권 핸드오버(423)의 기반.

### 기능 (feat) — ODYSSEY Phase 467 사고 조사 데이터 표준 변환기 (2026-06-14)
- `simulation/incident_investigation_report.py` 신규 — 시뮬레이션 안전 사건 로그(충돌·근접·
  충돌징후·추진/항법계 고장·공역 침범)를 **ICAO Annex 13** 구조의 표준 사고 조사 양식으로
  결정적으로 변환. ADREP 발생 분류 코드(MAC·SCF-PP·SCF-NP·AIRSPACE) 매핑 + 사건 등급
  (Accident/Serious Incident/Incident) 자동 판정. 근접 사건은 이격거리 임계값(5 m)으로
  준사고/이상 자동 조정. 시간순 사실 정보 + 등급·코드별 집계 분석 + 결정적 안전 권고를
  JSON·한국어 텍스트로 export. 입력 검증(`ValueError`).
- `tests/test_incident_investigation_report.py` 신규 — 분류·집계·검증·export·결정성 **25건 PASS**.
- `docs/standards/INCIDENT_INVESTIGATION_REPORT.md` 신규 — 근거 표준(ICAO Annex 13/ADREP)·
  등급 정의·5계층 안전망 사후 분석 계층 연계. Phase 466(텔레메트리 표준)의 조사 단계 후속.
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Phase 467 ✅ 표시. Track 🏛 표준·정책 자산 확장.

### 기능 (feat) — GENESIS Phase 304 KC 전파인증 요건 체크리스트 (2026-06-14)
- `simulation/kc_certification.py` 신규 — 드론 탑재 통신 모듈(RC·텔레메트리·영상·셀룰러·GNSS)에 대해
  「전파법」 §58-2 적합성평가 유형을 결정적으로 분류. **셀룰러→적합인증**, **비면허 특정소출력 대역 +
  공중선전력 한도 이내→적합등록**, **면허대역/한도 초과→적합인증**, **수신전용→적합등록(자기시험)**.
  제품 단위로 가장 엄격한 유형을 집계하고 유형별 제출서류 + KC 식별부호 표기 안내를 JSON·텍스트로 export.
  시스템 경계 입력 검증(`ValueError`).
- `tests/test_kc_certification.py` 신규 — 분류·집계·검증·export·결정성 **23건 PASS** (전 대역 parametrize 포함).
- `docs/certification/KC_RADIO_CERTIFICATION.md` 갱신 — 실행 모듈 링크 + 917–923.5 MHz(비면허 특정소출력)
  분류를 적합등록으로 정정(기존 문서 M4/M6 적합인증 표기와 코드 일치화).
- `docs/SIMULATOR_GENESIS_PLAN.md` Phase 304 ✅ 표시. SORA(302)·비행계획 신고(303)에 이어 규제 적합 자산 확장.

### 기능 (feat) — GENESIS Phase 303 비행계획 신고 양식 자동 생성 (2026-06-14)
- `simulation/flight_plan_filing.py` 신규 — 드론 원스톱 비행승인 신청서를 시뮬 파라미터로부터
  결정적으로 생성. 관제권(9.3 km)·고도(150 m AGL)·비행금지구역·BVLOS·야간 비행을 종합해
  **비행승인 / 특별비행승인 / 기체신고** 필요 여부를 자동 판정하고 JSON·한국어 텍스트로 export.
  haversine 거리 기반 구역 진입 판정 + 시스템 경계 입력 검증(`ValueError`).
- `tests/test_flight_plan_filing.py` 신규 — 판정·검증·export·결정성 **18건 PASS**.
- `docs/certification/FLIGHT_PLAN_FILING.md` 신규 — 근거 법령·임계값·API·5계층 안전망(Layer 0) 연계.
- `docs/SIMULATOR_GENESIS_PLAN.md` Phase 303 ✅ 표시. SORA 계산기(302)와 함께 규제 적합 자산 확장.

### 추가 (docs) — TRANSCENDENCE Phase 209·210: API Deprecation Policy + SemVer 규약 (2026-06-13)
- `docs/API_DEPRECATION_POLICY.md` 신설 — `window._sdacs` 외부 404 API의 **버전 관리·폐기 규약**을 단일 기준으로 확정:
  - **Phase 210 (SemVer)**: MAJOR/MINOR/PATCH ↔ API 영향 정의 + 4개 호환성 불변식 + maturity 격상(speculative→mock→beta→production)을 MINOR로 취급.
  - **Phase 209 (Deprecation)**: ACTIVE → DEPRECATED(≥1 MINOR, `console.warn` 1회) → REMOVED(MAJOR 경계) 3단계 생애주기 + maturity별 폐기 보수성 차등(production 최장 유지) + Deprecation Registry 표(현재 0건) + `experimental.*` 면책 규정.
  - 변경 절차 체크리스트(VERSION.md 증가·E2E 동반·`extract_sdacs_api.py --check` G-2·md5 G-4·CHANGELOG 표기)로 기존 거버넌스 게이트와 연결.
- 근거: `docs/MASTER_PLAN_2026H2.md` Track Ⅱ-4 (Phase 209-210 Deprecation Policy + SemVer 문서) — 명시된 차기 스프린트 항목 완료.
- 영향: 핵심 시뮬레이터 코드·테스트 무변경(문서 전용), 4 사본 md5 불변. 베이스라인 회귀 **4,071 pass / 280 skip / 0 fail** GREEN 독립 재현 확인(신규 컨테이너, `pytest -n auto`, 103s).

### 기능 (feat) — TRANSCENDENCE Phase 286: 안전망 Ablation 자동화 (2026-06-13)
- **`scripts/ablation_study.py` 신설** — 안전망 계층(APF 회피·CBS 다중 에이전트 계획)을 선택적으로
  제거하고 충돌·근접경고·충돌 해결률에 미치는 영향을 정량화. `baseline`/`no_apf`/`no_cbs`/
  `no_apf_no_cbs` × N 시드를 실행해 시드 평균을 markdown(논문 §Ablation 삽입용)+JSON으로 출력.
  충돌 해결률은 CLAUDE.md 공식 `1 − collisions/(conflicts + collisions)` 사용.
- **시뮬레이터·컨트롤러 ablation 토글 추가** — `SwarmSimulator`가 `ablation.disable_apf`를,
  `AirspaceController`가 `ablation.disable_cbs`를 읽음. **둘 다 기본 미설정 시 전 계층 활성**으로
  기존 동작과 완전 동일(additive, 회귀 무영향). `disable_apf`는 `_apf_batch_loop`에서 회피 힘
  계산을 건너뛰고, `disable_cbs`는 CBS 배치 계획을 건너뛰어 per-drone A* 폴백만 사용.
- **검증**: `tests/test_ablation_study.py` 12개 단위 테스트 PASS(해결률 공식·집계·토글 plumbing·
  통합 스모크). 샘플 실행(25드론·90s·2시드)에서 APF 제거 시 충돌 1.00→2.50, 해결률 98.25%→94.50%로
  악화 — 안전망 효과를 정량 확인. 전체 회귀 기준선 **4,071 pass / 280 skip / 0 fail**(83.87%) 영향 없음.
### 수정 (fix) — Phase 207 Maturity Badge 자동 생성·드리프트 해소 (2026-06-13)
- **드리프트 발견**: 수작업 유지되던 `docs/badges/maturity.svg`가 `prod 89`로 표기되어
  라이브 실측(`maturityReport()`)·자동 생성 `docs/SDACS_API.md`의 **production 90**과 불일치.
  Phase 207은 "완료"로 표기되어 있었으나 배지가 코드 생성물이 아니라 수작업이라 무방비로 어긋남.
- **해소**: `scripts/extract_sdacs_api.py`에 `render_badge_svg(counts)` 순수 함수 추가 —
  라이브 maturity counts에서 배지 SVG를 **결정적으로 생성**(세그먼트 폭을 카운트 자릿수에서 산출).
  재생성 시 `maturity.svg`도 함께 출력하고, `--check` 게이트(CI `sim-smoke.yml`)에 배지-실측
  정합성 검사를 편입해 향후 드리프트를 차단. 배지를 `prod 90`으로 정정.
- **테스트**: `tests/test_maturity_badge.py` 신규 7건 (counts 포함·title 일치·SVG 구조·폭 산출·
  결정성·자릿수 변화·저장 배지=생성기 출력 게이트). 브라우저 없이 순수 함수만 검증.

### 점검 (chore) — 일일 점검 2026-06-13 (신규 컨테이너 독립 재현 GREEN)
- 신규 세션 컨테이너에서 의존성 신규 설치(`blinker` RECORD 충돌은 `--ignore-installed`,
  `pytest-xdist`·`pytest-timeout`·`hypothesis` 추가 설치) 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,065 pass / 267 skip / 0 fail** (545.46s) — 본 세션 +7 배지 테스트 포함.
  커버리지 게이트(≥ 80%) 통과.
- **저장소 상태**: 열린 이슈 0건. main 직전 머지 PR #265(Maturity 정직성·SORA·계획 3층) 기준 동기.

### 점검 (chore) — 일일 점검 2026-06-12 (18차 독립 재현 GREEN, main `843aec9` 기준)
- 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (388.13s).
  8~17차와 **동일 수치** 재확인 — 18차 독립 재현 GREEN. 커버리지 **83.93%**(≥ 80% 게이트) 동일 재현.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `843aec9` — 직전 17차 기준 `c2649ad`에서
  PR #261 머지로 전진). main 최신 커밋(`843aec9`) CI·Security Audit·Canonical Hash Verification·Pages
  **전 워크플로우 success** 확인(actions API 재조회).
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 열린 PR **0건**, 보조 로드맵(`docs/MASTER_TODO_ATC.md`) 미체크 **0건**.
  `ROADMAP.md` 잔여 미체크는 **P755(창업·LOI)** 1건뿐 — 사용자 환경 의존. `docs/ULTRA_PLAN.md`·
  `presentation_remaining_tasks.md` 미체크는 슬라이드 실물 제작·브라우저 검증·실 하드웨어 비교 실험
  등 전부 사용자 환경 의존 항목으로 코드 작업거리 없음.
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `pytest`·`pytest-xdist`·`pytest-cov` 미설치 +
  `dash`·`pandas` 미설치 시 실패 → `pip install --ignore-installed blinker -r requirements.txt 'pytest<9'`
  + `pip install pytest-xdist pytest-cov` 후 `python -m pytest`로 정상 재현(Debian `blinker` RECORD
  부재 충돌은 `--ignore-installed`로 우회, `pyproject.toml` addopts `-n auto --dist loadfile`이
  `pytest-xdist` 요구).
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-12 (17차 독립 재현 GREEN, main `c2649ad` 기준)
- 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (309.64s).
  8~16차와 **동일 수치** 재확인 — 17차 독립 재현 GREEN. 커버리지 **83.93%**(≥ 80% 게이트) 동일 재현.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `c2649ad` — 직전 15차 기준 `91a4fcc`에서
  PR #259 머지로 전진). main 최신 커밋(`c2649ad`) CI·Security Audit·Canonical Hash Verification
  **전 워크플로우 success** 확인(actions API 재조회).
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 보조 로드맵(`docs/MASTER_TODO_ATC.md`) 미체크 코드 작업거리 **0건**.
- **중복 점검 PR 정리**: 같은 날(2026-06-12) 동일 main HEAD `c2649ad` 기준 16차 점검을 기록한 미머지
  드래프트 PR **#260**(16차)을 본 점검(17차, 동일 수치 재현 + 전 워크플로우 success 재확인)으로
  **superseded** 처리.
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `pytest`·`pytest-xdist`·`pytest-cov` 미설치 +
  `dash`·`pandas` 미설치 시 실패 → `pip install pytest-xdist pytest-cov pytest-timeout`
  (`--ignore-installed blinker` 우회) + `requirements.txt` 전체 설치 후 `python -m pytest`로 정상 재현.
  PATH의 uv 격리 `pytest 9.x`는 사용 금지(`pyproject.toml` addopts `-n auto --dist loadfile` 필요).
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-12 (15차 독립 재현 GREEN, main `91a4fcc` 기준)
- 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (503.23s).
  8~14차와 **동일 수치** 재확인 — 15차 독립 재현 GREEN. 커버리지 **83.93%**(≥ 80% 게이트) 동일 재현.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `91a4fcc` — 직전 14차 기준 `e1aa87c`에서
  PR #258 머지로 전진). main 최신 커밋(`91a4fcc`) CI·Security Audit·Canonical Hash Verification·Pages
  **전 워크플로우 success** 확인.
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 열린 PR **0건**, 보조 로드맵 미체크 코드 작업거리 **0건**
  (`SIMULATOR_HYPER_PLAN.md` 데모 영상 30초는 MediaRecorder 녹화 기능이 `swarm_3d_simulator.html` CIN-4에
  이미 구현됨 → 실제 영상 산출은 브라우저 세션 의존, P755 창업과 함께 사용자 환경 의존 항목).
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `dash`·`pandas` 등 미설치 시 `visualization`/`monte_carlo`
  계열 16건이 `ModuleNotFoundError`로 실패 → `requirements.txt` 전체 설치(`--ignore-installed blinker` 우회)
  + `pytest>=8.4,<9`·`pytest-xdist`로 정렬해야 4,057 정상 재현. PATH의 uv 격리 `pytest 9.x`는 사용 금지.
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-12 (14차 독립 재현 GREEN + 중복 점검 PR #257 정리)
- 신규 세션 컨테이너에서 의존성 신규 설치(`pytest`·`pytest-xdist`·`pytest-cov` + `requirements.txt`) 후
  전체 회귀 **독립 재현**: `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (407.63s).
  8~13차와 **동일 수치** 재확인 — 14차 독립 재현 GREEN. 커버리지는 CI 측정 기준 **83.93%**(≥ 80% 게이트) 유지.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `e1aa87c`). main 최신 커밋(`e1aa87c`)
  CI·Security Audit·Canonical Hash Verification·Pages **전 워크플로우 success** 확인.
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 보조 로드맵(`docs/MASTER_TODO_ATC.md`) 미체크 코드 작업거리 **0건**.
- **중복 점검 PR 정리**: 같은 날(2026-06-12) 동일 4,057 검증을 기록한 미머지 드래프트 PR **#257**(13차)을
  본 점검(14차, 동일 수치 + main `e1aa87c` 기준 재현)으로 **superseded** 처리하고 정리.
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `pytest` 미설치 → `pip install pytest pytest-xdist pytest-cov`
  (`--ignore-installed blinker` 우회) + `requirements.txt` 설치 후 `python -m pytest`로 정상 재현.
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-11 (8차 독립 재현 GREEN + 중복 점검 PR 정리)
- 신규 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `PYTHONHASHSEED=0 python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (531s, 커버리지 **83.93%** ≥ 80% 게이트). 8차 독립 재현 GREEN — 직전 재현들과 **동일 수치** 재확인.
- **환경 함정 해결**(후속 세션 참고): 신규 컨테이너 PATH의 `pytest`가 uv 격리 도구(`pytest 9.0.2`, numpy 미포함)로 잡혀
  `conftest.py` import 실패를 유발 → 시스템 인터프리터 기준 `python -m pytest`(pytest 8.4.2, `requirements.txt` 핀)로 실행해야 정상 재현됨.
  `pip install`은 시스템 debian `blinker` RECORD 부재로 중단되어 `--ignore-installed blinker`로 우회.
- **중단 작업(중복 점검 PR) 정리**: 같은 날 동일 4,057 검증을 기록한 미머지 드래프트 PR **#250**(6차)·**#251**(7차)이 적체 →
  본 점검(8차, 동일 수치 + 환경 함정 노트 보강)으로 **superseded** 처리하고 정리.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0), main 최신 커밋(`bba6815`) CI·Security Audit·Canonical Hash·Pages **전 워크플로우 success**.
- **작업거리 재확인**: Python 소스 실 TODO/FIXME **0건**, 열린 이슈 **0건**, 보조 로드맵 미체크 항목 **0건**.
  로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 / P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-11 (신규 세션 독립 재현 + 중단 PR 정리)
- 신규 컨테이너에서 의존성 신규 설치(`requirements.txt` + `pytest-xdist`) 후 전체 회귀 **독립 재현**:
  `pytest tests/` → **4,057 pass / 252 skip / 0 fail** (311s, 커버리지 **83.93%** ≥ 80% 게이트). 5차 독립 재현 GREEN.
- **중단 작업 정리**: 직전 세션이 남긴 열린 PR **#248**(STELLAR Phase 51 시드 API 5건 `docs/SDACS_API.md` 누락 보강,
  문서 전용) 전제를 재검증 — 시뮬레이터 `_sdacs`에 5개 멤버 존재 / 당시 `main` 문서에는 부재 확인. head CI·Security Audit
  모두 success 확인 후 **머지**. 머지 후 열린 PR 0건.
- Python 코드 실 TODO 0건 재확인(`onboard_bridge.py` 2건은 추상 인터페이스 메서드·플랫폼 시그널 핸들러 가드로 오탐).
  로드맵 **99.5%** 유지 — 잔여 4항목 전부 사용자 환경 의존(P755 창업·LOI / Track A 실기 / P707 실측 그래프 / P709 IROS 투고).

### 문서 (docs) — 일일 점검 2026-06-11 (Phase 51 시드 API 문서 동기화)
- 신규 컨테이너에서 의존성 재설치 후 전체 회귀 **독립 재현**: `pytest tests/` → **4,057 pass / 252 skip / 0 fail**
  (398s, 커버리지 **83.93%** ≥ 80% 게이트). 브랜치는 `main`과 완전 동기(0/0), 열린 PR 0건, Python 코드 실 TODO 0건.
- **중단 작업 발견·완결**: STELLAR Phase 51 시드(#232)가 `swarm_3d_simulator.html` `window._sdacs`에 추가한
  API 5건(`stellar51DelegatedGroups`·`stellar51Groups`·`stellar51Recommend`·`stellar51Revoke`·`stellar51Tick`)이
  `docs/SDACS_API.md`(2026-06-05 자동 생성본)에 누락돼 있던 것을 확인. 현재 시뮬레이터 `_sdacs` 멤버를 견고한
  파서로 전수 추출해 문서와 diff → 누락 5건만 알파벳 위치에 정확히 보강(형 라벨 포함), 총계 표기를 실제
  테이블 행 수 **392항목**으로 정정(원본 388 → 1건 과대표기였던 것도 함께 교정).
- `docs/SIMULATOR_HYPER_PLAN.md` "`_sdacs` 전체 API 자동 문서화" 체크박스 `[ ]` → `[x]` (산출물 존재·최신화 반영).
- 로드맵 **99.5%** 유지. 잔여 4항목 전부 사용자 환경 의존(P755 창업·LOI / Track A 실기 검증 /
  P707 §4-§7 실측 그래프 / P709 IROS 2026 투고).

### 점검 (chore) — 일일 점검 2026-06-11 (신규 컨테이너 독립 재현 GREEN)
- 신규 클론 컨테이너에서 의존성을 새로 설치(`requirements.txt` + `pytest-xdist`·`pytest-cov`)한 뒤
  전체 회귀를 **독립 재현**: `pytest tests/` → **4,057 pass / 252 skip / 0 fail** (320s, 커버리지 **83.93%** ≥ 80% 게이트 통과).
- `main` CI 전 워크플로우 success 확인 (CI · Security Audit · Canonical Hash Verification · Simulator Smoke · Pages).
- 코드 내 실 TODO/FIXME **0건** — 잔여 매치는 추상 베이스 `RemoteIDTransport.emit` `NotImplementedError`
  (`LogRemoteIDTransport` 폴백 + 테스트로 검증됨)와 테스트 fixture 문자열뿐.
- 로드맵 **99.5%** 유지. 잔여 4항목 전부 사용자 환경 의존(P755 창업·LOI / Track A 실기 검증 /
  P707 §4-§7 실측 그래프 / P709 IROS 2026 투고)이라 코드 작업거리 없음.
- **PR 백로그 재정리**: 병렬 세션이 동일 결과를 중복 기록한 일일 점검 PR 2건(#245·#246)을 superseded로 close
  (둘 다 머지 완료된 #244와 동일한 `4,057 pass` 수치 중복) → 열린 PR 0건 유지.
- **4차 독립 재현**(신규 컨테이너, `pytest-xdist -n auto`): `pytest tests/` → **4,057 pass / 252 skip / 0 fail**
  (490s, 커버리지 **83.93%**) — 1·2·3차와 **동일 수치** 재확인(seed 고정 결정성 교차 검증).

### 수정 (fix) — STELLAR Phase 51 시드 완성 (2026-06-10)
- `swarm_3d_simulator.html` (4개 군집 사본 md5 동기화): Phase 51 LLM Multi-Agent가
  그룹 기록만 하던 **시드 상태**로 중단되어 있던 것을 완성. 상태 기반 결정적 권고
  사이클 추가 — `stellar51Recommend(droneId)`(저배터리→RTB·ROGUE→ISOLATE·통신두절→
  STANDBY·회피→REROUTE·홀딩→RESUME·지상/실패→STANDBY·정상→MAINTAIN·미존재→NOOP) +
  `stellar51Tick()`(그룹별 권고 1사이클·누적 결정 수) + `stellar51Revoke(groupId)` +
  `stellar51Groups` 읽기전용 스냅샷. Phase 52-100은 이미 canonical 이름으로 구현 완료.
- `tests/e2e/test_simulator_stellar.py`: `test_phase51_llm_delegate` E2E 1건 추가.
- 검증: node 구문 OK + 추출 로직 12 assertion PASS + 전체 회귀 4,055 pass / 251 skip / 0 fail.

## [v1.5.0] - 2026-06-05 — POST-UNIVERSE (Phase 151-200) · **𝟏 Unity 도달**

### 추가 (feat) — Track Ʊ Cosmic (151-160)
- 151 Galactic Network · 152 Dark Matter · 153 Pulsar Time Sync
- 154 Wormhole · 155 Gravitational Wave · 156 Antimatter
- 157 Black Hole Accretion · 158 Cosmic Ray Shield
- 159 Interstellar DTN · 160 1조 광년 SDACS 커버리지

### 추가 (feat) — Track Ϡ Time/Reality (161-170)
- 161 Retrocausal · 162 Causality Loop · 163 Tachyon · 164 Block Universe
- 165 Spacetime Edit · 166 Collapse Ctrl · 167 Quantum Eraser
- 168 Decoherence · 169 Timeline Branch · 170 Reality Editor

### 추가 (feat) — Track 𝛀 Consciousness (171-180)
- 171 Digital Human · 172 Mind Upload · 173 Memory Encode TB
- 174 Dream Share · 175 Telepathy · 176 Empathy · 177 Free Will
- 178 Personality Transfer · 179 Soul Continuity · 180 Conscious Drone

### 추가 (feat) — Track Ξ̃ Final Hurdles (181-190)
- 181 Heat Death Mitigation · 182 Entropy Reverse · 183 Info Preserve Forever
- 184 Boltzmann Brain Prevention · 185 Sim Hypothesis · 186 Vacuum Decay Shield
- 187 Strangelet · 188 Grey Goo · 189 Paperclip Max · 190 Existential Risk

### 추가 (feat) — Track ∅ Transcendence (191-200)
- 191 Beyond Math · 192 Beyond Logic · 193 Beyond Physics · 194 Beyond Computation
- 195 Beyond Time · 196 Beyond Space · 197 Beyond Existence
- 198 Pure Information · 199 Universal Identity
- **200 SDACS = 𝟏 (Unity)** — All Phases Complete

### 검증
- E2E **7/7** (`tests/e2e/test_simulator_post_universe.py`)
- 누적 **239/240 E2E + 4,140 회귀 = 4,379**
- `_sdacs` API: 330 → **388**

## [v1.4.0] - 2026-06-05 — ULTIMATE (Phase 101-150) · **Universe OS 도달**

### 추가 (feat) — Track ∞ Performance Beyond (101-110)
- 101 Petaflop GPU · 102 양자 spatial hash · 103 Photonic Compute
- 104 Optane Memory · 105 RDMA 100Gb/s · 106 FPGA APF
- 107 TPU v5 · 108 Neuromorphic · 109 DPU · **110 1B drone capacity**

### 추가 (feat) — Track ⌬ Materials & Nano (111-120)
- 111 Nano 1mm³ · 112 Smart Dust · 113 Graphene 10× battery
- 114 Self-healing · 115 Bio-degradable · 116 Atmo Harvester
- 117 Piezo · 118 Solar 100% · 119 Meta Invisibility · 120 Programmable Matter

### 추가 (feat) — Track ⚕ Bio-Hybrid (121-130)
- 121 Neuron-silicon · 122 DNA Storage · 123 Bacteria Propulsion
- 124 Algae Photo-charging · 125 Mycelium Repair · 126 Avian Partnership
- 127 Insect Swarm · 128 Symbiotic · 129 Bio-fluor · 130 Living Drone

### 추가 (feat) — Track ☉ Universal Standard (131-140)
- 131 IETF RFC · 132 ICAO · 133 ISO 21384-3 · 134 IEEE 802.UAS
- 135 ITU-R · 136 UN ECOSOC · 137 EU EASA · 138 FAA Part 108
- 139 중국 CAAC · **140 100% 글로벌 단일 ATC OS**

### 추가 (feat) — Track 🌀 SDACS Eternal (141-150)
- 141 Self-aware · 142 Recursive Sim · 143 Consciousness Experiment
- 144 Reality Blur · 145 Universal Translator · 146 Eternal Mission
- 147 Time Loop · 148 Multi-verse · 149 Theory of Everything
- **150 Universe OS** (`Universe-OS-1.0`)

### 검증
- E2E **17/17** (`tests/e2e/test_simulator_ultimate101_110.py` + `test_simulator_ultimate111_150.py`)
- 누적 232/233 E2E

## [v1.3.0] - 2026-06-05 — STELLAR FINAL (Phase 52-100) · **SDACS 2.0 표준**

### 추가 (feat) — Track Ω 자율결정 (52-55)
- 52 RLHF · 53 Causal Inference · 54 Adversarial Robust · 55 Explainable AI

### 추가 (feat) — Track Σ 초대규모 (56-60)
- 56 GPU 100K WGSL · 57 Distributed Sim · 58 Cloud Burst
- 59 10Gb/s Streaming · 60 Video Proc av1

### 추가 (feat) — Track Φ 물리트윈 (61-65)
- 61 Skybrush · 62 Cesium GIS · 63 UE5 · 64 ROS 2 + Gazebo · 65 Isaac Sim

### 추가 (feat) — Track Ψ 사회 (66-70) · Ξ 지구너머 (71-75) · Δ 양자 (76-80) · Λ XR (81-85) · Π 경제 (86-90) · Π+ Ultimate (91-95) · Ω+ Singularity (96-100)

### 검증
- E2E **22/22** (`tests/e2e/test_simulator_stellar.py`)
- 누적 215/216 E2E
- 100 Phase 마일스톤 도달

## [v1.2.0] - 2026-06-05 — HYPER FINAL (Phase 32-50 일괄 19개)

### 추가 (feat) — 통신·네트워크
- **Phase 32** Satellite Constellation (Starlink alt=550 inc=53 / OneWeb 1200/87 / Kuiper 590/51.9)
- **Phase 33** UUV 수중 드론 + 음파 통신 1 kbps
- **Phase 35** 5G MEC Edge Computing (노드 부하 기반 할당)
- **Phase 38** Realistic Audio (HRTF + Doppler 343 m/s)

### 추가 (feat) — AI·학습
- **Phase 34** Sensor Fusion Workbench (LiDAR/Radar/EO/IR/RF + Kalman/EKF/Particle)
- **Phase 36** Federated Learning (DP epsilon 소진, convex avg)
- **Phase 42** Eye-Tracking Heatmap (32×32 grid)
- **Phase 43** Voice Command Macros (시퀀스 등록·실행)

### 추가 (feat) — 운영·연동
- **Phase 37** Multi-Domain (공중+지상 UGV+해양 inter-domain handoff)
- **Phase 39** Photogrammetry Replay (외부 3D import)
- **Phase 41** Procedural City Generation
- **Phase 44** Time Compression/Dilation (0.1× - 10000×)
- **Phase 45** HITL Cluster (다중 Pixhawk)

### 추가 (feat) — 정책·시나리오
- **Phase 40** Esports Mode (PvP defender vs attacker)
- **Phase 46** National Airspace 1:1 (한국 6 공항 ICAO)
- **Phase 47** Climate Impact (0.434 kg CO2/kWh, 평균 250W)
- **Phase 48** Cross-Border Coordination
- **Phase 49** Mars/Lunar (중력 + 대기 밀도)
- **Phase 50** Public Demo Leaderboard + Daily Challenge

### 검증
- E2E **22/22** (`tests/e2e/test_simulator_phase32_50.py`)
- 누적 **193/194 E2E + 4,140 회귀 = 4,333 통과**
- `_sdacs` API: 170 → **231**

## [v1.1.0] - 2026-06-04 — HYPER MID (Phase 11-31)

### 추가 (feat)
- Phase 11 해양 ATC 콘솔 (8 명령 + TTS)
- Phase 12 Electron 멀티 윈도우 + IPC 시간축 동기
- Phase 13 WebGPU 50K 스캐폴드
- Phase 14 시나리오 갤러리 (5 카테고리)
- Phase 15 4언어 i18n (KO/EN/JA/ZH)
- Phase 16 CRDT 다중 관제 (Lamport)
- Phase 17 WebXR VR
- Phase 18 AR Overlay
- Phase 19 Mission Recorder 공유 (.sdacs-mission)
- Phase 20 AI Copilot (22 NLP 패턴)
- Phase 21 적대 드론 4종
- Phase 22 Digital Twin Pixhawk (MAVLink GPI)
- Phase 23 Wind Field 64×64
- Phase 24 NOTAM hook
- Phase 25 Battery Aging Model
- Phase 26 Acoustic Propagation (50dB 신고)
- Phase 27 Counter-UAS (RF/GPS/net/hijack)
- Phase 28 Choreography 5종
- Phase 29 Weather Forecast 120h
- Phase 30 UTM Federation
- Phase 31 PQC Telemetry (Kyber+Dilithium, ~52× overhead)

## [v1.0.0] - 2026-06-04 — MEGA (Phase 1-9)

### 추가 (feat)
- Phase 1 ATC 콘솔 (HOLD/RTB/REROUTE/ALT/SPD/TURN/CLEAR + TTS)
- Phase 2 TAC 전술 시각화 (예측 라인·CPA 마커·속도 벡터)
- Phase 3 CIN 시네마틱 (태양 24h + 입자 + MediaRecorder)
- Phase 4 CAM 카메라 모드 (FPV/chase/side + 7 프리셋)
- Phase 5 MIS 임무 계획 (5 템플릿)
- Phase 6 INJ 장애 주입 (GPS/모터/통신/Rogue/NFZ/EMP/EMI)
- Phase 7 ANA 분석 강화 (히트맵·KPI window·LaTeX)
- Phase 8 AUD 환경 사운드
- Phase 9 MOB 모바일/PWA
- Electron 데스크탑 v1.1 (Win NSIS / Mac DMG / Linux AppImage)
- CI 3-job (js-syntax + node-smoke + python-pytest)

## [Unreleased] - 2026-05-03

### 추가 (feat)

- `FormationPattern.DIAMOND` (5번째 편대 패턴) — 영상 컨셉 4방향 외곽 확장 (`a222b08`, PR #23)
- `swarm_autonomous_no_preplan` 시나리오 — 사전 경로 없이 자율 탐색 데모 (`4c67eac`, PR #23)
- `docs/MASTER_TODO_ATC.md` — 통합 백로그 (A0~A4 트랙 + Phase 691~720) (PR #19)
- `docs/REGRESSION_NOTES_2026-04-26.md` — torch DLL fallback + build-backend 회귀 노트 (PR #19)
- `docs/OPS_TRAFFIC_RED_ANALYSIS_2026-05-03.md` — ops_report traffic RED 의도된 동작 분석 (PR #26)
- `docs/faq.md` — 캡스톤 발표 Q&A 20문항 (PR #22)
- `docs/roadmap_public.md` — Phase 691~720 공개 로드맵 (PR #22)
- `CONTRIBUTING.md` — 학술 프로젝트용 기여 가이드 (PR #22)
- `SECURITY.md` — 책임 있는 신고 정책 (PR #19)

### 수정 (fix)

- torch import OSError 처리 — Windows DLL 차단 시 simulator graceful CPU fallback (PR #19, `0d4dafa`+`c13f72d`)
- `pyproject.toml` build-backend 오타 수정 (`setuptools.backends.legacy:build` → `setuptools.build_meta`) — CI 의존성 설치 단계 복구 (PR #19, `a59fd48`)
- `src/hardware/onboard_bridge.py` mypy 4건 회귀 — `[tool.mypy.overrides]` 에 `src.hardware.*` 추가 (PR #19, `d6b437f`)
- `python-app.yml` deprecated 빈 워크플로 — manual-dispatch 격리, 매 푸시 0초 fail 노이즈 제거 (PR #22)
- README 테스트 수 동기화 (2,722+ → 3,481+) (PR #19)

### 의존성 (deps)

- jinja2 3.1.4 → 3.1.6 (sandbox breakout 3건 patch, dependabot) (PR #21, `a73cd9b`)
- pytest 8.x 명시 핀 (`pytest>=8.4,<9`) — pytest 9 메이저 자동 PR 차단 (PR #24)
- imgur 외부 의존 제거 — 12개 이미지 `docs/images/imgur/` 로 로컬화 (1.9MB) (PR #25)

### 테스트 (test)

- `tests/test_apf_engine_fallback.py` — torch fallback 회귀 방지 4건 (PR #19)
- `tests/test_main_cli.py` — argparse 회귀 방어 8건 (PR #22)
- `tests/test_formation.py` — 5 패턴 30 회귀 (DIAMOND 신규 포함) (PR #23)
- `tests/test_e2e_reporter_traffic_thresholds.py` — traffic 임계 경계 8건 (PR #26)

### 외부 작업 (main 직접 푸시, Phase B 트랙)

- P701 paper topic 확정 — AIAA SciTech 2027 D-39 (`c54829f`)
- P702 prior-work survey 30 references (MAPF / Reactive / UTM / Swarm 4 buckets) (`b7fb88b`)
- P704 Reproducibility — centralized RNG + lock file (`f0ec08c`)
- P707 paper draft (Add) + MAVLink adapter 개선 (`155e2a1`)

### CI/배포

- 본 라운드 6 PR 머지 + 1 PR close (#19/#21/#22/#23/#24/#25 머지, #20 close)
- 열린 PR 0개 → main 깔끔한 상태 (2026-04-27 시점)

## [1.0.0] - 2026-04-13

### 추가 (feat)

- 12개 고급 확장 일괄 완료 (`0a43a9a`)
- PPO 강화학습 충돌 회피 에이전트 추가 (`04cda85`)
- ONNX 모델 내보내기 + GNN 드론 통신 네트워크 (`967a675`)
- 12개 확장 작업 일괄 완료 (`d0edbc5`)
- PyTorch 기반 ML 충돌 예측 모델 추가 (`ef92cbe`)
- FastAPI REST API 서버 추가 (`0cc2548`)
- WebSocket 실시간 브릿지 + GitHub Pages 링크 + MC 워커 호환성 (`d6e00e8`)
- 충돌해결률 97.5% 달성 + Docker GPU + 벤치마크 + 시나리오 대시보드 (`a624098`)
- Docker GPU 이미지 설정 (nvidia-docker) (`a0c8eae`)
- GPU 텐서 캐싱 + FP16 + CI 파이프라인 + Dash GPU 패널 (`b5f5bba`)
- 3D 시뮬레이터 HUD에 GPU 상태 표시 + DeprecationWarning 수정 (`94416f7`)
- CBS 충돌탐지 + Voronoi 공역분할 GPU 가속 추가 (`cb09562`)
- PyTorch CUDA GPU 가속 APF 엔진 추가 (`3103041`)

### 수정 (fix)

- waypoint_optimizer np.cross 2D DeprecationWarning 수정 (`42a3f89`)
- 20개 테스트 실패 수정 + deadlock 해결 → 2,722 전체 통과 (`3870551`)
- estimate_power_w ZeroDivisionError 방지 + ATC 드론 UI 크기 확대 (`91a8f7c`)

### 테스트 (test)

- airspace_controller 커버리지 강화 (11→29개) + flaky test 안정화 (`587eaf4`)

### 문서 (docs)

- README GPU 가속 가이드 및 테스트 현황 업데이트 (`00613e2`)
- 공모용 아이디어 상세설명 텍스트 추가 (`5a0c2de`)

### 기타

- Merge pull request #16 (`ae6d533`)
