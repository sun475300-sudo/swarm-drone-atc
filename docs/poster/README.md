# SDACS 학회 포스터 (P710)

학술대회 발표용 포스터 자산 모음. 한국어/영어 2가지 버전 유지.

## 데드라인

| 행사 | 날짜 | 언어 | 사이즈 | 상태 |
|---|---|---|---|---|
| **동강대 학술대회** | 2026-04-23 | KO | A0 세로 | 🔄 스켈레톤 |
| **IROS 2026 Workshop** | 2026-10 (TBD) | EN | A0 세로 | ⏳ 대기 |
| **한국로보틱스학회** | TBD | KO | A1 가로 | ⏳ 대기 |

## 구조 (8 섹션 × 한국어/영어)

1. **Title + Authors** (한 줄)
2. **Background & Problem** (300자) — UAM·UTM 폭발적 성장, 기존 ORCA/CBS 한계
3. **System Architecture** (figure) — 5계층 안전망 다이어그램
4. **Method: Wind-Aware Hybrid APF + CBS** (300자 + 식 2개)
5. **Experimental Setup** (table) — 10 시나리오 × 5 seed × 3 baseline
6. **Results** (chart × 2) — NMR/MSD bar + Pareto front
7. **Demo** (QR code) — github.io 라이브 시뮬레이터 링크
8. **Conclusion & Future Work** (200자) — P736 RL, P740 디지털 트윈

## 파일 구성

```
docs/poster/
├── README.md                   (이 문서)
├── donggang_2026_ko.md         (동강대 한국어 — 스켈레톤)
├── iros_2026_en.md             (IROS 영어 — 추후)
├── assets/
│   ├── architecture_diagram.svg     (5계층 안전망 다이어그램)
│   ├── results_nmr_msd_bar.png      (P706 결과 차트)
│   └── pareto_front.png             (NMR vs RTF Pareto)
└── final/
    ├── donggang_2026_ko.pdf    (최종 PDF, 생성 시점)
    └── iros_2026_en.pdf
```

## 자산 생성 방법

- **다이어그램**: draw.io / Excalidraw → SVG export
- **차트**: `python scripts/poster_charts.py` (P706 결과 CSV → matplotlib)
- **PDF**: `pandoc donggang_2026_ko.md --pdf-engine=xelatex -o final/donggang_2026_ko.pdf` (KaTeX/한글 폰트)

## 디자인 가이드

- **색 팔레트**: 메인 #00e5ff (SDACS 시안), 보조 #a855f7 (보라), 강조 #10b981 (녹색)
- **폰트**: 본문 Pretendard / Inter, 코드 JetBrains Mono
- **로고**: 목포대 + 캡스톤
- **여백**: 20mm 외곽, 섹션 간 8mm
