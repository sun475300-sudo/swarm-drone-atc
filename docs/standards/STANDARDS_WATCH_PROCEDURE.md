# 📡 SDACS 표준 변경 모니터링 절차 (Phase 479)

*ODYSSEY Track 🏛 Standards & Policy — Phase 479 산출물*
*Created: 2026-06-25 · 분기 모니터링 + 자동 알림*

## 1. 목적

SDACS 가 정합·기여 중인 18개 표준(Phase 470 dashboard 참조)의 **upstream 변경 사항** 을 분기마다 결정적으로 추적하여, 본 프로젝트 산출물이 stale 되는 것을 방지한다.

---

## 2. 모니터링 대상

### 2.1 표준 기관별 알림 채널

| 기관 | 알림 채널 | 점검 주기 |
|---|---|:-:|
| **ASTM F38** | <https://www.astm.org/COMMIT/SUBCOMMIT/F38.htm> 신규 표준 게시 | 분기 |
| **ISO/TC 20/SC 16** | <https://www.iso.org/committee/5336224.html> News tab | 분기 |
| **EASA** | <https://www.easa.europa.eu/en/light/topics/rules-and-related-information> | 분기 |
| **FAA** | <https://www.federalregister.gov/agencies/federal-aviation-administration> RSS | 월 |
| **ICAO** | <https://www.icao.int/safety/ua/Pages/default.aspx> | 분기 |
| **JARUS** | <http://jarus-rpas.org/news> | 분기 |
| **GUTMA** | <https://gutma.org/news/> RSS | 분기 |
| **IFALPA** | <https://www.ifalpa.org/publications/library/position-papers> | 분기 |
| **KAIA** | <https://kaia.or.kr> 공지 | 분기 |
| **국토부** | <https://www.molit.go.kr> 항공정책실 보도자료 | 월 |

### 2.2 트리거 이벤트

다음 이벤트 발생 시 본 프로젝트 산출물 검토 필요:

- 새 표준 발간 (DIS → IS 또는 WD → CD → DIS)
- 기존 표준 개정 (예: SORA v2.0 → v2.5)
- Public Comment 기간 시작 (FAA Federal Register, EASA NPA 등)
- 워킹그룹 정기 회의 (분기·반기)
- 신규 기술 권고 (예: ICAO Annex 13 갱신)

---

## 3. 분기 점검 절차

### 3.1 단계별 절차

```
[분기 1주 차]
1. 본 문서 §2.1 의 각 채널을 수동 점검 (자동화는 후속 Phase)
2. 신규 표준 발견 시 docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md §2.2 추가
3. 발간 표준 (WD → IS) 승격 시 §2.1 이동
4. 새 의견 수렴 기간 발견 시 본 프로젝트 의견서 갱신 검토

[분기 2-4주 차]
5. 본 SDACS 산출물 (Phase 461-477) stale 가능성 검토
6. 필요 시 갱신 PR + 회귀 회신

[분기 마감 주]
7. 본 분기 보고서 작성 (docs/standards/SDACS_STANDARDS_QUARTERLY_REPORT_YYYY-QN.md)
   → Phase 480 템플릿 사용
8. Phase 470 dashboard 의 §2.1 매트릭스 + §3 회의 일정 갱신
9. Phase 478 정합성 점검 (`scripts/standards_conformance_check.py`) 실행
```

### 3.2 자동화 후보 (Phase 480+ 후속)

- RSS 폴러 (Python `feedparser` 기반)
- GitHub Actions 분기 cron 잡 (1월·4월·7월·10월 1일)
- Slack/Discord 웹훅 알림
- LLM 기반 신규 표준 *영향 평가* 자동 생성 (수동 확인 필수)

---

## 4. 변경 영향 평가 매트릭스

upstream 변경 발견 시:

| 변경 유형 | 영향 평가 | 대응 |
|---|---|---|
| 신규 표준 (WD/CD 단계) | 정합 가능성 평가 | 본 dashboard §2.2 추가 |
| 발간 표준 (DIS → IS) | 산출물 영향 검토 | 의견서 갱신 PR |
| 기존 표준 개정 (예: SORA v2.5) | 영향 큼 | 자매 의견서 (Phase 476) 갱신 |
| Public Comment 기간 | 즉시 검토 | 의견서 제출 |
| Working Group 회의 | 발표 검토 | 회의 자료 준비 |

---

## 5. 한계 (정직성 공시)

- 본 절차는 *수동 분기 점검* — 자동화는 Phase 480+ 후속.
- RSS·이메일 알림 자동화는 사용자 환경 (이메일 서버·RSS 인프라) 의존.
- 표준 기관 사이트 변경 (URL deprecation) 시 본 문서 갱신 필요.

---

## 6. 참조

- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470 대시보드 (분기 갱신)
- `scripts/standards_conformance_check.py` — Phase 478 정합성 자동 점검
- `docs/standards/SDACS_STANDARDS_QUARTERLY_REPORT_TEMPLATE.md` — Phase 480 분기 보고서
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
