# Phase 281–300 — Academic Impact: Zenodo DOI 준비 가이드

> **성숙도 공시**: 이 문서는 Zenodo DOI 등록 절차와 K-UTM 표준 제안 준비를 위한
> 실행 가이드입니다. 실제 DOI 등록은 Zenodo 계정 및 GitHub 연동 설정이 필요합니다.

---

## 1. Zenodo DOI 등록 개요

[Zenodo](https://zenodo.org)는 CERN이 운영하는 오픈 리포지터리로, GitHub 저장소와 연동하여
소프트웨어 릴리스에 자동으로 DOI를 부여한다. SDACS는 `CITATION.cff`와 `benchmarks/CITATION.bib`가
이미 준비되어 있어 Zenodo 등록 절차를 즉시 진행할 수 있다.

### 현재 준비 상태

| 항목 | 상태 | 파일 |
|---|---|---|
| `CITATION.cff` | ✅ 완료 | `CITATION.cff` |
| `benchmarks/CITATION.bib` | ✅ 완료 | `benchmarks/CITATION.bib` |
| `LICENSE` (MIT) | ✅ 완료 | `LICENSE` |
| `README.md` (한국어) | ✅ 완료 | `README.md` |
| `README.en.md` (영어) | ✅ 완료 | `README.en.md` |
| GitHub Release v1.5.0 | ⏳ 준비 필요 | — |
| Zenodo 계정 연동 | ⏳ 준비 필요 | — |

---

## 2. Zenodo DOI 등록 절차

### Step 1: Zenodo 계정 생성 및 GitHub 연동

```
1. https://zenodo.org 접속
2. "Sign Up" → GitHub 계정으로 로그인 권장
3. 상단 메뉴 "GitHub" 탭 클릭
4. "sun475300-sudo/swarm-drone-atc" 저장소 활성화 (토글 ON)
```

### Step 2: GitHub Release 생성

Zenodo는 GitHub Release 생성 시 자동으로 스냅샷을 캡처하고 DOI를 발급한다.

```bash
# v1.5.0 태그 생성 및 푸시
git tag -a v1.5.0 -m "SDACS v1.5.0 — 500+ Phase 통합 릴리스"
git push origin v1.5.0

# GitHub CLI로 릴리스 생성
gh release create v1.5.0 \
  --title "SDACS v1.5.0 — Swarm Drone Airspace Control System" \
  --notes-file docs/RELEASE_NOTES_v1.5.0.md \
  --latest
```

### Step 3: Zenodo 메타데이터 보강

Zenodo 연동 후 `.zenodo.json` 파일을 저장소 루트에 추가하면 메타데이터가 자동으로 적용된다.

```json
{
  "title": "SDACS — Swarm Drone Airspace Control System",
  "description": "APF + WebGPU 기반 군집 드론 공역 관제 자동화 시스템. 90초 선제 예측으로 97.8% 충돌 해결률 달성, 38,400회 Monte Carlo 검증. 목포대학교 캡스톤 디자인 프로젝트.",
  "upload_type": "software",
  "access_right": "open",
  "license": "MIT",
  "keywords": [
    "swarm drone",
    "airspace control",
    "collision avoidance",
    "artificial potential field",
    "APF",
    "WebGPU",
    "UTM",
    "unmanned traffic management",
    "capstone design",
    "Monte Carlo simulation",
    "SimPy"
  ],
  "creators": [
    {
      "name": "Jang, Sunwoo",
      "affiliation": "Mokpo National University",
      "orcid": ""
    }
  ],
  "related_identifiers": [
    {
      "identifier": "https://github.com/sun475300-sudo/swarm-drone-atc",
      "relation": "isSupplementTo",
      "scheme": "url"
    },
    {
      "identifier": "https://sun475300-sudo.github.io/swarm-drone-atc/",
      "relation": "isDocumentedBy",
      "scheme": "url"
    }
  ],
  "communities": [
    {"identifier": "zenodo"},
    {"identifier": "robotics"}
  ],
  "language": "kor",
  "version": "1.5.0"
}
```

### Step 4: DOI 배지 추가

DOI 발급 후 README.md와 README.en.md에 배지를 추가한다.

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

`CITATION.cff`에도 DOI를 추가한다.

```yaml
# CITATION.cff에 추가
doi: "10.5281/zenodo.XXXXXXX"
identifiers:
  - type: doi
    value: "10.5281/zenodo.XXXXXXX"
    description: "Zenodo software archive DOI"
```

---

## 3. ORCID 등록 (권장)

ORCID는 연구자 고유 식별자로, Zenodo와 연동하면 자동으로 연구 성과가 프로필에 등록된다.

```
1. https://orcid.org 접속
2. "Register Now" → 계정 생성
3. Zenodo 프로필에서 ORCID 연동
4. CITATION.cff의 orcid 필드에 ID 추가
```

---

## 4. K-UTM 표준 제안

### 4.1 K-UTM 표준 개요

K-UTM(Korean Unmanned Traffic Management)은 국토교통부 주도로 추진 중인 한국형 드론 교통 관리 표준 체계다. SDACS는 다음 표준 항목에 기여할 수 있는 기술 기반을 보유하고 있다.

| K-UTM 표준 항목 | SDACS 대응 기술 | 성숙도 |
|---|---|---|
| 비행 계획 승인 체계 | `_sdacs.requestClearance()` | production |
| 충돌 회피 알고리즘 | APF + CBS/A* 하이브리드 | production |
| 원격 식별 (Remote ID) | `_sdacs.remoteId.*` | production |
| 비행금지구역 관리 | `mokpo_harbor.py` NFZ 판정 | beta |
| 기상 연동 | `simulation/kma_wind_field.py` | beta |
| V2X 통신 규격 | `simulation/v2x_message.py` | beta |
| 다중 드론 우선순위 | `AirspaceController` 우선순위 큐 | production |
| 비상 절차 (Failsafe) | `simulation/failsafe_manager.py` | production |

### 4.2 표준 제안 절차

```
1. 국토교통부 드론 정책과 연락
   - 이메일: drone@korea.kr
   - 전화: 044-201-4000

2. 한국교통연구원(KOTI) K-UTM 연구팀 협력
   - https://www.koti.re.kr

3. 한국항공우주연구원(KARI) UTM 실증 사업 참여
   - https://www.kari.re.kr

4. 표준 제안서 작성 (KS 표준 또는 단체 표준)
   - 한국표준협회(KSA): https://www.ksa.or.kr
   - 한국정보통신기술협회(TTA): https://www.tta.or.kr
```

### 4.3 표준 제안서 초안 구조

```
K-UTM 기술 표준 제안서 (초안)

1. 표준 제안 배경
   - 드론 교통량 증가와 안전 관리 필요성
   - 기존 항공교통관제(ATC)와의 차별성

2. 제안 표준 범위
   - 군집 드론 충돌 회피 알고리즘 표준 (APF 기반)
   - 비행 계획 승인 메시지 형식 (JSON 스키마)
   - 원격 식별 데이터 구조 (SAE J2735 기반)

3. 기술 근거
   - SDACS 38,400회 Monte Carlo 검증 결과
   - APF + CBS 하이브리드 알고리즘 성능 지표
   - 목포 해역 실 좌표계 검증 데이터

4. 국제 표준 정합성
   - ICAO UTM Framework
   - ASTM F3411 Remote ID
   - EUROCAE ED-269 SORA

5. 구현 참조
   - 오픈소스 참조 구현: SDACS v1.5.0
   - GitHub: https://github.com/sun475300-sudo/swarm-drone-atc
   - DOI: 10.5281/zenodo.XXXXXXX (등록 후 갱신)
```

---

## 5. 학술 인용 현황 추적

### Google Scholar 알림 설정

```
1. https://scholar.google.com 접속
2. "내 프로필" → 프로필 생성
3. "알림" → "SDACS" 또는 저자명 검색 알림 설정
```

### Semantic Scholar 등록

```
1. https://www.semanticscholar.org 접속
2. 논문 검색 후 "Claim Paper" 기능 활용
3. arXiv 프리프린트 제출 후 자동 인덱싱
```

---

## 6. 체크리스트

### Zenodo DOI 등록

- [ ] Zenodo 계정 생성 및 GitHub 연동
- [ ] `.zenodo.json` 파일 저장소 루트에 추가
- [ ] GitHub Release v1.5.0 생성
- [ ] DOI 발급 확인 (zenodo.org/record/XXXXXXX)
- [ ] README.md 배지 추가
- [ ] README.en.md 배지 추가
- [ ] `CITATION.cff` DOI 필드 추가
- [ ] `benchmarks/CITATION.bib` DOI 추가

### ORCID 등록

- [ ] ORCID 계정 생성
- [ ] Zenodo 프로필 ORCID 연동
- [ ] `CITATION.cff` orcid 필드 추가

### K-UTM 표준 제안

- [ ] 국토교통부 드론 정책과 초기 연락
- [ ] KOTI K-UTM 연구팀 협력 의향 확인
- [ ] 표준 제안서 초안 작성
- [ ] TTA 단체 표준 제안 접수

### IROS 2026 투고 (Phase 281-285)

- [ ] `docs/paper/submission_guide.md` 절차 확인
- [ ] PaperCept 계정 등록
- [ ] 논문 PDF 최종본 준비 (`docs/paper/latex/main.pdf`)
- [ ] 익명화 저장소 생성 (`scripts/anonymize_repo.py`)
- [ ] arXiv 프리프린트 제출 (cs.RO 카테고리)

---

## 7. 참고 문서

| 문서 | 경로 |
|---|---|
| 투고 가이드 | `docs/paper/submission_guide.md` |
| 논문 초안 | `docs/paper/PAPER_DRAFT.md` |
| 기여 개요 | `docs/paper/contribution_outline.md` |
| 평가 메트릭 | `docs/paper/EVALUATION_METRICS.md` |
| 재현성 가이드 | `docs/REPRODUCIBILITY.md` |
| 벤치마크 데이터셋 | `benchmarks/DATASET_CARD.md` |
| CITATION.cff | `CITATION.cff` |

---

*작성일: 2026-07-30 | 버전: 1.0 | 성숙도: beta (DOI 등록 절차 준비 완료, 실제 등록 미완)*
