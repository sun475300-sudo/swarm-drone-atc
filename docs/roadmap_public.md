# SDACS Public Roadmap / 공개 로드맵

> 외부 검토자 / 협력 기관용 요약. 내부 TODO·개인 메모는 `ROADMAP.md` / `MASTER_TODO_ATC.md` 참조.

**현재 상태 (2026-04)**: Phase 1~690 완료, Phase 691~720 진행 중.

---

## 완료된 마일스톤

| 범위 | 주제 | 완료 시점 |
|------|------|----------|
| Phase 1~470 | Core ATC + 25개 언어 다중 언어 확장 | 2025 ~ 2026-Q1 |
| Phase 501~600 | Deep Theory (Quantum / Neural ODE / IIT) | 2026-Q1 |
| Phase 601~660 | Production Hardening + Multi-Lang VII (Go/Rust/C++/Zig 등) | 2026-Q1 |
| Phase 661~670 | Advanced AI (Transformer / GNN / Diffusion / Federated) | 2026-Q2 초 |
| Phase 671~680 | Hardware Integration SITL (PX4 / ROS2 / MQTT / Jetson) | 2026-Q2 초 |
| Phase 681~690 | UTM 표준 준수 (K-UTM / ADS-B / Remote ID / FAA LAANC / ICAO) | 2026-Q2 초 |

3,330+ 자동화 테스트 / 86%+ 커버리지 / 590+ 모듈 / 50+ 언어 / 120K+ LOC.

---

## 진행 중 — Phase 691~720 (3 트랙 병렬)

각 Phase 는 2~5일 단위 스프린트.

### Track A — 실기 드론 통합 (P691~P700)

SITL 에서 검증된 제어 스택을 실제 하드웨어로 이식.

| ID | 작업 | 외부 의존 |
|----|------|----------|
| P691 | Pixhawk 6X / Cube Orange 펌웨어 + PX4 v1.15+ | 하드웨어 |
| P692 | Jetson Orin Nano 컴패니언 컴퓨터 MAVLink 브릿지 | 하드웨어 |
| P693 | 실기 Remote ID 방송 (ASTM F3411 v2.0) | — |
| P694 | RTK-GPS 측위 + AirspaceController 피드백 | 하드웨어 |
| P695 | Failsafe 로직 (RTL / Geofence) | — |
| P696 | 다중 기체 PTP/NTP 동기화 (<10ms jitter) | — |
| P697 | 실내 Motion Capture (Vicon/Optitrack) HITL | 시설 |
| P698 | 실외 소규모 스웜 (3-5기) 비행 시험 | 비행 허가 |
| P699 | 풍동 / 강우 / 저조도 시나리오 실측 | 시설 |
| P700 | HITL 통합 보고서 + FMEA | — |

**의존 일정**: 하드웨어 도착 → 시설 / 비행 허가 → P698~P700.

### Track B — 연구·논문화 (P701~P710)

캡스톤 결과물을 학술적 기여로 정제.

| ID | 작업 | 마일스톤 |
|----|------|---------|
| P701 | 논문 주제 + 기여 포인트 3개 도출 | 2026-Q2 |
| P702 | 선행 연구 서베이 (30편, IROS/ICRA/AIAA) | 2026-Q2 |
| P703 | 벤치마크 데이터셋 공개 (7+3) | 2026-Q3 |
| P704 | Reproducibility 패키지 (Docker + 시드) | 2026-Q3 |
| P705 | 평가 메트릭 정형화 | 2026-Q3 |
| P706 | 비교 실험 (vs ORCA, VO, CBS) | 2026-Q3 |
| P707 | 논문 초안 (IROS 2026 / AIAA SciTech 2027) | 2026-Q3 ~ Q4 |
| P708 | 내부 리뷰 + 지도교수 피드백 (3회) | 2026-Q4 |
| P709 | 공식 투고 + arXiv 프리프린트 | 2026-Q4 |
| P710 | 학술대회 발표 슬라이드 / 포스터 | 2027-Q1 |

### Track C — 배포·서비스화 (P711~P720)

공역 관리자용 대시보드를 SaaS 수준으로 안정화.

| ID | 작업 | 결과물 |
|----|------|-------|
| P711 | Dash → FastAPI + React 리팩토링 | 신규 web/api 디렉터리 |
| P712 | OAuth2 + RBAC + 감사 로그 | 인증/권한 |
| P713 | WebSocket 1 kHz 채널 | 실시간 스트림 |
| P714 | PostgreSQL + TimescaleDB (30일 보존) | 이력 저장 |
| P715 | Docker Compose → K8s Helm | 컨테이너 오케스트레이션 |
| P716 | CI/CD (Actions → 레지스트리 → 스테이징) | 자동 배포 |
| P717 | 부하 테스트 (100기 60FPS) | 성능 검증 |
| P718 | 관측성 (Prometheus + Grafana + Loki) | 운영 가시성 |
| P719 | 보안 감사 (OWASP ZAP + CVE 스캔) | 베타 진입 게이트 |
| P720 | 공개 베타 (3 파일럿 기관, 4주 피드백) | 베타 사용자 |

---

## 12-개월 누적 목표 (2026-04 ~ 2027-04)

- ✅ 실기 비행 시험 — 광주광역시 특정 구역 실증 실험 (Track A 완성)
- ✅ IEEE / IROS / AIAA 1편 이상 투고 (Track B 완성)
- ✅ 베타 SaaS 대시보드 + 3개 파일럿 기관 도입 (Track C 완성)
- ✅ K-UTM 표준 인증 1건
- ✅ 특허 1건 출원 + 1건 등록

---

## 협력·기여 환영 영역

| 영역 | 내용 |
|------|------|
| **하드웨어** | PX4 / Pixhawk / Jetson 실기 검증 — 테스트베드 협력 |
| **시설** | Vicon/Optitrack 실내 모캡 / 풍동 — 셋업 1~2주 |
| **데이터셋** | 도심 드론 비행 로그 익명 기여 (벤치마크용) |
| **법규** | 국내 / 국제 UTM 인증 상담 |
| **파일럿 기관** | 베타 사용자 (P720) — 4주 피드백 |

문의: [GitHub Issues](https://github.com/sun475300-sudo/swarm-drone-atc/issues) / sun475300@gmail.com.

---

*Last updated: 2026-04-26. 다음 갱신: 매월 말.*
