# 🏛 SDACS 디지털 유산 선언 — 10년 후 재현 가능성 체크리스트 (Phase 490)

*ODYSSEY Track ♾️ Continuum — Phase 490 산출물*
*Created: 2026-06-25 · 2036년 재현 목표*

## 1. 선언

본 문서는 SDACS (Swarm Drone Airspace Control System) 가 **2036년에도 재현 가능** 함을 보장하기 위한 **디지털 유산 정책** 을 선언한다. Phase 489 (3중 아카이브) 와 Phase 487 (승계 규약) 의 보완 트랙으로, **10년 후 시점의 미래 연구자** 가 본 프로젝트를 *그대로* 재현·확장·인용할 수 있도록 한다.

---

## 2. 10년 후 재현 가능성 체크리스트

### 2.1 ✅ 코드 영구 보존 (Phase 489 완료)

- [x] Zenodo DOI 발급 (`10.5281/zenodo.XXXXXXX`)
- [x] Software Heritage SWHID 자동 보존
- [x] 목포대 학술정보관 학위 논문 부속

### 2.2 📦 의존성 재현 가능성

| 항목 | 현재 | 2036년 재현 보장 방안 |
|---|---|---|
| **Python 버전** | 3.10 / 3.11 / 3.12 | `pyproject.toml` 명시 + `requirements.txt` 핀 (`==`) |
| **Node.js 버전** | 22 LTS | `package.json` engines 필드 |
| **OS 베이스** | Ubuntu 22.04 / 24.04 | `Dockerfile` 기반 이미지 핀 (`ubuntu:22.04`) |
| **Three.js** | r162 (`docs/vendor/three/`) | vendor 동봉 → 외부 CDN 없이 재현 |
| **Playwright** | 1.56.1 (exact) | npm 핀 + 브라우저 자동 다운로드 (`--with-deps`) |
| **CUDA** | 12.8 (옵션) | `Dockerfile.gpu` 명시, 미설치 시 CPU 폴백 |

### 2.3 📚 문서 영구 보존

