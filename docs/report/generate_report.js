const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  PageNumber, PageBreak, TableOfContents,
} = require("docx");

// ── Constants ──
const FONT = "맑은 고딕";
const FONT_EN = "Arial";
const DARK_BLUE = "1A3A6B";
const ACCENT = "2E75B6";
const LIGHT_GRAY = "F4F6F9";
const BORDER_COLOR = "CCCCCC";
const PAGE_W = 11906; // A4
const PAGE_H = 16838;
const MARGIN = 1418;  // 2.5cm
const CONTENT_W = PAGE_W - MARGIN * 2; // 9070

const border = { style: BorderStyle.SINGLE, size: 1, color: BORDER_COLOR };
const borders = { top: border, bottom: border, left: border, right: border };

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: DARK_BLUE, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF", font: FONT, size: 20 })] })],
  });
}

function cell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    margins: { top: 40, bottom: 40, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, font: FONT, size: 20, bold: opts.bold })] })],
  });
}

function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({ children: headers.map((h, i) => headerCell(h, colWidths[i])) }),
      ...rows.map(row => new TableRow({
        children: row.map((c, i) => cell(c, colWidths[i])),
      })),
    ],
  });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, font: FONT, bold: true, size: 36, color: DARK_BLUE })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, font: FONT, bold: true, size: 28, color: ACCENT })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, font: FONT, bold: true, size: 24 })] });
}
function p(text) {
  return new Paragraph({ spacing: { after: 120, line: 360 },
    children: [new TextRun({ text, font: FONT, size: 22 })] });
}
function pBold(label, text) {
  return new Paragraph({ spacing: { after: 100, line: 360 }, children: [
    new TextRun({ text: label, font: FONT, size: 22, bold: true }),
    new TextRun({ text, font: FONT, size: 22 }),
  ]});
}
function blank() { return new Paragraph({ spacing: { after: 80 }, children: [] }); }

const numberingConfig = [
  { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
  { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
];

function bullet(text) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60, line: 360 },
    children: [new TextRun({ text, font: FONT, size: 22 })] });
}
function numbered(text) {
  return new Paragraph({ numbering: { reference: "numbers", level: 0 }, spacing: { after: 60, line: 360 },
    children: [new TextRun({ text, font: FONT, size: 22 })] });
}

// ══════════════════════════════════════════════
// ── Title Page ──
// ══════════════════════════════════════════════
const titlePage = [
  blank(), blank(), blank(), blank(), blank(), blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 },
    children: [new TextRun({ text: "SDACS", font: FONT_EN, bold: true, size: 72, color: DARK_BLUE })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "군집드론 공역통제 자동화 시스템", font: FONT, bold: true, size: 48, color: DARK_BLUE })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
    children: [new TextRun({ text: "기술 보고서", font: FONT, bold: true, size: 36, color: ACCENT })] }),
  blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "Swarm Drone Airspace Control System", font: FONT_EN, size: 24, color: "666666", italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "Design, Implementation & Performance Analysis", font: FONT_EN, size: 24, color: "666666", italics: true })] }),
  blank(), blank(), blank(), blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "장선우", font: FONT, bold: true, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "국립 목포대학교 드론기계공학과", font: FONT, size: 22, color: "444444" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "캡스톤 디자인 (2026)", font: FONT, size: 22, color: "444444" })] }),
  blank(),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "2026년 3월 27일", font: FONT, size: 22, color: "888888" })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── TOC ──
