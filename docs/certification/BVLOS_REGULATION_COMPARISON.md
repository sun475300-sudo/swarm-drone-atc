# 다국 BVLOS 규제 비교 — 한·미·EU·일 (Phase 409, ODYSSEY)

> **목적**: BVLOS(가시권 밖, Beyond Visual Line of Sight) 무인비행장치 운영 요건을
> 4개 관할권에 걸쳐 횡단 비교하여, SDACS 운영 프로파일의 관할권별 적합성 갭을
> 결정적으로 산정한다.
>
> **범위·면책**: 본 문서와 `simulation/bvlos_regulation_compare.py` 는 2026-06 기준
> 공개 규제 프레임워크의 *스냅샷 모델*이며 **교육·시뮬레이션 목적**이다. 권위 있는
> 법령 텍스트가 아니며 법률 자문을 대체하지 않는다. 실제 운영 전 각 관할권 규제기관의
> 최신 고시를 확인해야 한다.

GENESIS 302(SORA `soraAssess`)·408(ICAO 공역 클래스 매핑)·`faa_laanc`·`icao_doc10019`
규제 자산이 **단일 관할권** 적합성을 다룬 반면, 본 Phase 는 4개 관할권 요건을
**비교**하는 결정적 데이터 모델 + 적합성 갭 산정 API 를 제공한다.

## 1. 비교 매트릭스

| 요건 | 🇰🇷 대한민국 | 🇺🇸 United States | 🇪🇺 EU (EASA) | 🇯🇵 日本 |
|---|---|---|---|---|
| 규제 프레임워크 | 항공안전법 §129 / 드론활용촉진법 | 14 CFR Part 107 §107.31 + Part 108(NPRM) + Part 89 | EU 2019/947 Specific + SORA (JARUS) | 改正航空法 (2022) Level 4 |
| 승인 방식 | 특별비행승인 (BVLOS·야간), Drone One-Stop | BVLOS waiver / BEYOND (Part 108 정규화) | 운영 승인 / LUC / PDRA | 飛行 허가·승인 (DIPS) |
| 조종자 자격 | 무인비행장치 조종자격 (1~4종) | Remote Pilot Certificate (Part 107) | 원격조종자 (STS/PDRA), LUC | 一等/二等 無人航空機操縦士 |
| 기체 인증 | 기체 신고 + 안전성 인증 (25kg 초과) | 기체 등록 (Part 47/48) | UAS Class (C0~C6) | 第一種/第二種 機体認証 |
| Remote ID 의무 | ✅ | ✅ (Part 89, ASTM F3411) | ✅ (Class C) | ✅ (登録記号 + リモートID) |
| Detect-And-Avoid 의무 | ✅ | ✅ | ✅ | ✅ |
| 보험 의무 | ✅ (사업용) | ❌ (연방 의무 아님) | ✅ (EC 785/2004) | ✅ (허가 조건) |
| 기본 고도 상한 (m AGL) | 150 | ≈121.9 (400 ft) | 120 | 150 |
| 사람 위 비행 (기본) | ❌ (별도 승인) | ✅ (Ops Over People) | ❌ (SORA 등급) | ✅ (Level 4) |

> 고도 상한은 각 관할권 **기본값**이며, 특별비행승인(KR)·waiver(US)·SORA 등급(EU)·
> Level 4 인증(JP)으로 상향 가능하다.

## 2. 관할권별 BVLOS 경로 요약

- **🇰🇷 KR** — 항공안전법 §129 특별비행승인으로 BVLOS/야간/고도초과를 일괄 허가받는다.
  K-드론시스템 UTM 연동이 전제이며, 인구밀집지역은 별도 승인이 필요하다.
- **🇺🇸 US** — Part 107 §107.31 BVLOS waiver 또는 BEYOND 프로그램을 통해 운영하며,
  Part 108 NPRM 으로 BVLOS 정규화가 진행 중이다. Remote ID(Part 89)는 의무화 완료.
- **🇪🇺 EU** — Specific 카테고리에서 SORA(JARUS)로 운영 위험 등급(SAIL+ARC)을 산정해
  운영 승인 또는 LUC 를 획득한다. PDRA(사전정의 위험평가)로 절차를 단축할 수 있다.
- **🇯🇵 JP** — 改正航空法 Level 4 는 第一種機体認証 + 一等無人航空機操縦士 + 運航管理
  매뉴얼을 갖추면 제3자 위 유인지대 BVLOS 가 허용된다.

## 3. API (`simulation/bvlos_regulation_compare.py`)

| 함수 | 설명 |
|---|---|
| `get_regulation(code)` | 관할권 코드(KR/US/EU/JP)로 `BvlosRegulation` 조회 |
| `compare_field(field)` | 단일 요건 필드를 4개국 횡단 비교 |
| `comparison_matrix()` | `COMPARISON_FIELDS` 전체 비교 매트릭스 (결정적) |
| `assess_conformance(profile, code)` | 운영 프로파일 ↔ 단일 관할권 적합성 갭 산정 |
| `assess_all(profile)` | 4개국 전체 적합성 일괄 산정 |
| `to_markdown_table()` | 비교 매트릭스 마크다운 표 (대시보드/문서 피드) |
| `to_dict()` | 전체 규제 테이블 JSON 직렬화 |

### 적합성 갭 산정 규칙

`OperationProfile`(고도·Remote ID·DAA·조종자/기체 인증·보험·사람 위 비행)을 입력하면,
각 관할권 요건과 대조해 미충족 항목을 `ConformanceResult.gaps` 로 표면화한다.
관할권별 차이가 산정에 반영된다 — 예: 보험 미가입은 KR/EU/JP 에서만 갭, US 는 적합;
고도 130 m 는 EU(120)·US(122)에서 초과, KR/JP(150)는 적합.

## 4. 결정성·검증

- 난수·외부 호출 0 (정적 데이터 + 순수 함수), frozen dataclass 로 불변.
- 단위 테스트 `tests/test_bvlos_regulation_compare.py` — 19건 PASS
  (테이블 무결성·조회·필드 비교·갭 산정·export 라운드트립).

## 5. 차기 격상 제안

- (409→409+) EU STS-01/STS-02·미 Part 108 확정안 반영 시 테이블 갱신.
- 규제 비교 매트릭스를 시뮬레이터 `_sdacs.bvlosCompare()` JS API 로 노출 (대시보드 시각화).
