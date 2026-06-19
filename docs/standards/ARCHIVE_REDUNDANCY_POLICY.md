# 아카이브 이중화 — 단일 실패점 없는 장기 보존 정책

> ODYSSEY Phase 489 (Continuum 트랙). 실행 가능 명세: [`simulation/archive_redundancy.py`](../../simulation/archive_redundancy.py)

## 목적

졸업 후 10년, 프로젝트가 **단일 보관처의 실패로 소실되지 않으려면** 서로
독립적인 보관처에 사본이 있어야 한다. GitHub 리포 하나에만 의존하면 계정
정지·조직 삭제·서비스 종료 한 번으로 전체가 사라진다. "현재 아카이브
이중화가 단일 실패점(single point of failure) 없이 충분한가"를 매번 직관으로
판단하면 일관성이 없다. 본 정책은 그 판단을 **결정적 규칙**으로 명문화한다.

이 문서는 규칙을 *서술*할 뿐이며, **유일한 권위 있는 명세는
`simulation/archive_redundancy.py` 의 `assess_redundancy()`** 다. 본 문서와
코드가 어긋나면 코드가 옳고, 테스트(`tests/test_archive_redundancy.py`)가
둘의 일치를 강제한다.

## 핵심 원칙

1. **자문이지 집행이 아님** — 본 모듈은 *현 상태를 판정*할 뿐 실제로 사본을
   업로드하지 않는다(부수효과 0). 실제 예치는 사람/CI 가 집행한다.
2. **위치자 없는 주장은 예치가 아님** — 식별자(DOI·SWHID·핸들)가 없거나
   형식이 어긋난 예치 주장은 *검증됨(VERIFIED)* 으로 인정하지 않는다.
   "어딘가 올렸다"는 주장만으로는 10년 후 찾을 수 없기 때문이다(정직성).
3. **독립 보관처 우선** — 같은 기관(custodian)에 사본이 둘이어도 단일
   실패점이다. 이중화는 *서로 다른 custodian* 으로 세며, 코드·데이터 두
   차원을 모두 덮어야 충분(`REDUNDANT`)하다.

## 보관처(아카이브)와 운영 기관(custodian)

| 아카이브 | custodian | 식별자 | 형식 |
|---|---|---|---|
| `zenodo` | CERN | 버전 DOI | `10.5281/zenodo.<digits>` |
| `software_heritage` | Inria | SWHID (core) | `swh:1:(cnt\|dir\|rev\|rel\|snp):<40 hex>` |
| `institutional` | 대학(기본 `university`) | Handle | `<prefix>/<suffix>` |

독립성은 **custodian** 으로 센다. 같은 custodian 에 사본이 둘이면 그 기관의
실패가 둘을 동시에 가져가므로 독립 보관처 **1곳**으로 집계한다. 기관
리포지터리가 여럿이면 `custodian` 을 명시해 서로 다른 기관으로 구분한다.

## 보존 차원

| 차원 | 의미 |
|---|---|
| `code` | 소스 코드 스냅샷 — 재빌드 가능성 |
| `data` | 결과·데이터·문서 산출물 — 재현 검증 가능성 |

## 예치 판정 (`deposit_state`, 먼저 매칭되는 규칙이 결과)

1. 알 수 없는 아카이브/상태/차원 → `INVALID`
2. 차원 미지정 → `INVALID` (무엇을 보존하는지 불명)
3. 상태 `planned` → `PENDING` (아직 사본 아님)
4. 상태 `deposited`/`verified` 이나 식별자 무효/누락 → `INVALID`
5. 식별자 유효 → `VERIFIED`

## 이중화 판정 매트릭스 (`assess_redundancy`)

`VERIFIED` 예치만 내구 사본으로 집계한다. 행은 *독립 custodian 수*, 열은
*코드·데이터 두 차원 모두 덮였는가*.

| 독립 custodian | 양차원 미덮음 | 양차원 덮음 |
|---|:-:|:-:|
| **0** | AT_RISK | AT_RISK |
| **1** | PARTIAL | PARTIAL |
| **≥2** | PARTIAL | **REDUNDANT** |

- **REDUNDANT** — 단일 실패점 없음. 독립 custodian ≥2곳 + 코드·데이터 두
  차원 모두 검증된 사본으로 덮임.
- **PARTIAL** — 내구 사본은 있으나 기준 미달(custodian 부족 또는 차원 누락).
- **AT_RISK** — 검증된 내구 사본 0. 단일 리포 의존, 소실 위험.

## 사용

```bash
python -m simulation.archive_redundancy --policy     # 정책 매트릭스 출력
python -m simulation.archive_redundancy --demo       # 이중화 달성 예시 평가
python -m simulation.archive_redundancy --status     # 리포 현 상태 정직 공시
python -m simulation.archive_redundancy --manifest   # 정책 매니페스트(JSON)
```

프로그래매틱 사용:

```python
from simulation.archive_redundancy import (
    ArchiveDeposit, KIND_CODE, KIND_DATA, STATUS_VERIFIED, assess_redundancy,
)

deposits = (
    ArchiveDeposit("zenodo", (KIND_CODE, KIND_DATA),
                   identifier="10.5281/zenodo.1234567", status=STATUS_VERIFIED),
    ArchiveDeposit("software_heritage", (KIND_CODE,),
                   identifier="swh:1:dir:" + "a" * 40, status=STATUS_VERIFIED),
)
print(assess_redundancy(deposits).summary())
# REDUNDANT: 독립 custodian 2곳(CERN, Inria) · 차원 code, data
```

## 리포 현 상태 (정직성 공시)

본 작성 시점에서 `.zenodo.json`·`CITATION.cff`·`docs/REPRODUCIBILITY.md`
메타데이터는 준비되어 있으나, **첫 릴리스 태그 전이라 Zenodo DOI 가
발급되지 않았고**(`.zenodo.json` notes 에 명시) Software Heritage SWHID·기관
핸들도 미확인이다. 따라서 `shipped_registry()` 의 정직한 현 판정은:

```
판정: AT_RISK — 검증된 내구 사본 0 (단일 리포 의존)
```

메타데이터 준비를 예치 완료로 포장하지 않는다. `REDUNDANT` 로 가려면 최소
다음이 필요하다:

1. **GitHub Release 태그** → Zenodo 가 자동으로 버전 DOI 발급 (code+data).
2. **Software Heritage `Save Code Now`** → 리포 SWHID 확인 (code).
3. (선택) 대학 기관 리포지터리에 보고서·데이터 예치 → 핸들 (data).

1+2 만 완료해도 독립 custodian 2곳(CERN·Inria) + 양차원 → `REDUNDANT`.

## 범위 밖 (정직성 공시)

- 본 모듈은 **사본을 실제로 업로드하지 않는다.** 예치 집행(Zenodo 연동·SWH
  저장 요청)은 별도 자동화가 필요하며 본 Phase 범위 밖이다.
- 식별자 *형식*만 검증하며, 그 DOI/SWHID 가 실제로 *해석(resolve)되는지*
  네트워크로 확인하지는 않는다(샌드박스 결정성 유지). 온라인 해석 검증은
  별도 Phase 후보.
- 보존 *주기성*(연 1회 재예치 리허설)은 Phase 486 범위다.
