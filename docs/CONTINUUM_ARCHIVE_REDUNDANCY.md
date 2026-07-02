# 🗄 SDACS 아카이브 이중화 정책 (Phase 489)

*ODYSSEY Track ♾️ Continuum — Phase 489 산출물*
*Created: 2026-06-25 · 100년 보존 목표*

## 1. 배경

SDACS 가 Phase 500 Centennial 선언(10년 후 재현 가능성) 으로 진행하려면 **GitHub 단일 호스팅** 의 단일 점 실패(SPOF) 를 제거해야 한다. 본 문서는 **3중 이중화 아카이브** 정책을 정의한다.

---

## 2. 3중 이중화 (Triple Redundancy)

| 우선 | 아카이브 | URL | 책임 | 갱신 주기 | DOI |
|:-:|---|---|---|:-:|:-:|
| 🥇 | **Zenodo** (CERN) | <https://zenodo.org> | 학술 인용 + DOI | 메이저 릴리스 | ✅ |
| 🥈 | **Software Heritage** | <https://archive.softwareheritage.org> | 코드 영구 보존 | 자동 (Git crawler) | ❌ (SWHID) |
| 🥉 | **대학 리포지터리** | 목포대 학술정보관 | 학위 논문 + 캡스톤 | 학위 수여 시 | (DOI 가능) |

### 2.1 왜 3중?

- **단일 의존 회피**: GitHub 정책 변경·기업 인수·서비스 종료 위험
- **상이한 보존 모델**: Zenodo (의도적 아카이브)·SWH (자동 크롤링)·대학 (학위 보존)
- **국제 + 국내**: Zenodo (글로벌)·대학 (한국 보존법 준수)

---

## 3. Zenodo 절차

### 3.1 등록

1. **Zenodo-GitHub 통합 활성화**: <https://zenodo.org/account/settings/github/>
2. SDACS 레포지터리 On
3. GitHub Release 생성 시 자동 archive + DOI 발급

### 3.2 DOI 정책

| 릴리스 | DOI 패턴 |
|---|---|
| Concept DOI (전체 프로젝트) | `10.5281/zenodo.NNNNNNN` |
| Version DOI (v1.5.0 등) | `10.5281/zenodo.NNNNNNN+1` 자동 증분 |

### 3.3 메타데이터

```json
{
  "title": "SDACS: Swarm Drone Airspace Control System",
  "creators": [{"name": "Sun, Wooseo", "affiliation": "Mokpo National University"}],
  "description": "결정적 시뮬레이션 + Federation Operations + 5계층 안전망 ...",
  "keywords": ["UAV", "swarm", "ATC", "UTM", "simulation"],
  "license": "MIT",
  "related_identifiers": [
    {"identifier": "https://github.com/sun475300-sudo/swarm-drone-atc", "relation": "isSupplementTo"}
  ]
}
```

→ `.zenodo.json` 파일을 레포 루트에 추가 (Zenodo가 자동 인식).

### 3.4 인용 정보 (CITATION.cff)

```yaml
# CITATION.cff (레포 루트)
cff-version: 1.2.0
title: "SDACS: Swarm Drone Airspace Control System"
authors:
  - family-names: Sun
    given-names: Wooseo
    affiliation: Mokpo National University
doi: 10.5281/zenodo.XXXXXXX
url: https://github.com/sun475300-sudo/swarm-drone-atc
license: MIT
keywords:
  - swarm robotics
  - air traffic control
  - UTM
  - simulation
```

---

## 4. Software Heritage 절차

### 4.1 자동 보존

Software Heritage 는 GitHub 공개 레포를 **자동 크롤링** (월 1회 추정). 별도 등록 불필요.

### 4.2 SWHID 조회

```bash
# 특정 커밋의 SWHID 조회
curl -s "https://archive.softwareheritage.org/api/1/origin/save/git/url/https://github.com/sun475300-sudo/swarm-drone-atc/"

# 결과: {"id": "...", "save_request_status": "succeeded"}
```