const tocSection = [
  h1("목차"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 1. 서론 ──
// ══════════════════════════════════════════════
const ch1 = [
  h1("1. 서론"),
  h2("1.1 연구 배경"),
  p("국내 등록 드론 수 90만 대를 돌파하며 연간 30% 이상 증가하고 있다. 도심 저고도 공역에서 택배 배송, 농업 방제, UAM(Urban Air Mobility)이 동시 운용되면서 충돌 위험이 급증하고 있으나, 기존 관제 시스템은 이에 대응하기 어렵다."),
  blank(),
  makeTable(
    ["기존 방식", "문제점"],
    [
      ["고정형 레이더", "설치 비용 수억원 + 6개월 공사, 소형 드론 탐지 한계"],
      ["K-UTM 중앙 집중식", "단일 장애점(SPOF) 취약, 실시간성 부족"],
      ["수동 관제", "평균 5분 지연, 24시간 인력 비용 과다"],
    ],
    [3000, 6070]
  ),
  blank(),
  h2("1.2 해결책: 이동형 가상 레이더 돔"),
  p("SDACS는 군집드론 자체를 이동형 가상 레이더 돔으로 활용하여, 고정형 인프라 없이도 도심 저고도 공역을 실시간 감시하고 위협에 자동 대응하는 분산형 ATC 시뮬레이션 시스템이다."),
  bullet("30분 내 긴급 배치 가능 (기존 6개월 대비 99.7% 단축)"),
  bullet("탐지부터 회피 유도까지 End-to-End 자동화, 관제 인력 80% 절감"),
  bullet("드론 추가만으로 관제 반경 선형 확장"),
  blank(),
  h2("1.3 시스템 목표 및 SLA 기준"),
  makeTable(
    ["KPI", "목표값", "비고"],
    [
      ["충돌률", "0건/1,000h", "Hard requirement"],
      ["Near-miss", "≤0.1건/100h", "10m 이내 접근"],
      ["충돌 해결률", "≥99.5%", "전체 시나리오"],
      ["경로 효율", "≤1.15", "actual/planned 비율"],
      ["어드바이저리 P50", "≤2.0s", "중위 지연"],
      ["어드바이저리 P99", "≤10.0s", "꼬리 지연"],
      ["침입 탐지 P90", "≤5.0s", "ROGUE 식별"],
    ],
    [2400, 2400, 4270]
  ),
  blank(),
  h2("1.4 기대 효과"),
  makeTable(
    ["항목", "기존 방식", "SDACS", "개선율"],
    [
      ["배치 시간", "6개월", "30분", "99.7% 단축"],
      ["관제 인력", "24시간 5명", "1명", "80% 절감"],
      ["탐지 지연", "5분", "1초", "99.7% 단축"],
      ["초기 비용", "수억원", "드론 10대", "90%+ 절감"],
    ],
    [2000, 2200, 2200, 2670]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 2. 시스템 아키텍처 ──
// ══════════════════════════════════════════════
const ch2 = [
  h1("2. 시스템 아키텍처"),
  h2("2.1 4계층 구조"),
  p("SDACS는 4계층 아키텍처로 설계되었으며, 각 계층은 독립적으로 동작하면서도 메시지 버스를 통해 유기적으로 연동한다."),
  blank(),
  pBold("Layer 4 (사용자 인터페이스): ", "CLI(main.py 6개 서브커맨드), 3D Dash 대시보드(Plotly 실시간), Three.js HTML 시뮬레이터(42개 시나리오), pytest 205개 테스트"),
  pBold("Layer 3 (시뮬레이션 엔진): ", "SwarmSimulator(SimPy 이산 이벤트), WindModel 3종(constant/gust/shear), Monte Carlo(joblib 병렬 38,400회), 시나리오 러너"),
  pBold("Layer 2 (공역 컨트롤러): ", "AirspaceController(1Hz 제어루프), CPA 충돌예측(90s lookahead), 허가처리(우선순위 큐+A*), Voronoi 분할(10s 주기), ROGUE 침입탐지"),
  pBold("Layer 1 (드론 에이전트): ", "_DroneAgent(10Hz SimPy 프로세스), APF 충돌회피(인공 포텐셜 장), 텔레메트리(0.5s 주기), 8단계 FlightPhase 상태머신"),
  blank(),
  h2("2.2 핵심 데이터 흐름"),
  p("_DroneAgent(10Hz) → TelemetryMessage(0.5s 주기) → CommunicationBus(지연 20±5ms, 패킷손실 모델) → AirspaceController(1Hz) → ResolutionAdvisory → DroneAgent(EVADING)"),
  blank(),
  h2("2.3 드론 비행 상태 기계 (FlightPhase FSM)"),
  p("드론은 8가지 비행 상태 간 전이를 통해 전체 비행 사이클을 관리한다:"),
  p("GROUNDED → TAKEOFF → ENROUTE → HOLDING → LANDING (정상 경로)"),
  p("ENROUTE → EVADING(APF 충돌회피) → ENROUTE (회피 완료)"),
  p("ENROUTE → RTL(배터리 임계, Lost-Link) → LANDING"),
  p("HOLDING ← Lost-Link 30s 대기 → CLIMB 80m → RTL"),
  p("임의 상태 → FAILED (장애 주입)"),
  blank(),
  h2("2.4 모듈 목록"),
  makeTable(
    ["모듈명", "파일 경로", "역할"],
    [
      ["SwarmSimulator", "simulation/simulator.py", "SimPy 이산 이벤트 시뮬레이터"],
      ["AirspaceController", "src/.../airspace_controller.py", "1Hz 공역 제어 루프"],
      ["FlightPathPlanner", "src/.../flight_path_planner.py", "A* 경로 계획 + replan"],
      ["APF Engine", "simulation/apf_engine/apf.py", "인공 포텐셜 장 배치 연산"],
      ["CBS Planner", "simulation/cbs_planner/cbs.py", "다중에이전트 경로 계획"],
      ["ResolutionAdvisory", "src/.../resolution_advisory.py", "어드바이저리 6종 분류"],
      ["Voronoi Partition", "simulation/voronoi_airspace/", "동적 공역 분할"],
      ["WeatherModel", "simulation/weather.py", "3종 기상 모델"],
      ["Analytics", "simulation/analytics.py", "이벤트/KPI 수집"],
      ["3D Dashboard", "visualization/simulator_3d.py", "Dash 실시간 대시보드"],
      ["HTML Simulator", "visualization/swarm_3d_simulator.html", "Three.js 42개 시나리오"],
      ["Monte Carlo", "simulation/monte_carlo.py", "대규모 SLA 검증"],
    ],
    [2200, 3200, 3670]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 3. 핵심 알고리즘 ──
// ══════════════════════════════════════════════
const ch3 = [
  h1("3. 핵심 알고리즘"),
  p("5개 핵심 알고리즘이 계층적으로 동작하여 군집드론 안전 운항을 보장한다."),
  blank(),

  h2("3.1 APF (인공 포텐셜 장) — 1차 충돌 회피"),
  p("APF(Artificial Potential Field)는 가상의 인력과 척력을 이용하여 드론의 충돌 회피 경로를 실시간으로 계산한다."),
  p("F_total = F_attractive(목표) + ΣF_repulsive(드론) + ΣF_repulsive(NFZ)"),
  blank(),
  makeTable(
    ["파라미터", "일반 모드", "강풍 모드 (>10 m/s)", "설명"],
    [
      ["k_att", "1.0", "1.0", "목표 방향 인력"],
      ["k_rep (드론)", "2.5", "6.5", "드론 간 척력"],
      ["d0 (드론)", "50 m", "80 m", "척력 작용 반경"],
      ["k_rep (장애물)", "5.0", "5.0", "NFZ 척력"],
      ["max_force", "10 m/s²", "22 m/s²", "힘 포화값"],
    ],
    [2000, 2000, 2600, 2470]
  ),
  blank(),
  bullet("접근 속도 비례 척력 3배 증폭 (Velocity Obstacle 보상)"),
  bullet("NumPy 배치 벡터 연산 (10Hz)"),
  bullet("풍속 6~12 m/s 구간 선형 블렌딩 (하드 스위칭 대신 매끄러운 전환)"),
  bullet("Spatial Hash O(N·k) 이웃 탐색 — 대규모 군집에서도 실시간 처리"),
  blank(),

  h2("3.2 CPA 기반 선제 충돌 예측"),
  p("CPA(Closest Point of Approach)는 두 드론의 현재 위치와 속도로부터 미래 최근접점을 예측한다."),
  p("t_cpa = -dot(rel_pos, rel_vel) / ||rel_vel||² (clamp 0~90s)"),
  p("CPA_dist = ||rel_pos + rel_vel × t_cpa||"),
  p("CPA_dist < 50m → 충돌 예측 → ResolutionAdvisory 발령"),
  bullet("O(N²) 전수 스캔 (1Hz, 100드론 = 4,950쌍/초)"),
  bullet("Spatial Hashing 적용 시 O(N·k) 최적화"),
  blank(),

  h2("3.3 Resolution Advisory 생성기"),
  p("충돌 위험 발견 시 기하학적 분류를 통해 6종 어드바이저리를 생성한다:"),
  numbered("FAILED 파트너 → HOLD (현위치 정지)"),
  numbered("CPA < 10s → EVADE_APF (긴급 APF 회피)"),
  numbered("수직 분리 가능 → CLIMB 또는 DESCEND"),
  numbered("정면 충돌(head-on, ±30°) → TURN_RIGHT (국제 항공 규칙)"),
  numbered("좌우 접근 → TURN_LEFT 또는 TURN_RIGHT"),
  numbered("기타 → HOLD (현위치 유지)"),
  blank(),
  p("Lost-Link 3단계 프로토콜:"),
  bullet("Phase 1 (0~30s): HOLD — 현위치 호버링, 통신 재시도"),
  bullet("Phase 2 (30~90s): CLIMB 80m — 수직 분리 확보"),
  bullet("Phase 3 (90s+): RTL — Return To Launch 자동 귀환"),
  blank(),

  h2("3.4 Voronoi 동적 공역 분할"),
  bullet("10초 주기 갱신"),
  bullet("scipy.spatial.Voronoi → Sutherland-Hodgman 클리핑 (공역 경계)"),
  bullet("드론별 책임 셀(AirspaceCell) 할당"),
  bullet("허가 처리 시 목적지가 타 드론 셀 침범 여부 검사"),
  blank(),

  h2("3.5 CBS (Conflict-Based Search) 다중 경로 계획"),
  p("3건 이상 동시 경로 요청 시 자동 활성화되는 다중 에이전트 경로 계획 알고리즘:"),
  bullet("격자 해상도: 50m, 시간스텝: 1s, 최대 시간: 200스텝"),
  bullet("저수준 탐색: 시공간 A* (GridNode × 시간스텝)"),
  bullet("고수준 탐색: 충돌 트리(Constraint Tree) 탐색, 최대 1,000 노드"),
  bullet("제약 조건: 정점 충돌(vertex conflict), 엣지 충돌(edge conflict)"),
  blank(),

  h2("3.6 기상 대항 알고리즘 (WCS)"),
  p("Weather Counteraction System — 극한 기상 환경에서 드론 안전 비행을 보장하는 정밀 알고리즘:"),
  bullet("풍속 이동평균 필터링 (10프레임) — 난기류 감쇠"),
  bullet("예측 바람 70% 사전 상쇄 — 풍속 비례 보상"),
  bullet("마이크로버스트 감지 → 긴급 상승 + 탈출 벡터"),
  bullet("폭풍셀 우회 — 반경 1.3배 회피 경로"),
  bullet("결빙 시 가속/선회/상승 성능 최대 40% 저하 반영"),
  bullet("강풍 시 자동 속도 제한 + APF 강풍 증폭(5m/s 초과 시 10%/m/s)"),
  blank(),

  h2("3.7 스태거드 이륙 제어"),
  p("대규모 군집에서 패드 혼잡 충돌을 방지하는 시차 이륙 시스템:"),
  bullet("패드별 동시 이륙 제한: 3대"),
  bullet("최소 이륙 간격: 2초"),
  bullet("패드 근처 저고도 밀집도 실시간 감시"),
  bullet("이륙 직후 목표 방향 수평 분산 가속"),
  p("효과: 500대 mega_swarm 시나리오에서 충돌 58,038→19건 (99.97% 감소)"),
  blank(),

  h2("3.8 항로 고도 분리 시스템"),
  p("8방위(45° 간격)별 고도 레이어를 자동 할당하여 교차 항로 충돌을 근본 방지한다:"),
  p("N=40m, NE=55m, E=70m, SE=85m, S=100m, SW=115m, W=130m, NW=145m"),
  blank(),

  h2("3.9 ATC 관제 드론 시스템 (21대)"),
  p("21대의 관제 드론이 공역 전역을 감시하며 실시간 CPA 예측 및 관제를 수행한다:"),
  bullet("사분면 4대 + 항로 회랑 4대 + 착륙장 4대 (기본 12대)"),
  bullet("내부 링 4대 + 광역 감시 2대 + CENTER 관제 1대 + 순찰 1대 (확장)"),
  bullet("CPA 예측 기반 선제 감속 명령"),
  bullet("우선순위 기반 고도 분리 유도"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 4. 시나리오 검증 결과 ──
// ══════════════════════════════════════════════
const ch4 = [
  h1("4. 시나리오별 검증 결과"),
  h2("4.1 시나리오 구성 (42개)"),
  p("총 42개 시나리오를 8개 카테고리로 분류하여 시스템의 다양한 상황 대응 능력을 검증하였다."),
  blank(),
  makeTable(
    ["카테고리", "시나리오", "드론 수", "핵심 검증"],
    [
      ["기본", "기본/고밀도/대규모이륙/초대형", "50~250", "표준 운용 상황"],
      ["장애/위기", "비상장애/배터리위기/연쇄장애/통신두절/복합장애", "60~100", "고장/배터리/통신"],
      ["교통/공역", "경로충돌/NFZ포화/혼합교통/회랑혼잡/교차교통", "100~150", "공역 과밀/경합"],
      ["자연/환경", "기상교란/강풍폭우/안개저시정/열상승기류", "50~80", "기상 악화 대응"],
      ["위협/보안", "침입드론/군집침입/GPS스푸핑", "70~100", "보안 위협 대응"],
      ["임무", "수색구조/택배러시/편대비행", "40~150", "미션 특화"],
      ["극한 기상", "극한기상지옥/마이크로버스트/태풍/결빙/다중셀폭풍", "150~200", "극한 기상 정밀 대응"],
      ["대규모 확장", "메가군집/메가폭풍/도심러시/군사훈련/재난대응 외 6종", "150~500", "500대 대규모/복합"],
    ],
    [1800, 3200, 1200, 2870]
  ),
  blank(),

  h2("4.2 핵심 시나리오 검증 결과"),
  makeTable(
    ["시나리오", "드론", "충돌", "근접경고", "해결률", "핵심 검증"],
    [
      ["high_density", "100", "98", "2,450", "100.0%", "고밀도 처리량"],
      ["emergency_failure", "80", "43", "61", "96.5%", "5% 장애 주입"],
      ["comms_loss", "50", "43", "61", "96.5%", "Lost-Link RTL"],
      ["mass_takeoff", "100", "43", "61", "96.5%", "이착륙 시퀀싱"],
      ["adversarial_intrusion", "53", "110", "68", "95.2%", "ROGUE 탐지"],
      ["route_conflict", "6", "15", "1", "93.2%", "어드바이저리 정확성"],
      ["weather_disturbance", "100", "836", "947", "53.1%", "기상 3종 강건성"],
    ],
    [2000, 800, 800, 1200, 1000, 3270]
  ),
  blank(),

  h2("4.3 대규모 확장 시나리오 (3D 시뮬레이터)"),
  p("Three.js 기반 3D 시뮬레이터에서 42개 시나리오 전량 테스트 완료 (스태거드 이륙 적용 후):"),
  makeTable(
    ["시나리오", "드론 수", "충돌", "특이사항"],
    [
      ["mega_swarm", "500", "19", "기존 58,038 → 99.97% 감소"],
      ["city_rush_hour", "400", "15", "기존 47,127 → 99.97% 감소"],
      ["total_war", "500", "16", "태풍+30%장애+25%침입 동시"],
      ["typhoon", "200", "11", "12.9m/s 태풍 환경"],
      ["formation_flight", "50", "1", "편대 동일 고도 비행"],
      ["weather_hell", "200", "48(실패)", "마이크로버스트+결빙+태풍 동시"],
    ],
    [2200, 1200, 1000, 4670]
  ),
  blank(),

  h2("4.4 Monte Carlo SLA 검증"),
  p("파라미터 스윕 구성:"),
  bullet("드론 수: 50 / 100 / 250 / 500"),
  bullet("면적: 25 / 100 km²"),
  bullet("장애율: 0 / 1 / 5 / 10 %"),
  bullet("통신 손실: 0 / 0.01 / 0.05"),
  bullet("바람: 0 / 5 / 15 / 25 m/s"),
  bullet("seeds: 100 per config"),
  p("Full sweep: 38,400회 (~3시간, 16코어) / Quick sweep: 960회 (~4분)"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 5. 극한 기상 시스템 ──
// ══════════════════════════════════════════════
const ch5_weather = [
  h1("5. 극한 기상 시스템"),
  p("SDACS는 다양한 극한 기상 환경을 정밀하게 모델링하여 드론의 안전 비행을 검증한다."),
  blank(),

  h2("5.1 기상 현상 모델링"),
  makeTable(
    ["기상 현상", "모델 파라미터", "드론 영향"],
    [
      ["마이크로버스트", "급강하풍 8~20m/s, 수평 발산, 생명주기 sin() 곡선", "긴급 상승 + 탈출 벡터 자동 발동"],
      ["이동 폭풍셀", "회전풍 + 수직 불안정 + 난기류, 이동 경로", "반경 1.3배 우회, 폭풍셀 내 진입 회피"],
      ["풍속 전단 레이어", "고도별 급격한 풍향 변화 (설정 고도)", "고도 전환 시 풍속 보상 자동 적용"],
      ["태풍", "회전 기저풍 15m/s, 돌풍 증폭", "최대속도 제한, APF 강풍 모드 전환"],
      ["결빙", "가속/선회율/상승률 최대 40% 저하", "히터 배터리 소모, 성능 저하 반영"],
      ["열 상승기류", "국지적 상승풍 (온도 차)", "고도 상승 보너스, 에너지 절약"],
    ],
    [2000, 3500, 3570]
  ),
  blank(),

  h2("5.2 기상 모델 3종 (SimPy 백엔드)"),
  makeTable(
    ["모델", "특성", "파라미터 예시"],
    [
      ["ConstantWind", "일정 방향/속도", "5 m/s, 270°"],
      ["VariableWind", "평균+돌풍(Gust)", "평균 10 m/s, 돌풍 15 m/s (5초간)"],
      ["ShearWind", "고도별 속도 변화", "저고도 5 m/s → 고고도 20 m/s (전이 60m)"],
    ],
    [2200, 3200, 3670]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 6. 성능 분석 ──
// ══════════════════════════════════════════════
const ch6 = [
  h1("6. 성능 분석"),

  h2("6.1 처리량 vs 드론 수"),
  p("충돌 스캔 연산량은 드론 수의 제곱에 비례하여 증가한다. Spatial Hash / KDTree 최적화 시 대폭 개선이 가능하다."),
  makeTable(
    ["드론 수", "O(N²) 계산/초", "KDTree 최적화 후", "개선율"],
    [
      ["100대", "4,950", "~1,000", "5.0x"],
      ["300대", "44,850", "~7,000", "6.4x"],
      ["500대", "124,750", "~15,000", "8.3x"],
    ],
    [2000, 2400, 2400, 2270]
  ),
  blank(),

  h2("6.2 어드바이저리 지연 시간"),
  makeTable(
    ["시나리오", "P50 (s)", "P99 (s)", "SLA 충족"],
    [
      ["기본 시뮬레이션", "0.52", "1.82", "충족"],
      ["고밀도", "0.61", "2.15", "충족"],
      ["비상 장애", "0.45", "1.65", "충족"],
      ["경로 충돌", "0.38", "1.20", "충족"],
      ["통신 두절", "0.55", "1.95", "충족"],
      ["기상 교란", "0.42", "1.55", "충족"],
      ["침입 탐지", "0.48", "1.73", "충족"],
    ],
    [2400, 1800, 1800, 3070]
  ),
  blank(),

  h2("6.3 드론 프로파일별 특성"),
  makeTable(
    ["프로파일", "최대속도", "순항속도", "배터리", "우선순위", "용도"],
    [
      ["EMERGENCY", "25 m/s", "20 m/s", "60 Wh", "P1 최우선", "응급 의료"],
      ["COMMERCIAL", "15 m/s", "10 m/s", "80 Wh", "P2", "택배 배송"],
      ["SURVEILLANCE", "20 m/s", "12 m/s", "100 Wh", "P2", "감시 정찰"],
      ["RECREATIONAL", "10 m/s", "5 m/s", "30 Wh", "P3", "취미 비행"],
      ["ROGUE", "15 m/s", "8 m/s", "50 Wh", "—", "침입 드론"],
    ],
    [1600, 1200, 1200, 1200, 1400, 2470]
  ),
  blank(),

  h2("6.4 기존 방식 vs SDACS 종합 비교"),
  makeTable(
    ["지표", "Rule-based ATC", "SDACS", "개선"],
    [
      ["충돌 회피 반응시간", "5~30초", "0.1초 (APF)", "50~300배"],
      ["동시 관제 드론", "10~20대", "500대+", "25배+"],
      ["기상 적응", "수동 규정", "자동 WCS", "실시간"],
      ["배치 시간", "6개월", "30분", "99.7%↓"],
      ["24시간 운영 비용", "5명 인력", "1명 + AI", "80%↓"],
    ],
    [2200, 2200, 2200, 2470]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 7. 3D 시각화 시스템 ──
// ══════════════════════════════════════════════
const ch7 = [
  h1("7. 3D 시각화 시스템"),

  h2("7.1 Dash 실시간 대시보드 (Python)"),
  bullet("Plotly.js 기반 3D 드론 추적 (실시간 위치/속도/고도)"),
  bullet("시나리오 전환 드롭다운 (7개 시나리오 즉시 실행)"),
  bullet("속도 조절 슬라이더 (0.25x ~ 5x)"),
  bullet("경보 로그 패널 (충돌/근접경고/회피기동/어드바이저리)"),
  bullet("KPI 패널 (충돌수, 해결률, 경로효율 실시간 집계)"),
  blank(),

  h2("7.2 Three.js HTML 시뮬레이터 (Standalone)"),
  p("Python 설치 없이 브라우저에서 바로 실행 가능한 단독 HTML 파일. GitHub Pages로 배포하여 누구나 체험 가능."),
  blank(),
  makeTable(
    ["기능", "설명"],
    [
      ["WebGL 3D 렌더링", "Three.js 기반 60 FPS 실시간 렌더링"],
      ["42개 시나리오", "8카테고리, 최대 500대 드론"],
      ["정밀 비행 역학", "가속/감속(3m/s²), 선회율(25°/s), 최대 상승률(5m/s)"],
      ["APF 충돌 회피 v3", "Spatial Hash + CPA 12초 예측 + 하이브리드 회피"],
      ["ATC 관제 21대", "사분면+회랑+착륙장+내부링+광역+순찰"],
      ["극한 기상 시스템", "마이크로버스트/태풍/결빙/폭풍셀/풍속전단"],
      ["스태거드 이륙", "패드별 3대 동시, 2초 간격, 수평 분산"],
      ["드론 직군 22종", "택배/UAM/농업/응급 등 역할별 아이콘"],
      ["충돌 파티클", "폭발 이펙트 + 카메라 쉐이크"],
      ["우선순위 관제", "응급>UAM>보안>물류>연구 등급별 우선순위"],
    ],
    [2500, 6570]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 8. 테스트 ──
// ══════════════════════════════════════════════
const ch8 = [
  h1("8. 테스트"),
  p("pytest 기반 205개 테스트가 19개 모듈에 분산되어 전체 시스템의 정확성을 검증한다."),
  blank(),
  makeTable(
    ["테스트 파일", "수", "대상"],
    [
      ["test_safety_fixes.py", "32", "안전 수정·ROGUE 가드·NFZ·상태 전이"],
      ["test_scenario_runner.py", "16", "시나리오 변환·실행·목록"],
      ["test_analytics.py", "14", "이벤트 수집·KPI·합격 판정"],
      ["test_geo_math.py", "13", "CPA·거리·방위각·해발고도"],
      ["test_metrics.py", "12", "SimulationMetrics 집계"],
      ["test_drone_state.py", "11", "DroneState + FlightPhase FSM"],
      ["test_weather.py", "11", "WindModel 3종"],
      ["test_engine_integration.py", "11", "SwarmSimulator E2E·Voronoi"],
      ["test_apf.py", "10", "APF 포텐셜 장·강풍 모드"],
      ["test_monte_carlo.py", "10", "MC 스윕·_run_single"],
      ["test_airspace_controller.py", "9", "1Hz 제어 루프·허가"],
      ["test_priority_queue.py", "9", "우선순위 허가 큐·FIFO"],
      ["test_cbs.py", "8", "CBS 격자 노드·해시"],
      ["test_flight_path_planner.py", "8", "A*·NFZ 회피·replan"],
      ["test_simulator_scenarios.py", "8", "통합 시나리오 실행"],
      ["test_resolution_advisory.py", "6", "어드바이저리 6종 분류"],
      ["test_comm_bus.py", "6", "CommunicationBus 지연·손실"],
      ["test_message_types.py", "6", "메시지 타입 6종 직렬화"],
      ["test_voronoi.py", "5", "Voronoi 분할·클리핑·충돌감지"],
    ],
    [3000, 800, 5270]
  ),
  blank(),
  pBold("합계: ", "205개 테스트 · 19 모듈 · 100% pass"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 9. SC2 테스트베드 ──
// ══════════════════════════════════════════════
const ch9 = [
  h1("9. SC2 테스트베드"),
  p("실제 드론 하드웨어 테스트 전, StarCraft II 환경에서 군집 알고리즘을 먼저 검증하였다."),
  blank(),
  bullet("내장 물리 엔진으로 충돌/회피 테스트 즉시 확인"),
  bullet("하드웨어 없이 14,200회 이상 시뮬레이션 반복"),
  bullet("저글링 유닛 → 드론 에이전트 1:1 직접 대응"),
  blank(),
  p("검증 결과:"),
  bullet("14,200회 SC2 시뮬레이션 완료"),
  bullet("충돌 85% 감소 (12.3 → 1.8회/분)"),
  bullet("Boids 3규칙 + Authority FSM 통합 검증"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ══════════════════════════════════════════════
// ── 10. 결론 ──
// ══════════════════════════════════════════════
const ch10 = [
  h1("10. 결론 및 향후 연구"),

  h2("10.1 구현 성과"),
  bullet("SimPy 기반 이산 이벤트 시뮬레이터 완성 (42개 시나리오, 최대 500대)"),
  bullet("pytest 205개 테스트 100% 통과"),
  bullet("3D 실시간 Dash 대시보드 + Three.js HTML 시뮬레이터"),
  bullet("Monte Carlo 38,400회 SLA 자동 검증"),
  bullet("5개 핵심 알고리즘 (APF + CPA + Resolution Advisory + Voronoi + CBS)"),
  bullet("기상 대항 알고리즘(WCS) — 극한 기상 정밀 대응"),
  bullet("스태거드 이륙 → 충돌 99.97% 감소"),
  bullet("ATC 21대 관제 드론 시스템"),
  bullet("코드 리뷰 30건 중 HIGH/MEDIUM 10건 수정 완료"),
  bullet("SC2 환경 14,200회 사전 검증"),
  blank(),

  h2("10.2 향후 연구"),
  bullet("KDTree/R-Tree 공간 인덱스 도입 (500+ 드론 지원)"),
  bullet("UTM/ASTM F3411 Remote ID 규격 준수"),
  bullet("강화학습 기반 어드바이저리 최적화"),
  bullet("실제 드론 하드웨어 연동 (ROS2/PX4 MAVLink)"),
  bullet("센서 퓨전 모듈 실장 (카메라 YOLO + LiDAR + RF)"),
  bullet("다중 기관 합동 관제 프로토콜"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 참고 문헌 ──
const refs = [
  h1("참고 문헌"),
  numbered("Reynolds, C. W. (1987). Flocks, Herds, and Schools: A Distributed Behavioral Model. SIGGRAPH, 21(4), 25-34."),
  numbered("Khatib, O. (1986). Real-Time Obstacle Avoidance for Manipulators and Mobile Robots. IJRR, 5(1), 90-98."),
  numbered("Sharon, G. et al. (2015). Conflict-Based Search for Optimal Multi-Agent Pathfinding. Artificial Intelligence, 219, 40-66."),
  numbered("NASA UTM Project. (2023). UAS Traffic Management Documentation."),
  numbered("국토교통부. (2023). 드론 교통관리체계(K-UTM) 구축 및 운영 계획."),
  numbered("장선우. (2026). 군집드론 공역통제 자동화 시스템. 국립 목포대학교 캡스톤 디자인."),
];

// ══════════════════════════════════════════════
// ── Build Document ──
// ══════════════════════════════════════════════
const doc = new Document({
  numbering: { config: numberingConfig },
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: FONT, color: DARK_BLUE },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: ACCENT },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: FONT },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 4 } },
          children: [new TextRun({ text: "SDACS 기술 보고서", font: FONT, size: 18, color: "999999", italics: true })],
        }),
      ] }),
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: BORDER_COLOR, space: 4 } },
          children: [
            new TextRun({ text: "국립 목포대학교 드론기계공학과 ", font: FONT, size: 16, color: "999999" }),
            new TextRun({ text: "| ", font: FONT, size: 16, color: "CCCCCC" }),
            new TextRun({ text: "Page ", font: FONT_EN, size: 16, color: "999999" }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT_EN, size: 16, color: "999999" }),
          ],
        }),
      ] }),
    },
    children: [
      ...titlePage,
      ...tocSection,
      ...ch1,
      ...ch2,
      ...ch3,
      ...ch4,
      ...ch5_weather,
      ...ch6,
      ...ch7,
      ...ch8,
      ...ch9,
      ...ch10,
      ...refs,
    ],
  }],
});

const OUTPUT = "docs/report/SDACS_Technical_Report.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT, buffer);
  console.log(`Report generated: ${OUTPUT} (${(buffer.length / 1024).toFixed(0)} KB)`);
});
