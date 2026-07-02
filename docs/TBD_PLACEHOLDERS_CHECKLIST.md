# TBD Placeholders — 갱신 체크리스트 (P1-C chore/doi-placeholder)

> 본 저장소에는 외부 발급을 기다리는 식별자 자리표시자가 있습니다.
> 발급 즉시 본 체크리스트의 각 항목을 따라 일괄 교체하세요.
> 자동 검색: `git grep -nE '<TBD-DOI>|<TBD-PATENT-KR>|<TBD-PATENT-US>'`

---

## 1. Zenodo DOI — `<TBD-DOI>` (2건)

| 파일 | 라인 (현재) | 컨텍스트 |
|------|------------|----------|
| `docs/handout.html` | ~490 | 릴리즈 핸드아웃 인용 표 |
| `docs/PERMALINK_GUIDE.md` | ~51 | DOI 영구 식별자 가이드 예시 |

**발급 절차** (소요 ≈ 30분):

1. GitHub 저장소에 `v1.1.0` 태그 push
2. Zenodo 계정 (`zenodo.org`) 로그인 → GitHub 연동 ON → 저장소 enable
3. 새 릴리즈 자동 archive → DOI 자동 발급 (`10.5281/zenodo.NNNNNNN`)
4. 본 체크리스트 두 곳의 `<TBD-DOI>` → 실제 DOI 문자열로 교체
5. `CITATION.cff`, `benchmarks/CITATION.bib`, `.zenodo.json` 도 함께 갱신 (이미 발급 후 채워졌는지 확인)
6. README 배지 추가:
   ```markdown
   [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.NNNNNNN.svg)](https://doi.org/10.5281/zenodo.NNNNNNN)
   ```

**검증**: `curl -sI https://doi.org/10.5281/zenodo.NNNNNNN | head -5` 가 `302 Found` 응답을 반환해야 함.

---

## 2. 특허 출원 번호 — `<TBD-PATENT-KR>`, `<TBD-PATENT-US>` (2건)

| 파일 | 라인 (현재) | 컨텍스트 |
|------|------------|----------|
| `docs/patent/SDACS_특허명세서.md` | ~83 | 특허문헌 1 인용 (선행 KR 특허 비교) |
| `docs/patent/선행기술_조사.md` | ~116 | 선행 US 특허 인용 |

**발급 절차** (소요 ≈ 6-12개월):

### KR 특허
1. 변리사 수임 또는 KIPRIS 1357 무료 상담 활용
2. 출원 → 출원번호 (`KR 10-20XX-XXXXXXX` 형식) 수령
3. `docs/patent/SDACS_특허명세서.md`의 `<TBD-PATENT-KR>` → 실제 발급 번호로 교체
4. (선택) 등록 후 등록번호도 함께 기재

### US 특허
1. PCT 출원 또는 US 직접 출원 (USPTO)
2. 출원번호 (`US YY/XXX,XXX` Application No. 또는 등록번호 `US X,XXX,XXX`) 수령
3. `docs/patent/선행기술_조사.md`의 `<TBD-PATENT-US>` → 실제 번호로 교체
4. (선택) `priority date`도 본문에 추가

---

## 3. 자동 검증 명령

```bash
# 잔존 placeholder 0건 확인
git grep -nE '<TBD-DOI>|<TBD-PATENT-KR>|<TBD-PATENT-US>'

# 정확히 4건만 잡혀야 정상 (체크리스트 본 문서 + 4개 실파일).
# 발급 후엔 본 체크리스트의 해당 줄도 함께 갱신 또는 삭제.
```

## 4. 본 PR (chore/doi-placeholder)의 변경 요약

| 파일 | 변경 |
|------|------|
| `docs/handout.html` | `10.5281/zenodo.XXXXXXX` → `<TBD-DOI>` |
| `docs/PERMALINK_GUIDE.md` | `10.5281/zenodo.XXXXXXX` → `<TBD-DOI>` |
| `docs/patent/SDACS_특허명세서.md` | `KR 10-20XX-XXXXXXX` → `KR 10-<TBD-PATENT-KR>` |
| `docs/patent/선행기술_조사.md` | `US XX,XXX,XXX` → `US <TBD-PATENT-US>` |
| `docs/TBD_PLACEHOLDERS_CHECKLIST.md` | (신규) 본 문서 — 발급 후 일괄 교체 절차 |

**왜 통일했나**:
- `XXXXXXX` 류 placeholder는 검색 시 자릿수가 정확히 맞아야 검색되어, "발급 후 빠뜨리고 머지" 사고가 일어남.
- `<TBD-...>` 꺾쇠 구분자는 grep 한 줄로 100% 검출되며, 의도(아직 발급 안 됨)가 명시적.
- 본 체크리스트 1개 문서에 일정/소요/검증까지 묶어 "어디 가서 무엇을 하면 되는지" 한 곳에 정리.

---

*작성: 2026-06-04 (P1-C chore/doi-placeholder)*
