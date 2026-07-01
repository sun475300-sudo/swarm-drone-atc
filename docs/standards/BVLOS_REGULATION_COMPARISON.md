# 다국 BVLOS 규제 비교 (한·미·EU·일) — ODYSSEY Phase 409

드론 BVLOS(Beyond Visual Line of Sight, 가시권 밖 비행) 운용을 허가하는 4개 관할의
규제 요건을 **동일한 비교 축(axis)** 으로 정렬해 대조한 기준 문서입니다.
정본 데이터는 `simulation/bvlos_regulation_compare.py` 가 보유하며, 본 문서는 그
요약과 활용 맥락을 제공합니다.

> **정직 공시**: 본 비교는 규제의 *기능적 요약* 이며 법률 자문이 아닙니다. 각 요건은
> 권위 있는 공개 규제 문서를 인용하고, 관할별 스냅샷 시점(`as_of = 2026-06`)을
> 명시합니다. 규제는 개정되므로 실제 운용 전 최신 원문을 확인해야 합니다.

## 비교 축 (6종)

| 축 id | 라벨 |
|---|---|
| `bvlos_pathway` | BVLOS 법적 허가 경로 |
| `risk_assessment` | 운영 위험 평가 방식 |
| `remote_id` | Remote ID(원격 식별) 요건 |
| `pilot_competency` | 조종 자격(라이선스) 요건 |
| `aircraft_cert` | 기체 인증 요건 |
| `over_populated` | 인구 밀집지/제3자 상공 BVLOS |

## 관할 요약

| 관할 | 프레임워크 | 당국 | BVLOS 경로 핵심 |
|---|---|---|---|
| **KR 대한민국** | 항공안전법 + 특별비행승인 | 국토교통부(MOLIT) | 포괄 규칙 부재 — 건별 특별비행승인 |
| **US 미국** | 14 CFR Part 107 + Waiver (Part 108 NPRM) | FAA | §107.31 금지 → Waiver 면제 |
| **EU 유럽연합** | Reg. (EU) 2019/947 | EASA | Specific 카테고리 — SORA/STS-02 |
| **JP 일본** | 改正航空法 (Level 4) | 国土交通省(MLIT) | Level 4 — 기체인증+라이선스+운항허가 |

## 핵심 대조 포인트

- **허가 모델의 차이**: 한국·미국은 *건별 승인/면제* 중심(포괄 BVLOS 규칙 미발효),
  EU 는 *위험 기반 카테고리*(SORA), 일본은 *3중 인증 요건*(기체+조종사+운항)으로
  Level 4 를 제도화한 점이 대비됩니다.
- **Remote ID**: 4개 관할 모두 원격 식별을 요구하나, EU 는 Direct + Network
  (U-space) 이중, 미국은 Part 89 표준/모듈/FRIA 3경로로 세분됩니다.
- **인구 밀집지 비행**: 일본 Level 4 가 제3자 상공 BVLOS 를 가장 명시적으로
  제도화(1종 기체 + 1등 라이선스 + 운항허가)한 반면, 미국은 Operations Over
  People 4범주, EU 는 SORA iGRC 로 지상 위험을 정량 평가합니다.

## SDACS 자가 평가/지원 커버리지

본 모듈은 각 관할 요건의 *자가 평가/지원* 에 실재로 쓰이는 리포 모듈을 가리키며,
대응 모듈이 없으면 `None` 으로 **갭** 을 표면화합니다(`test_cited_sdacs_modules_exist_on_disk`
가 인용 경로의 디스크 실재를 강제).

| 관할 | SDACS 지원 모듈 |
|---|---|
| KR | `simulation/special_flight_approval.py` |
| US | `simulation/flight_plan_filing.py` |
| EU | `simulation/airspace_class.py` |
| JP | — (**갭**) |

지원 관할: **3/4 (75%)**.

## 활용 (CLI)

```bash
python simulation/bvlos_regulation_compare.py --matrix              # 전체 비교 매트릭스
python simulation/bvlos_regulation_compare.py --jurisdiction JP     # 관할별 요건
python simulation/bvlos_regulation_compare.py --dimension remote_id # 축별 전 관할 대조
python simulation/bvlos_regulation_compare.py --support             # SDACS 지원 갭
```

`comparison_matrix()` 는 도구 간 교환용 JSON 행(축별 전 관할 요건/인용)을 반환하므로,
다른 분석 도구가 SDACS 의 규제 비교 데이터를 기계 판독할 수 있습니다.

## 연계 Phase

- Phase 401 (EASA U-space 서비스 매핑) · 403 (EASA 운영 카테고리)
- Phase 402 (FAA UTM ConOps) · 407 (ICAO UTM Framework)
- Phase 408 (국제 공역 분류 A-G) · 406 (다국 좌표계)

본 Phase 는 위 자가 평가 모듈과 비경쟁(상호 보완)이며, 관할 *간* 요건 대조라는
별도 축을 제공합니다.
