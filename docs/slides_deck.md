# SDACS 발표 슬라이드 (Marp 형식)

이 파일은 Marp(Markdown Presentation Ecosystem)로 즉시 PowerPoint/PDF/HTML로 변환 가능합니다.

**변환 방법** (Node.js 필요):
```bash
npm install -g @marp-team/marp-cli
marp slides_deck.md -o slides.pptx     # PowerPoint
marp slides_deck.md -o slides.pdf      # PDF
marp slides_deck.md -o slides.html     # HTML
```

또는 VS Code 확장 "Marp for VS Code" 설치 후 미리보기로 확인.

---

```marp
---
marp: true
theme: default
paginate: true
size: 16:9
backgroundColor: white
color: #1a1a1a
header: 'SDACS · 군집드론 공역통제 자동화 시스템'
footer: '캡스톤 3조 · 2026'
style: |
  section {
    font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
  }
  h1 {
    color: #0055AA;
    font-size: 56px;
  }
  h2 {
    color: #0055AA;
    border-bottom: 3px solid #60a5fa;
    padding-bottom: 8px;
  }
  .big-number {
    font-size: 120px;
    font-weight: 900;
    color: #FB8C00;
    text-align: center;
    margin: 30px 0;
  }
  .quote {
    font-size: 36px;
    font-style: italic;
    color: #444;
    text-align: center;
    padding: 40px;
    border-left: 6px solid #60a5fa;
    margin: 20px 50px;
  }
  table {
    margin: 0 auto;
    font-size: 22px;
  }
  th {
    background: #0055AA;
    color: white;
    padding: 12px;
  }
  td {
    padding: 10px 14px;
  }
---

<!-- _class: title -->
<!-- _paginate: false -->

# 하늘에도
# 신호등이 필요합니다

**SDACS**
Swarm Drone Airspace Control System

군집드론 공역통제 자동화 시스템

캡스톤 3조 · 2026

---

# 갑자기 질문 하나

## 도시 위 100미터 상공에
## **자동차 3만 대가 더** 떠다닌다면?

<br>

말도 안 되는 얘기 같지만,
드론이 늘어나는 낮은 하늘에서는
이미 비슷한 일이 시작되고 있습니다.

---

# 대한민국 등록 드론

<div class="big-number">90만 대+</div>

<small>출처: 국토교통부 드론 등록 통계 (2024 기준)</small>

배송·촬영·구조·점검·행사용 드론까지 계속 증가

<br>

**그런데 — 누가 교통정리를 할까요?**

---

# 기존 방식의 빈틈

| 방식 | 한계 |
|------|------|
| 고정 레이더 | 설치 비용·시간이 크고 도시 사각지대 |
| 중앙 관제 | 한 곳에 부담 집중, 장애에 취약 |
| 사전 경로 | 바람·고장·돌발 상황에 약함 |

<br>

→ **신호등 없는 하늘**에서 무제약 비행

---

# 핵심 문제

<div class="quote">
응급 드론, 배송 드론, 촬영 드론이<br>
같은 하늘을 쓸 때 —<br>
<br>
누가 먼저 가고,<br>
누가 비켜야 할까요?
</div>

---

# 우리의 발상 전환

<br>

## 레이더로 드론을 보는 대신

## **드론이 직접**
## 하늘의 관제망이 됩니다

<br>

고정된 관제탑이 아닌, 움직이는 관제망

---

# 시스템 이름 + 구조

<br>

# **SDACS**
**Swarm Drone Airspace Control System**
군집드론 공역통제 자동화 시스템

<br>

| 계층 | 책임 | 주기 |
|------|------|------|
| L1 (드론) | 비행 제어, 회피, 배터리 | 10 Hz |
| L2 (관제) | 충돌 예측, 어드바이저리 | 1 Hz |
| L3 (시뮬) | 이벤트 엔진, 바람 모델, MC | 이벤트 기반 |
| L4 (UI/CLI) | 3D 대시보드, 명령 | 실시간 |

> 분산 자율 제어 + 중앙 조정 결합

---

# 작동 비유 4가지

<br>

| 비유 | 역할 |
|------|------|
| 🚥 **신호등** | 멈추고 가기 |
| 🗺️ **내비게이션** | 미리 길 찾기 |
| 🧲 **자석** | 너무 가까우면 밀어내기 |
| 🚏 **톨게이트** | 순서대로 통과하기 |

---

# 5겹 안전장치

<br>

| # | 단계 | 비유 | 알고리즘 |
|---|------|------|---------|
| 1 | 출발 전 — 길 미리 짜기 | 내비게이션 | A* / CBS |
| 2 | 90초 전 — 충돌 예측 | 일기예보 | CPA |
| 3 | 가까워지면 — 자동 회피 | 자석 척력 | APF |
| 4 | 위험하면 — 잠시 대기 | 비상 브레이크 | Advisory |
| 5 | 통신 끊기면 — 안전 복귀 | 비둘기 귀소 | RTL |

> 한 단계가 놓친 위험을 다음 단계가 받아냅니다.

---

# 핵심: 90초 미리 예측

<br>

```
   90초 뒤
   🚁 ────💥──── 🚁
   "이대로면 가까워집니다"

   지금
   🚁 ↗️   ↘️ 🚁
   "경로를 조금 바꿉니다"