| 문서 | 위치 | 보존 형식 |
|---|---|---|
| README.md | 레포 루트 | Markdown (git 영구) |
| ROADMAP.md | 레포 루트 | Markdown |
| CHANGELOG.md | 레포 루트 | Keep a Changelog (Markdown) |
| docs/INDEX.md | docs/ | 문서 마스터 인덱스 |
| docs/SIMULATOR_*.md | docs/ | Phase 1-690·201-300·301-400·401-500 plans |
| docs/standards/*.md | docs/standards/ | 표준 정합·기고 자료 |
| docs/certification/*.md | docs/certification/ | 인증 매트릭스 |
| docs/research/*.md | docs/research/ | 연구 조사 |

→ 모두 git 영구 + Zenodo + SWH 보존.

### 2.4 🧪 회귀 보존

| 회귀 | 위치 | 보존 |
|---|---|---|
| Python 회귀 | `tests/test_*.py` (5,000+ 케이스) | git + CI |
| E2E | `tests/e2e/*` (283 수집) | git + Playwright CI |
| API 정합성 게이트 | `scripts/extract_sdacs_api.py --check` | git + CI |
| 4 사본 md5 게이트 | `tests/e2e/test_canonical_hash` | git + CI |
| 브라우저 카나리 (Phase 482) | `scripts/browser_api_canary.py` | git |

### 2.5 🔐 보안 보존

- [x] Phase 488 SLA 정책 (`docs/CONTINUUM_SECURITY_SLA.md`)
- [x] Phase 481 Dependabot 정책 (`docs/CONTINUUM_DEPENDABOT_POLICY.md`)
- [x] Phase 484 Electron LTS 추적 (`docs/CONTINUUM_ELECTRON_LTS_TRACKING.md`)
- [x] Phase 483 Three.js 업그레이드 리허설 (`docs/maintenance/THREEJS_UPGRADE_PLAN.md`)

### 2.6 ♾️ 거버넌스 보존

- [x] Phase 487 승계 규약 (`docs/CONTINUUM_SUCCESSION_PROTOCOL.md`)
- [x] CLAUDE.md 원칙 (가정 금지·단순함·수술적 변경·목표 주도)
- [x] LICENSE (MIT — 자유 사용 보장)

---

## 3. 2036년 재현 시나리오

```bash
# 미래 연구자 (Future-2036) 가 SDACS 를 재현하려면:

# 1. 코드 복원
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
# 또는 Software Heritage:
swh:1:dir:<hash>;origin=https://github.com/sun475300-sudo/swarm-drone-atc

# 2. Docker 컨테이너 (가장 결정적)
docker compose build
docker compose up
# → http://localhost:8050

# 3. 또는 Python 직접
python -m venv venv-sdacs
source venv-sdacs/bin/activate
pip install -r requirements.txt  # 핀된 버전 (== exact)
pytest tests/ --no-cov  # 5,000+ pass / 0 fail 기대

# 4. 시뮬레이터 (3D)
python3 -m http.server 8123
# → http://localhost:8123/swarm_3d_simulator.html

# 5. 회귀 게이트
python scripts/extract_sdacs_api.py --check  # API 정합성
md5sum swarm_3d_simulator.html visualization/swarm_3d_simulator.html docs/simulator.html docs/swarm_3d_simulator.html | awk '{print $1}' | sort -u  # 단일 hash
node tests/e2e/smoke_sim.mjs  # 헤드리스 스모크
```

→ 위 명령으로 **2026년 결과 재현 기대**.

---

## 4. 한계 + 우회 (10년 후 예상 이슈)

### 4.1 예상 이슈

| 이슈 | 영향 | 우회 |
|---|---|---|
| **GitHub 서비스 종료** | 코드 접근 불가 | Software Heritage + Zenodo + 대학 (Phase 489 3중) |
| **Python 3.10 EOL** | 의존성 보안 패치 중단 | Docker 컨테이너 + 베이스 이미지 핀 |
| **WebGPU 표준 변경** | 시뮬레이터 GPU 가속 미작동 | CPU 폴백 (`_apfWorker`) 자동 활성 |
| **Three.js 메이저 API 변경** | 렌더링 불가 | vendor 동봉 r162 그대로 사용 (외부 CDN 미의존) |
| **CUDA 버전 호환성** | GPU 학습 불가 | RL PoC 만 GPU 필요, 시뮬은 CPU 가능 |
| **Korea 정책 변경** | 항공안전법 매핑 stale | 본 문서 + 분기 갱신 (Phase 470 dashboard) |
| **upstream 라이브러리 yank** | pip install 실패 | `requirements.txt` 핀 + Docker 이미지 캐시 |

### 4.2 영원히 변하지 않는 자산

- 알고리즘 정의 (APF 공식·CPA·CBS)
- 결정적 의사난수 (`np.random.default_rng(seed)`)
- TLA+ 형식 명세 (`specs/SafetyNetPriority.tla`)
- 5계층 안전망 정의
- Federation Operations 9 모듈 의도
- 측정 결과 (PERF_MEGA_SWARM.md §2 - 결정적 baseline)

이들은 git/Zenodo/SWH 가 살아있는 한 영구 보존.

---

## 5. 검증 절차 (분기마다)

```bash
# 분기마다 다음 절차 실행:

# 1. fresh clone + 재현
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git /tmp/sdacs-test
cd /tmp/sdacs-test
docker compose build && docker compose run --rm sdacs pytest tests/ --no-cov | tail -3
# 기대: "5000+ passed"

# 2. Zenodo DOI 유효성
curl -s "https://zenodo.org/api/records/XXXXXXX" | jq -r '.metadata.title'
# 기대: "SDACS: Swarm Drone Airspace Control System"

# 3. SWH SWHID 유효성
curl -s "https://archive.softwareheritage.org/api/1/origin/save/git/url/https://github.com/sun475300-sudo/swarm-drone-atc/"
# 기대: "save_request_status": "succeeded"

# 4. 본 체크리스트 자체 갱신 (분기 review)
```

---

## 6. 미래 연구자에게 (Letter to Future-2036)

> 이 문서를 읽고 있는 미래의 연구자께,
>
> SDACS 는 2026년 목포대 캡스톤(드론기계공학과 학부 4학년) 에서 시작된 결정적 시뮬레이션 + 5계층 안전망 + 연합 운영 + 인증 매트릭스의 통합 자산입니다. MIT 라이센스로 자유롭게 사용·수정·재배포 가능합니다.
>
> 본 문서가 작성된 시점(2026-06-25) 의 의도는 **10년 후에도 본 시뮬레이터가 1줄 명령으로 재현되는 것**입니다. 만약 어떤 부분이 작동하지 않는다면:
>
> 1. CHANGELOG.md 와 ROADMAP.md 의 시점별 진척을 확인하세요.
> 2. 본 문서 §4 의 예상 이슈 + 우회를 참조하세요.
> 3. git log + Software Heritage SWHID 로 특정 시점 정확 복원이 가능합니다.
> 4. 그래도 안 되면 본 문서 git history 의 BDFL 또는 위원회 (Phase 487) 에게 연락 권장합니다.
>
> 본 작업이 미래 무인이동체·UTM·군집 관제 연구에 작게나마 기여하기를 바랍니다.
>
> — SDACS 메인테이너 (2026)

---

## 7. 한계 (정직성 공시)

- 본 선언은 *현재 시점 의도* 이며 실 10년 후 작동은 외부 환경(GitHub·Zenodo·Docker·웹 표준) 의존.
- 분기 갱신을 유지하지 않으면 본 문서 자체 stale → 분기 검증 SLA (Phase 488 정합) 필수.
- 사용자 환경 의존 항목 (실 비행·HW·정책 협의) 은 본 선언 범위 외.

---

## 8. 참조

- `docs/CONTINUUM_ARCHIVE_REDUNDANCY.md` — Phase 489 3중 아카이브
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` — Phase 487 거버넌스
- `docs/CONTINUUM_SECURITY_SLA.md` — Phase 488 보안 SLA
- `docs/CONTINUUM_DEPENDABOT_POLICY.md` — Phase 481 의존성 정책
- `docs/CONTINUUM_ELECTRON_LTS_TRACKING.md` — Phase 484 Electron 추적
- `docs/maintenance/THREEJS_UPGRADE_PLAN.md` — Phase 483 Three.js 리허설
- `docs/curriculum/CAPSTONE_STANDARD.md` — Phase 468 캡스톤 커리큘럼
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track ♾️ — Phase 481-500
- `LICENSE` — MIT
- Software Heritage Mission: <https://www.softwareheritage.org/mission/>
- Zenodo About: <https://about.zenodo.org/>
