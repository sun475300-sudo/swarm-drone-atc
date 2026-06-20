# 디지털 유산 — 10년 후 재현 가능성 체크리스트

> ODYSSEY Phase 490 (Continuum 트랙). 실행 가능 명세: [`simulation/legacy_readiness.py`](../../simulation/legacy_readiness.py)

## 목적

졸업 후 10년, 원저자가 손을 뗀 뒤에도 이 프로젝트가 **재현 가능하고 인용
가능하며 법적으로 사용 가능한** 상태로 살아남는가? "충분히 인계 준비가
됐는가"를 매번 직관으로 판단하면 일관성이 없다. 본 정책은 그 판단을
**결정적 체크리스트**로 명문화한다 — 같은 리포 상태는 항상 같은 판정을 낸다.

이 문서는 규칙을 *서술*할 뿐이며, **유일한 권위 있는 명세는
`simulation/legacy_readiness.py` 의 `assess_legacy_readiness()`** 다. 본 문서와
코드가 어긋나면 코드가 옳고, 테스트(`tests/test_legacy_readiness.py`)가 둘의
일치를 강제한다.

## 핵심 원칙

1. **자문이지 집행이 아님** — 본 모듈은 *현 상태를 판정*할 뿐 누락 자산을
   생성하지 않는다(부수효과 0). 실제 보완은 사람/CI 가 집행한다.
2. **증거는 디스크에 실재해야 한다** — 각 기준은 *리포에 실제로 존재하는
   파일*로만 충족(`SATISFIED`)된다. "준비할 예정"은 충족이 아니다(정직성).
3. **CRITICAL 한 칸이라도 비면 READY 아님** — 재현성·라이선스·내구 아카이브는
   10년 생존의 필요조건이다. 하나라도 미충족이면 전체 판정은 `NOT_READY`.
4. **아카이브 차원은 Phase 489 에 위임** — 내구 사본 충분성은
   [`archive_redundancy`](ARCHIVE_REDUNDANCY_POLICY.md) 의 결정적 판정을
   재사용한다(중복 로직 0).

## 차원과 심각도

| 차원 | 의미 |
|---|---|
| `reproducibility` | 동일 결과 재생성 가능성(핀·컨테이너·재현 스크립트) |
| `licensing` | 법적 사용 가능성(LICENSE 전문) |
| `archival` | 내구 사본 — 단일 실패점 없음(Phase 489 판정) |
| `identity` | 인용·식별 메타데이터 |
| `documentation` | 인수자가 읽을 문서 |
| `security` | 장기 보안 대응 절차 |
| `governance` | 유지보수자 승계 규약 |

| 심각도 | 가중치 | 의미 |
|---|:-:|---|
| `CRITICAL` | 3 | 미충족 시 10년 생존 불가 — `READY` 차단 |
| `IMPORTANT` | 2 | 인수·재현 품질에 중대 |
| `RECOMMENDED` | 1 | 있으면 좋음 |

## 체크리스트(SSoT)

| 기준 id | 차원 | 심각도 | 증거 |
|---|---|---|---|
| `repro-pinned-deps` | reproducibility | CRITICAL | `requirements.lock.txt`·`Dockerfile.reproducible`·`docs/REPRODUCIBILITY.md`·`scripts/independent_reproduction.sh` |
| `license-file` | licensing | CRITICAL | `LICENSE` |
| `archival-durable` | archival | CRITICAL | `.zenodo.json`·`CITATION.cff` **+ Phase 489 판정 REDUNDANT** |
| `citation-metadata` | identity | IMPORTANT | `CITATION.cff`·`.zenodo.json` |
| `handover-docs` | documentation | IMPORTANT | `README.md`·`CONTRIBUTING.md` |
| `security-support` | security | IMPORTANT | `SECURITY.md`·`docs/standards/CVE_RESPONSE_SLA_POLICY.md` |
| `dependency-policy` | reproducibility | RECOMMENDED | `docs/standards/DEPENDENCY_AUTOMERGE_POLICY.md` |
| `governance-succession` | governance | RECOMMENDED | `docs/GOVERNANCE.md` |

## 판정 규칙

```
미충족 CRITICAL 존재     → NOT_READY
전 기준 충족             → READY
그 사이(중요/권장만 미충족) → PARTIAL
```

점수 = 충족 기준의 가중치 합 ÷ 전체 가중치 합(소수 넷째 자리 반올림, 결정적).

## 현 상태(정직 공시)

본 작성 시점 리포 판정은 **`NOT_READY` (58.8%)** 다. 정직하게 미충족인
CRITICAL 두 칸:

- **`license-file`** — `pyproject.toml`·`package.json`·`CITATION.cff` 가 모두
  MIT 를 *선언*하지만 최상위 `LICENSE` 전문 파일이 없다. 선언만으로는 10년 후
  법적 사용 보장이 약하다 → 보완 필요(LICENSE 전문 추가).
- **`archival-durable`** — `.zenodo.json`·`CITATION.cff` 메타데이터는 준비됐으나
  첫 릴리스 태그 전이라 DOI 미발급(Phase 489 판정 `AT_RISK`) → 릴리스 시 발급.

권장 보완: `governance-succession`(`docs/GOVERNANCE.md`, Phase 487).

이 두 CRITICAL 이 해소(LICENSE 추가·DOI 발급)되면 회귀 핀
(`test_live_repo_not_ready_until_license_and_archive`)이 *의도적으로* 깨져
체크리스트 갱신을 강제한다.

## CLI

```bash
python -m simulation.legacy_readiness --checklist   # 기준 매트릭스
python -m simulation.legacy_readiness --status      # 리포 현 상태 판정
python -m simulation.legacy_readiness --manifest    # 체크리스트 매니페스트(JSON)
```