```

<br>

사고 임박 후 피하는 것이 아니라, **먼저 보고 조정**

---

# 바람과 돌발 상황 대응

<br>

| 조건 | 안전 간격 |
|------|---------|
| 약한 바람 | 일반 간격 유지 |
| **강한 바람** | **더 넓게 떨어져 비행** |

<br>

> 비 오는 날 자동차 사이 거리를 더 넓히는 것과 같습니다.

---

# 🎬 라이브 데모

<br>

## 지금부터 3D 시뮬레이터로
## **직접 보겠습니다**

<br>

| 단계 | 시연 |
|------|------|
| 0:00 | 기본 비행 (자유 시나리오) |
| 1:00 | 드론 수 증가 (혼잡 상황) |
| 2:00 | 강풍 조건 (안전 간격 확대) |
| 3:00 | 침입 드론 (회피 동작) |
| 4:00 | 결과 지표 (실시간 패널) |

> 💡 Plan B: 라이브 실패 시 `docs/offline_demo_backup.html` 활용

---

# 데모: 9개 시뮬레이션 시나리오 결과

| 시나리오 | 드론 | 해결률 | SLA 99.5% |
|---------|------|-------|-----------|
| swarm_autonomous_no_preplan | 20 | 100.00% | ✅ |
| route_conflict | 100 | 99.80% | ✅ |
| high_density | 100 | 99.56% | ✅ |
| mass_takeoff | 100 | 99.56% | ✅ |
| emergency_failure | 80 | 99.45% | ⚠️ |
| weather_disturbance | 100 | 99.38% | ⚠️ |
| adversarial_intrusion | 50+ | 98.96% | ⚠️ |
| multi_city | 240 | 98.49% | ⚠️ |
| comms_loss | 50 | 97.59% | ⚠️ |

<small>※ 각 시나리오 1회 시뮬레이션 결과 · 시드 191664964</small>

---

# 검증의 깊이

<br>

| 항목 | 규모 |
|------|-----|
| 반복 실험 (Monte Carlo Full 설계) | 38,400회 (384 설정 × 100 시드) |
| 반복 실험 (Quick 모드 실측) | 80회 (16 설정 × 5 시드) |
| 자동 테스트 (pytest 수집) | 3,083개 (CPU 환경) |
| 운영 시나리오 | 9개 |
| 표준 벤치마크 | 10개 |
| Python 모듈 | 590+개 |

---

# 사회적 가치

<br>

| 분야 | 기대 효과 |
|------|---------|
| 🏥 응급 의료 | 더 빠른 도착 가능성 |
| 🚒 화재 정찰 | 복잡한 현장 안전 탐색 |
| 📦 배송 드론 | 더 많은 수 동시 운영 |
| 🎉 행사 안전 | 돌발 상황 대응력 향상 |
| 🏙️ 도시 관제 | 분산 자율 인프라 구축 |

---

# 솔직한 한계

<br>

✅ **현재까지**: 시뮬레이션 검증 단계

⏭️ **다음 단계**:
- 실제 드론 연동 (실기 통합)
- 규제 협의
- 통신·보안 강건성 검증
- 도심 환경 실증

<br>

> "완성된 상용 서비스"가 아니라
> "검증 가능한 다음 단계의 기반"

---

# 결론

<br>

<div class="quote">
하늘에는 신호등이 없습니다.<br>
<br>
<strong>SDACS는</strong><br>
<strong>그 신호등을 소프트웨어로 만드는 시도입니다.</strong>
</div>

---

# 자료 및 연락

<br>

| 항목 | 링크 |
|------|------|
| 공식 허브 | `docs/go.html` |
| 3D 시뮬레이터 v2 | `docs/swarm_3d_simulator_v2.html` |
| 검증 보고서 | `docs/verification_report.md` |
| Q&A 응답 카드 | `docs/qa_response_card.md` |
| 오프라인 백업 | `docs/offline_demo_backup.html` |
| GitHub | github.com/sun475300-sudo/swarm-drone-atc |

<br>

# 질문 받겠습니다

---

# 부록 A: 데모 단축키

<br>

| 키 | 기능 |
|---|------|
| **1** | Cinematic 카메라 (영화) |
| **2** | ATC 카메라 (관제 시점) |
| **3** | Data 카메라 (분석용) |
| **4** | Follow 카메라 (드론 추적) |

<br>

시나리오 선택: free / crossing / voronoi / cbs / gnn / diffusion / wind / vertiport

---

# 부록 B: 핵심 KPI 8개

<br>

| KPI | 값 |
|-----|-----|
| 등록 드론 | 90만 대+ |
| 충돌 예측 시간 창 | 90초 |
| Monte Carlo 검증 | 38,400회 |
| 자동 테스트 | 3,083개 |
| 핵심 모듈 | 590+개 |
| 운영 시나리오 | 9개 |
| 표준 벤치마크 | 10개 |
| GPU 검증 환경 | RTX 5070 Ti |

---

# 부록 C: 시스템 4계층

<br>

| 계층 | 주기 | 책임 |
|------|------|------|
| L1 드론 에이전트 | 10Hz | 비행 제어, 회피, 배터리 |
| L2 공역 컨트롤러 | 1Hz | 충돌 예측, 어드바이저리 |
| L3 시뮬 엔진 | 이산 | SimPy, 바람, MC |
| L4 UI / CLI | 실시간 | 3D 대시보드, 명령 |

<br>

분산 자율 제어 + 중앙 조정 결합

---

# 부록 D: 발견된 코드 이슈 (정직)

<br>

| 이슈 | 설명 |
|------|------|
| `advisory_latency` | 메트릭 정의는 있으나 호출 누락 (출력 0) |
| `comms_loss SLA` | 97.59% (목표 99.5% 미달) |
| `multi_city SLA` | 98.49% (240대 부하 시 한계) |
| torch 모듈 누락 | 5개 테스트 파일 collection 에러 |

<br>

> 검증 결과는 `docs/verification_report.md`에 모두 공개
```

---

## 슬라이드 변환 가이드

### 옵션 1: VS Code Marp 미리보기
1. VS Code에서 `Marp for VS Code` 확장 설치
2. 이 파일 열기
3. 우측 상단 미리보기 버튼 클릭
4. 내보내기: 우측 클릭 → "Marp: Export slide deck..." → PPTX 선택

### 옵션 2: 명령줄 변환
```powershell
# Node.js 설치 후
npm install -g @marp-team/marp-cli

# PowerPoint 변환
marp docs/slides_deck.md -o slides.pptx

# PDF 변환
marp docs/slides_deck.md -o slides.pdf

# HTML (브라우저로 발표 가능)
marp docs/slides_deck.md -o slides.html
```

### 옵션 3: 온라인 변환
- https://web.marp.app/ 에서 마크다운 붙여넣고 PPTX 다운로드

### 총 슬라이드 수: 19장
- 메인: 15장 (오프닝~결론)
- 부록: 4장 (단축키, KPI, 4계층, 이슈)