### 4.3 수동 저장 요청

크롤링이 지연될 경우:
1. <https://archive.softwareheritage.org/save/> 접속
2. URL `https://github.com/sun475300-sudo/swarm-drone-atc` 입력
3. "Save" 클릭
4. SWHID 발급 (영구 식별자)

### 4.4 SWHID 인용

```
swh:1:dir:<hash>;origin=https://github.com/sun475300-sudo/swarm-drone-atc
```

→ 논문·문서에 SWHID 인용 시 영구 접근 보장.

---

## 5. 대학 리포지터리 (목포대)

### 5.1 절차

1. 학위 논문 (캡스톤) 제출 시 부속 자료로 SDACS 코드 첨부.
2. 목포대 학술정보관 디지털 컬렉션 등록.
3. (옵션) DOI 발급 (대학 도서관 통해).

### 5.2 보존 자료

| 항목 | 형식 | 주기 |
|---|---|:-:|
| 학위 논문 (PDF) | PDF/A | 학위 수여 시 |
| 캡스톤 보고서 | PDF + DOCX | 졸업 시 |
| 코드 스냅샷 | tar.gz (특정 커밋) | 졸업 시 |
| 데모 영상 | MP4/WebM | 졸업 시 |

---

## 6. 보존 무결성 검증

### 6.1 3중 일치 검증

릴리스 시 다음 자동 검증:

```bash
# 1. Git tag 의 commit SHA
GIT_SHA=$(git rev-list -n 1 v1.5.0)

# 2. Zenodo DOI 가 해당 SHA 보존 여부
curl -s "https://zenodo.org/api/records/NNNNNNN" | jq -r '.metadata.related_identifiers[]'

# 3. SWH 가 해당 SHA 보존 여부
SWH_URL="https://archive.softwareheritage.org/api/1/revision/$GIT_SHA/"
curl -s "$SWH_URL" | jq -r '.id'

# 4. 일치 확인 (모두 동일 SHA 가리키는지)
```

### 6.2 분기 점검

- 분기마다 본 절차 수동 점검 (CI 도입 시 자동화)
- 누락 발견 시 즉시 수동 저장 요청

---

## 7. 디지털 유산 선언 전제 (Phase 490 후속)

본 정책이 작동하면 Phase 490 (디지털 유산 선언) 의 *10년 후 재현 가능성 체크리스트* 충족 기반이 된다:

1. ✅ 코드 영구 보존 (Zenodo + SWH + 대학)
2. ✅ DOI 인용 (학술 인용 가능)
3. ✅ MIT 라이센스 (재사용 가능)
4. ⏳ 의존성 재현 가능 (Phase 488 SBOM 후속)
5. ⏳ 문서 영구 보존 (본 문서 + ROADMAP + CHANGELOG 모두 git 보존)

---

## 8. 한계 (정직성 공시)

- 본 정책은 *기술 절차* 만 정의 — 실제 등록·DOI 발급은 사용자 환경 의존.
- Zenodo 등록은 BDFL (현재 sun475300-sudo) 의 ORCID 필요.
- 대학 리포지터리는 학위 수여 시점 한정.
- Software Heritage 는 *공개 레포* 만 자동 크롤링 (private 레포는 미보존).
- 미러 사이트(GitLab·Gitea) 추가는 별도 후보 (Phase 489 확장).

---

## 9. 참조

- Zenodo-GitHub 통합: <https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content>
- Software Heritage: <https://archive.softwareheritage.org/>
- CITATION.cff 표준: <https://citation-file-format.github.io/>
- ORCID (저자 식별자): <https://orcid.org/>
- `docs/CONTINUUM_SECURITY_SLA.md` — Phase 488 (보안 SLA)
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` — Phase 487 (위원회 키 관리)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track ♾️ — Phase 481-500
