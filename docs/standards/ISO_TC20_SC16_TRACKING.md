# ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스

> **ODYSSEY Phase 462** · 자동 생성 출처: [`simulation/iso_uas_standards.py`](../../simulation/iso_uas_standards.py)
> *as of 2026-06-19*

국제표준화기구(ISO) 항공우주기술위원회(TC 20) 산하 무인항공기시스템 분과위원회
(SC 16, *Unmanned aircraft systems*)가 발행하는 UAS 표준군을 추적하고, 각 표준의
**주제(theme)** 를 SDACS 의 어느 모듈이 다루는지 결정적으로 대응시킵니다.

Phase 470(표준화 기고 추적)이 SDACS 가 *내보내는* 자체 기고를 추적한다면, 본
매트릭스는 SDACS 가 *마주하는* 외부 ISO 표준 지형을 추적하고, 그 지형 대비 현재
시스템의 주제 커버리지를 표면화합니다.

## 정직 공시

1. 본 매트릭스는 **주제 정렬(thematic alignment)** 추적이며 ISO 공식 적합성
   인증이 아닙니다. `커버리지` 는 "이 표준의 주제를 SDACS 의 어느 모듈이
   다루는가" 일 뿐, 표준의 세부 요구사항을 인증 수준으로 충족한다는 주장이
   아닙니다.
2. 표준 지정번호·발행 성숙도는 **지식 기준일(2026-06-19) 시점 스냅샷**입니다. ISO
   카탈로그는 갱신(개정·발행·폐지)되므로 인용 전 공식 카탈로그로 검증해야 합니다.
   본 매트릭스의 가치는 정확한 발행 연도보다 *어떤 표준 주제가 미커버(gap)인지* 의
   가시화에 있습니다.
3. `SDACS 모듈` 은 그 주제를 **실제로** 다루는 리포 내 모듈 경로입니다. 커버리지가
   `none` 이면 모듈을 인용하지 않으며, `full`/`partial` 이면 반드시 실재 모듈을
   인용합니다 — 모듈 없는 커버리지 주장은 구조적으로 금지되고
   `iso_uas_standards.validate()` 가 디스크 실재를 강제합니다.

## 커버리지 등급

| 등급 | 의미 | 가중치 |
|---|---|:-:|
| `full` | 표준의 주제를 핵심 도메인으로 구현 | 1.0 |
| `partial` | 주제를 부분 대응(완전 요구 매핑은 미완) | 0.5 |
| `none` | SDACS 범위 밖 또는 미구현 (gap) | 0.0 |

## 추적 매트릭스

| 지정번호 | 제목 | 범주 | 성숙도 | 커버리지 | SDACS 모듈 |
|---|---|---|---|:-:|---|
| ISO 21384-1 | UAS — Part 1: General specification | general | published | none | — |
| ISO 21384-2 | UAS — Part 2: UA systems requirements | product | published | none | — |
| ISO 21384-3:2023 | UAS — Part 3: Operational procedures | operations | published | full | src/airspace_control/controller/airspace_controller.py |
| ISO 21384-4 | UAS — Part 4: Vocabulary | terminology | published | none | — |
| ISO 23629-5 | UTM — Part 5: UAS Service Provider (USP) functional structure | utm | published | partial | simulation/faa_uss_roles.py |
| ISO 23629-7:2021 | UTM — Part 7: Data model for spatial data | utm | published | partial | simulation/geo_zones.py |
| ISO 23629-12 | UTM — Part 12: Requirements for UTM service providers | utm | under_development | partial | simulation/icao_utm_conformance.py |

**주제 커버리지 점수**: 35.7% (7건, as of 2026-06-19)

## 해석

- **운영 절차(ISO 21384-3)** 는 SDACS 의 핵심 도메인으로 완전 대응합니다 — 공역
  관제·승인·분리 운영을 `AirspaceController` 1Hz 로 구현합니다.
- **UTM 계열(ISO 23629-5/-7/-12)** 은 부분 대응합니다 — USS 역할 매핑·좌표계
  판정·UTM 적합성 자가 평가가 각 표준 주제와 정렬되나, ISO 요구사항 전수 매핑은
  후속 작업입니다.
- **기체 제품 사양(ISO 21384-1/-2)·용어(ISO 21384-4)** 는 SDACS 범위 밖이거나
  별도 통제 어휘집을 발행하지 않아 정직하게 gap 으로 표시합니다 — 본 매트릭스의
  가치는 이 미커버 영역의 가시화에 있습니다.

## 재생성

```bash
python -m simulation.iso_uas_standards --markdown   # 본 표 재생성
python -m simulation.iso_uas_standards --report     # 커버리지 요약
python -m simulation.iso_uas_standards --gaps        # 미커버(gap) 표준
python -m simulation.iso_uas_standards --validate    # 레지스트리 정합성
```
