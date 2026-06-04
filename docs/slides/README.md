# SDACS 발표 슬라이드 (P710)

학술대회·워크숍 발표용 슬라이드 자산.

## 행사별 슬라이드

| 행사 | 길이 | 언어 | 도구 | 상태 |
|---|---|---|---|---|
| 동강대 학술대회 | 12분 (15장) | KO | Marp / Reveal.js | 🔄 outline |
| IROS Workshop | 10분 (12장) | EN | Marp | ⏳ 대기 |
| 캡스톤 최종발표 | 20분 (25장) | KO | PPTX | ⏳ 대기 |

## 동강대 학술대회 outline (KO, 12분)

| 슬라이드 | 내용 | 시간 |
|---|---|---|
| 1 | 표지 (제목·저자·소속) | 0:00 |
| 2 | 목차 | 0:30 |
| 3 | UAM/UTM 시장 폭발 (그래프) | 1:00 |
| 4 | 기존 알고리즘 한계 (ORCA/CBS) | 2:00 |
| 5 | SDACS 5계층 안전망 | 3:00 |
| 6 | Layer 2: Wind-Aware APF | 4:30 |
| 7 | Layer 4: CBS Replan Trigger | 5:30 |
| 8 | 시스템 데모 (영상 30초) | 6:30 |
| 9 | 실험 설정 (P703 dataset) | 7:30 |
| 10 | 결과 - NMR/MSD (차트) | 8:30 |
| 11 | 결과 - Pareto (차트) | 9:30 |
| 12 | 한계 및 향후 | 10:30 |
| 13 | 결론 (요약 3 줄) | 11:00 |
| 14 | 질의응답 (백업 슬라이드) | — |
| 15 | 참고문헌 (백업) | — |

## 디자인 가이드

- **테마**: 어두운 배경(#02060d) + 시안 강조(#00e5ff) — SDACS 시뮬레이터와 일관
- **본문 폰트**: Pretendard SemiBold
- **코드 폰트**: JetBrains Mono
- **이미지**: 시뮬레이터 스크린샷 활용 (시각 임팩트)
- **애니메이션**: 최소화 — 그래프 reveal만

## 생성

```bash
# Marp (권장)
marp docs/slides/donggang_2026_ko.md -o final/donggang_2026_ko.pdf
marp docs/slides/donggang_2026_ko.md -o final/donggang_2026_ko.pptx  # PPTX export
```

## TODO

- [ ] `donggang_2026_ko.md` Marp 형식으로 15장 작성
- [ ] 시뮬레이터 데모 영상 30초 녹화
- [ ] 백업 슬라이드(Q&A 대비) 5장 추가
