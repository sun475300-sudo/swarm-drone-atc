# SDACS Version Manifest

*Single source of truth — 본 파일이 SDACS 모든 산출물의 버전을 단일 추적.*

## 📌 현재 버전

| 컴포넌트 | 버전 | 빌드 일자 |
|---|---|---|
| **SDACS Desktop App** | `v1.5.0` | 2026-06-05 |
| 시뮬레이터 (군집 ATC) | `v1.5.0` (200 Phase) | 2026-06-05 |
| 시뮬레이터 (해양 탐지) | `v1.5.0` (HYPER 11 ATC 포함) | 2026-06-05 |
| `package.json` | `1.5.0` | 2026-06-05 |
| Electron | `32.3.3` (v1.5.0 빌드) → `^39.8.5` (package.json, 차기 빌드) | — |
| electron-builder | `25.1.8` | — |
| Three.js | `r162` | — |

## 📊 검증 통계 (v1.5.0 기준)

| 항목 | 값 |
|---|:-:|
| Phase 완료 | **200 / 200** (100%) |
| 시뮬레이터 코드 | 11,836 line |
| `_sdacs` 외부 API | 402 항목 — 분류 400 (production 89·beta 98·mock 110·speculative 103) + 헬퍼 2 |
| Playwright E2E | 255 / 256 (1 skip) |
| 회귀 pytest | 4,180 pass / 8 skip / 0 fail |
| **종합 자동 검증** | **4,435 pass / 9 skip / 0 fail** (2026-06-12 실측) |
| 사본 동기화 (md5) | 7 파일 일치 (군집 4 + 해양 3) |
| 데스크탑 AppImage | 105 MB (ELF, ASAR 검증 완료) |

## 🗂 버전 히스토리

| 버전 | 일자 | Phase | 핵심 마일스톤 |
|---|---|---|---|
| **v1.5.0** | 2026-06-05 | 200 | POST-UNIVERSE — Phase 200 `𝟏 (Unity)` |
| v1.4.0 | 2026-06-05 | 150 | ULTIMATE — Phase 150 `Universe OS` |
| v1.3.0 | 2026-06-05 | 100 | STELLAR — Phase 100 `SDACS 2.0 표준 ATC OS` |
| v1.2.0 | 2026-06-05 | 50 | HYPER FINAL — Phase 32-50 일괄 |
| v1.1.0 | 2026-06-04 | 30 | HYPER MID — Phase 11-31 |
| v1.0.0 | 2026-06-04 | 9 | MEGA — Phase 1-9 (코어 ATC) |

전체 변경 사항: [CHANGELOG.md](CHANGELOG.md)

## 🔄 다음 버전 후보

| 버전 | 트리거 | 예상 |
|---|---|---|
| v1.5.1 | bug fix only | 미정 |
| v1.6.0 | MASTER_PLAN Track Ⅰ 완료 (시각화 5종 마감) | 2026-07 |
| v1.7.0 | Track Ⅲ 다중 사용자 실증 | 2026-09 |
| v2.0.0 | TRANSCENDENCE 격상 + GENESIS 착수 (Phase 301+) | 2026-12 |

## 🏗 빌드 산출물 (배포 위치)

| 파일 | 위치 | 비고 |
|---|---|---|
| AppImage (Linux) | `dist-desktop/SDACS-Simulator-1.5.0-x86_64.AppImage` | .gitignore (Releases에서 배포) |
| `.exe` (Windows) | GitHub Releases | `v1.5.0` 태그 푸시 시 자동 생성 |
| `.dmg` (macOS) | GitHub Releases | 동일 |
| 웹 시뮬 (HTML) | `swarm_3d_simulator.html` + Pages | main 직접 커밋 |
| 데모 영상 | `docs/demo/sdacs_200phase_showcase.webm` | main 직접 커밋 (9.4 MB) |
| 캡스톤 보고서 | `docs/report/SDACS_Capstone_Report_v200.docx` | main 직접 커밋 |
| IROS PDF | `docs/paper/SDACS_IROS_2026_sections_4to7.pdf` | main 직접 커밋 |

## 🔗 관련

- [Quick Start](docs/QUICK_START.md) — 1줄 실행
- [Release Guide](docs/RELEASE_GUIDE.md) — 데스크탑 빌드 절차
- [V1.5.0 Release Instructions](docs/V1_5_0_RELEASE_INSTRUCTIONS.md) — 사용자 1줄 명령
- [CHANGELOG](CHANGELOG.md)
- [Phase Matrix HTML](docs/phase_matrix.html) — 200 Phase 시각 인덱스
