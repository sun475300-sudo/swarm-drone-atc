/**
 * SDACS Capstone Design Presentation Generator
 * 군집드론 공역통제 자동화 시스템 — 캡스톤 디자인 발표 PPTX
 *
 * Usage: node scripts/generate_pptx.js
 * Output: docs/SDACS_Capstone_Presentation.pptx
 */

const pptxgen = require("pptxgenjs");
const path = require("path");

// ── Color Palette: Midnight Aviation ──────────────────────────────────
const C = {
  navy:      "0A1628",
  darkNavy:  "060F1D",
  midNavy:   "122040",
  blue:      "1B6CA8",
  cyan:      "00B4D8",
  teal:      "0891B2",
  mint:      "06D6A0",
  gold:      "FFB703",
  orange:    "FB8500",
  white:     "FFFFFF",
  offWhite:  "E8EDF5",
  lightGray: "94A3B8",
  midGray:   "64748B",
  red:       "EF4444",
  green:     "22C55E",
};

// ── Helpers ───────────────────────────────────────────────────────────
const makeShadow = () => ({
  type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.25,
});

function addFooter(slide, num, total) {
  slide.addText(`${num} / ${total}`, {
    x: 8.8, y: 5.2, w: 1, h: 0.3,
    fontSize: 9, color: C.midGray, align: "right",
  });
  slide.addText("SDACS — Mokpo National Univ.", {
    x: 0.3, y: 5.2, w: 3, h: 0.3,
    fontSize: 9, color: C.midGray, align: "left",
  });
}

function darkBg(slide) {
  slide.background = { color: C.navy };
}

function lightBg(slide) {
  slide.background = { color: C.offWhite };
}

function sectionHeader(slide, title, subtitle) {
  slide.background = { color: C.darkNavy };
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 2.0, w: 10, h: 1.8,
    fill: { color: C.midNavy, transparency: 40 },
  });
  slide.addText(title, {
    x: 0.8, y: 2.1, w: 8.4, h: 0.9,
    fontSize: 38, fontFace: "Arial Black", color: C.cyan,
    bold: true, margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.8, y: 3.0, w: 8.4, h: 0.6,
      fontSize: 16, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  }
}

// card helper for dark slides
function addCard(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: opts.fill || C.midNavy },
    shadow: makeShadow(),
  });
  if (opts.accent) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.06, h,
      fill: { color: opts.accent },
    });
  }
}

// ── Presentation Init ─────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Sunwoo Jang";
pres.title = "SDACS — Swarm Drone Airspace Control System";

const TOTAL_SLIDES = 14;
let sn = 0;

// =====================================================================
// SLIDE 1: Title
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  s.background = { color: C.darkNavy };

  // decorative top bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.cyan },
  });

  // accent shape
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 1.2, w: 0.08, h: 2.8, fill: { color: C.cyan },
  });

  s.addText("SDACS", {
    x: 1.0, y: 1.2, w: 8, h: 1.0,
    fontSize: 52, fontFace: "Arial Black", color: C.white,
    bold: true, margin: 0,
  });

  s.addText("Swarm Drone Airspace Control System", {
    x: 1.0, y: 2.1, w: 8, h: 0.6,
    fontSize: 22, fontFace: "Calibri", color: C.cyan, margin: 0,
  });

  s.addText("군집드론 공역통제 자동화 시스템", {
    x: 1.0, y: 2.7, w: 8, h: 0.5,
    fontSize: 18, fontFace: "Calibri", color: C.lightGray, margin: 0,
  });

  // bottom info bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 4.4, w: 10, h: 1.2, fill: { color: C.midNavy },
  });

  s.addText([
    { text: "장선우 (Sunwoo Jang)", options: { bold: true, color: C.white, fontSize: 16, breakLine: true } },
    { text: "국립 목포대학교 드론기계공학과  |  캡스톤 디자인 2026", options: { color: C.lightGray, fontSize: 13 } },
  ], { x: 1.0, y: 4.55, w: 8, h: 0.9, margin: 0 });

  s.addText("Phase 660  |  590+ Modules  |  2,620+ Tests  |  50+ Languages", {
    x: 1.0, y: 5.15, w: 8, h: 0.3,
    fontSize: 10, color: C.midGray, margin: 0,
  });
}

// =====================================================================
// SLIDE 2: Problem Statement
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("해결하려는 문제", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  s.addText("국내 등록 드론 90만대 돌파, 연간 30% 증가 — 저고도 공역 충돌 위험 급증", {
    x: 0.6, y: 1.0, w: 8.8, h: 0.4,
    fontSize: 13, fontFace: "Calibri", color: C.gold, italic: true, margin: 0,
  });

  // problem cards
  const problems = [
    { title: "고정형 레이더", desc: "설치 비용 수억원\n소형 드론 탐지 불가\n6개월 설치 기간", color: C.red },
    { title: "중앙 집중식 관제", desc: "단일 장애점(SPOF)\n실시간성 부족\nK-UTM 한계", color: C.orange },
    { title: "수동 관제", desc: "평균 5분 지연\n24/7 인력 비용 과다\n확장 불가", color: C.gold },
  ];

  problems.forEach((p, i) => {
    const cx = 0.6 + i * 3.1;
    addCard(s, cx, 1.6, 2.8, 2.6, { accent: p.color });
    s.addText(p.title, {
      x: cx + 0.25, y: 1.75, w: 2.3, h: 0.5,
      fontSize: 18, fontFace: "Arial Black", color: p.color, bold: true, margin: 0,
    });
    s.addText(p.desc, {
      x: cx + 0.25, y: 2.3, w: 2.3, h: 1.6,
      fontSize: 13, fontFace: "Calibri", color: C.offWhite, margin: 0,
    });
  });

  // arrow + solution teaser
  s.addText("SDACS의 해답", {
    x: 0.6, y: 4.5, w: 3, h: 0.5,
    fontSize: 18, fontFace: "Arial Black", color: C.mint, bold: true, margin: 0,
  });
  s.addText("드론 자체를 이동형 레이더로 활용 → 30분 긴급배치, 완전자동 충돌회피, 무한 확장", {
    x: 3.5, y: 4.5, w: 6, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.offWhite, margin: 0,
  });
}

// =====================================================================
// SLIDE 3: Our Approach
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("SDACS 접근 방식", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  const approaches = [
    { num: "01", title: "레이더를 드론으로 대체", desc: "고정 인프라 없이 30분 내 긴급 배치\n군집 드론이 이동형 가상 레이더 돔 형성", accent: C.cyan },
    { num: "02", title: "탐지 → 판단 → 회피 자동화", desc: "90초 전 선제 충돌 예측 (CPA)\n6종 자동 어드바이저리 발행 (<1초)", accent: C.mint },
    { num: "03", title: "분산 아키텍처로 무한 확장", desc: "드론 추가만으로 관제 반경 선형 확장\n단일 장애점(SPOF) 완전 제거", accent: C.gold },
  ];

  approaches.forEach((a, i) => {
    const cy = 1.2 + i * 1.4;
    addCard(s, 0.6, cy, 8.8, 1.2, { accent: a.accent });
    s.addText(a.num, {
      x: 0.85, y: cy + 0.15, w: 0.7, h: 0.7,
      fontSize: 28, fontFace: "Arial Black", color: a.accent, bold: true, margin: 0, align: "center",
    });
    s.addText(a.title, {
      x: 1.7, y: cy + 0.1, w: 4, h: 0.45,
      fontSize: 18, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
    });
    s.addText(a.desc, {
      x: 1.7, y: cy + 0.55, w: 7.5, h: 0.55,
      fontSize: 12, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  });
}

// =====================================================================
// SLIDE 4: System Architecture (4 Layers)
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("시스템 아키텍처 (4계층)", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  const layers = [
    { name: "Layer 4: User Interface", desc: "CLI (main.py) + Dash 3D Visualizer", color: C.teal, y: 1.15 },
    { name: "Layer 3: Simulation Engine", desc: "SwarmSimulator + WindModel + Monte Carlo", color: C.cyan, y: 2.2 },
    { name: "Layer 2: Control System", desc: "AirspaceController 1Hz + Priority Queue + Advisory Gen", color: C.mint, y: 3.25 },
    { name: "Layer 1: Drone Agents", desc: "_DroneAgent 10Hz SimPy process × N drones", color: C.gold, y: 4.3 },
  ];

  layers.forEach((l) => {
    // layer bar
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: l.y, w: 8.8, h: 0.85,
      fill: { color: C.midNavy },
      shadow: makeShadow(),
    });
    // left accent
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: l.y, w: 0.06, h: 0.85, fill: { color: l.color },
    });
    s.addText(l.name, {
      x: 0.9, y: l.y + 0.05, w: 4, h: 0.4,
      fontSize: 16, fontFace: "Arial Black", color: l.color, bold: true, margin: 0,
    });
    s.addText(l.desc, {
      x: 0.9, y: l.y + 0.43, w: 8, h: 0.35,
      fontSize: 12, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  });

  // arrows between layers
  for (let i = 0; i < 3; i++) {
    const ay = 2.0 + i * 1.05;
    s.addText("\u25BC", {
      x: 4.7, y: ay, w: 0.6, h: 0.3,
      fontSize: 14, color: C.midGray, align: "center", margin: 0,
    });
  }
}

// =====================================================================
// SLIDE 5: Data Flow
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("데이터 흐름 아키텍처", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  // Flow steps
  const flows = [
    { step: "10Hz", title: "Drone Agent", items: "위치/속도/배터리 물리 갱신\nWindModel 풍 벡터 적용\nAPF 합력 계산 (EVADING 시)", color: C.gold },
    { step: "1Hz", title: "Airspace Controller", items: "O(N\u00B2) CPA 스캔 (90초 예측)\nVoronoi 분할 갱신 (10초)\nAdvisory 자동 생성", color: C.cyan },
    { step: "Event", title: "Communication Bus", items: "20\u00B15ms 지연 모델링\n범위 기반 이웃 탐색\n패킷 손실률 시뮬레이션", color: C.mint },
    { step: "End", title: "Analytics & KPI", items: "충돌해결률, 경로효율\n어드바이저리 지연시간\n에너지 소비량 계산", color: C.teal },
  ];

  flows.forEach((f, i) => {
    const cx = 0.4 + i * 2.4;
    addCard(s, cx, 1.2, 2.2, 3.4, { accent: f.color });

    s.addText(f.step, {
      x: cx + 0.2, y: 1.35, w: 1.8, h: 0.4,
      fontSize: 20, fontFace: "Arial Black", color: f.color, bold: true, margin: 0,
    });
    s.addText(f.title, {
      x: cx + 0.2, y: 1.75, w: 1.8, h: 0.4,
      fontSize: 14, fontFace: "Calibri", color: C.white, bold: true, margin: 0,
    });
    s.addShape(pres.shapes.LINE, {
      x: cx + 0.2, y: 2.2, w: 1.8, h: 0,
      line: { color: f.color, width: 1, transparency: 60 },
    });
    s.addText(f.items, {
      x: cx + 0.2, y: 2.35, w: 1.8, h: 2.0,
      fontSize: 11, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  });

  // arrows
  for (let i = 0; i < 3; i++) {
    s.addText("\u25B6", {
      x: 2.5 + i * 2.4, y: 2.6, w: 0.4, h: 0.4,
      fontSize: 16, color: C.midGray, align: "center", margin: 0,
    });
  }
}

// =====================================================================
// SLIDE 6: Core Algorithms — Detection
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("핵심 알고리즘 (1) — 충돌 탐지", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  const algos = [
    { name: "CPA", full: "Closest Point of Approach", desc: "O(N\u00B2) 쌍별 스캔\n90초 선제 예측\n분리기준 동적 조정 (풍속 연동)", complexity: "O(N\u00B2)", accent: C.cyan },
    { name: "Voronoi", full: "Tessellation", desc: "10초 주기 동적 갱신\n밀도 기반 셀 분리\nSutherland-Hodgman 클리핑", complexity: "O(N log N)", accent: C.mint },
    { name: "SpatialHash", full: "3D Uniform Grid", desc: "50m 셀 크기 균일 격자\nO(N) → O(N\u00B7k) 최적화\n충돌/근접/위협 3단계", complexity: "O(N\u00B7k)", accent: C.gold },
    { name: "Geofence", full: "Boundary Monitor", desc: "공역 경계 90% 이탈 감지\n자동 RTL(Return to Launch)\n침입 드론 실시간 탐지", complexity: "O(N)", accent: C.teal },
  ];

  algos.forEach((a, i) => {
    const cy = 1.15 + i * 1.05;
    addCard(s, 0.6, cy, 8.8, 0.9, { accent: a.accent });
    s.addText(a.name, {
      x: 0.85, y: cy + 0.08, w: 1.8, h: 0.4,
      fontSize: 18, fontFace: "Arial Black", color: a.accent, bold: true, margin: 0,
    });
    s.addText(a.full, {
      x: 0.85, y: cy + 0.48, w: 1.8, h: 0.3,
      fontSize: 10, fontFace: "Calibri", color: C.midGray, margin: 0,
    });
    s.addText(a.desc, {
      x: 2.9, y: cy + 0.08, w: 4.5, h: 0.75,
      fontSize: 11, fontFace: "Calibri", color: C.offWhite, margin: 0,
    });
    s.addText(a.complexity, {
      x: 7.8, y: cy + 0.15, w: 1.4, h: 0.5,
      fontSize: 16, fontFace: "Consolas", color: a.accent, bold: true, align: "center", margin: 0,
    });
  });
}

// =====================================================================
// SLIDE 7: Core Algorithms — Resolution
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("핵심 알고리즘 (2) — 충돌 해결", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  // APF section
  addCard(s, 0.6, 1.1, 4.2, 2.5, { accent: C.cyan });
  s.addText("APF Engine", {
    x: 0.85, y: 1.2, w: 3.8, h: 0.4,
    fontSize: 18, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });
  s.addText("Artificial Potential Field", {
    x: 0.85, y: 1.6, w: 3.8, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: C.midGray, margin: 0,
  });
  s.addText([
    { text: "Normal: ", options: { bold: true, color: C.offWhite, fontSize: 11, breakLine: false } },
    { text: "k_rep=2.5, d0=50m, max=10m/s\u00B2", options: { color: C.lightGray, fontSize: 11, breakLine: true } },
    { text: "Windy:  ", options: { bold: true, color: C.gold, fontSize: 11, breakLine: false } },
    { text: "k_rep=6.5, d0=80m, max=22m/s\u00B2", options: { color: C.lightGray, fontSize: 11, breakLine: true } },
    { text: "6~12 m/s \uAD6C\uAC04: \uC120\uD615 \uBCF4\uAC04(lerp) \uC804\uD658", options: { color: C.lightGray, fontSize: 11, breakLine: true } },
    { text: "CFIT \uBC29\uC9C0: z<5m \uC9C0\uBA74 \uCC99\uB825\uC7A5 \uD65C\uC131", options: { color: C.lightGray, fontSize: 11 } },
  ], { x: 0.85, y: 2.0, w: 3.8, h: 1.4, margin: 0 });

  // CBS section
  addCard(s, 5.2, 1.1, 4.2, 2.5, { accent: C.mint });
  s.addText("CBS Planner", {
    x: 5.45, y: 1.2, w: 3.8, h: 0.4,
    fontSize: 18, fontFace: "Arial Black", color: C.mint, bold: true, margin: 0,
  });
  s.addText("Conflict-Based Search", {
    x: 5.45, y: 1.6, w: 3.8, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: C.midGray, margin: 0,
  });
  s.addText([
    { text: "High-level: \uCDA9\uB3CC \uD2B8\uB9AC \uD0D0\uC0C9 + \uC81C\uC57D \uBD84\uAE30", options: { color: C.lightGray, fontSize: 11, breakLine: true } },
    { text: "Low-level: \uC2DC\uACF5\uAC04 A* (7\uBC29\uD5A5 + \uB300\uAE30)", options: { color: C.lightGray, fontSize: 11, breakLine: true } },
    { text: "Grid: 50m, Max 100K expansions", options: { color: C.lightGray, fontSize: 11, breakLine: true } },
    { text: "Wall-clock timeout: 5s(A*) / 10s(CBS)", options: { color: C.lightGray, fontSize: 11 } },
  ], { x: 5.45, y: 2.0, w: 3.8, h: 1.4, margin: 0 });

  // Resolution Advisory
  addCard(s, 0.6, 3.85, 8.8, 1.2, { accent: C.gold });
  s.addText("Resolution Advisory — 6\uC885 \uD68C\uD53C \uBA85\uB839 \uC790\uB3D9 \uBD84\uB958", {
    x: 0.85, y: 3.95, w: 8, h: 0.4,
    fontSize: 16, fontFace: "Arial Black", color: C.gold, bold: true, margin: 0,
  });
  s.addText("CLIMB  |  DESCEND  |  TURN_LEFT  |  TURN_RIGHT  |  EVADE_APF  |  HOLD", {
    x: 0.85, y: 4.35, w: 8, h: 0.3,
    fontSize: 14, fontFace: "Consolas", color: C.cyan, margin: 0,
  });
  s.addText("\uAE30\uD558\uD559\uC801 \uBD84\uB958: \uC218\uC9C1 \uBD84\uB9AC \uC6B0\uC120 \u2192 360\u00B0 \uBC29\uC704\uAC01 \uD310\uC815 \u2192 \uD3D0\uC1C4\uC18D\uB3C4 \uBE44\uB840 \uC9C0\uC18D\uC2DC\uAC04", {
    x: 0.85, y: 4.65, w: 8, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: C.lightGray, margin: 0,
  });
}

// =====================================================================
// SLIDE 8: Key Results — Big Numbers
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("\uD575\uC2EC \uC131\uACFC", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  const metrics = [
    { value: "99.9%", label: "\uCDA9\uB3CC \uD574\uACB0\uB960", sub: "500\uB300 \uBA54\uAC00\uC2A4\uC6DC\n58,038 \uCDA9\uB3CC\uC704\uD611 \u2192 19\uAC74", accent: C.mint },
    { value: "90s", label: "\uC120\uC81C \uC608\uCE21", sub: "CPA \uAE30\uBC18\n1Hz \uC5F0\uC18D \uC2A4\uCE94", accent: C.cyan },
    { value: "<1s", label: "\uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC \uC9C0\uC5F0", sub: "6\uC885 \uC790\uB3D9 \uD68C\uD53C\nP99 < 0.8\uCD08", accent: C.gold },
    { value: "38.4K", label: "Monte Carlo \uAC80\uC99D", sub: "384\uC124\uC815 \u00D7 100\uC2DC\uB4DC\n\uD1B5\uACC4\uC801 \uC2E0\uB8B0\uC131 \uD655\uBCF4", accent: C.teal },
  ];

  metrics.forEach((m, i) => {
    const cx = 0.4 + i * 2.4;
    addCard(s, cx, 1.1, 2.2, 3.0);

    s.addText(m.value, {
      x: cx + 0.1, y: 1.25, w: 2.0, h: 0.8,
      fontSize: 40, fontFace: "Arial Black", color: m.accent, bold: true, align: "center", margin: 0,
    });
    s.addText(m.label, {
      x: cx + 0.1, y: 2.1, w: 2.0, h: 0.4,
      fontSize: 14, fontFace: "Calibri", color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addShape(pres.shapes.LINE, {
      x: cx + 0.5, y: 2.55, w: 1.2, h: 0,
      line: { color: m.accent, width: 2 },
    });
    s.addText(m.sub, {
      x: cx + 0.1, y: 2.7, w: 2.0, h: 1.0,
      fontSize: 11, fontFace: "Calibri", color: C.lightGray, align: "center", margin: 0,
    });
  });

  // bottom row
  const bottomMetrics = [
    { value: "500+", label: "\uB3D9\uC2DC \uC6B4\uC6A9 \uB4DC\uB860", accent: C.cyan },
    { value: "30\uBD84", label: "\uAE34\uAE09 \uBC30\uCE58 \uC2DC\uAC04", accent: C.mint },
    { value: "2,620+", label: "\uC790\uB3D9\uD654 \uD14C\uC2A4\uD2B8", accent: C.gold },
    { value: "42", label: "\uAC80\uC99D \uC2DC\uB098\uB9AC\uC624", accent: C.teal },
  ];

  bottomMetrics.forEach((m, i) => {
    const cx = 0.4 + i * 2.4;
    s.addText(m.value, {
      x: cx, y: 4.3, w: 1.1, h: 0.5,
      fontSize: 20, fontFace: "Arial Black", color: m.accent, bold: true, margin: 0,
    });
    s.addText(m.label, {
      x: cx + 1.1, y: 4.3, w: 1.3, h: 0.5,
      fontSize: 11, fontFace: "Calibri", color: C.lightGray, margin: 0, valign: "middle",
    });
  });
}

// =====================================================================
// SLIDE 9: Simulation Scenarios
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("시나리오 검증 체계 (7대 시나리오)", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  // table header
  const headerRow = [
    { text: "#", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11, align: "center" } },
    { text: "Scenario", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11 } },
    { text: "Drones", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11, align: "center" } },
    { text: "Duration", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11, align: "center" } },
    { text: "Key Test", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11 } },
  ];

  const scenarios = [
    ["1", "Normal Operation", "20", "60s", "\uAE30\uBCF8 \uCDA9\uB3CC \uD574\uACB0\uB960"],
    ["2", "High Density", "50", "60s", "\uBC00\uC9D1 \uD658\uACBD \uC131\uB2A5"],
    ["3", "Weather Disturbance", "20", "60s", "\uD48D\uC18D 15m/s \uAC15\uD48D \uB300\uC751"],
    ["4", "Communication Loss", "20", "60s", "\uD1B5\uC2E0 \uB450\uC808 \uC2DC \uC790\uC728 \uD68C\uD53C"],
    ["5", "Intruder Response", "20", "60s", "\uBBF8\uB4F1\uB85D \uB4DC\uB860 \uD0D0\uC9C0/\uB300\uC751"],
    ["6", "Emergency Landing", "20", "60s", "\uBAA8\uD130/\uBC30\uD130\uB9AC/GPS \uACE0\uC7A5"],
    ["7", "Mass Delivery", "100", "120s", "\uB300\uADDC\uBAA8 \uBC30\uC1A1 \uB3D9\uC2DC \uC6B4\uC6A9"],
  ];

  const rowOpts = { fontSize: 11, color: C.offWhite, align: "left" };
  const tableData = [headerRow];
  scenarios.forEach((row) => {
    tableData.push(row.map((cell, ci) => ({
      text: cell,
      options: { ...rowOpts, align: ci === 0 || ci === 2 || ci === 3 ? "center" : "left" },
    })));
  });

  s.addTable(tableData, {
    x: 0.6, y: 1.15, w: 8.8, h: 3.5,
    colW: [0.5, 2.2, 1.0, 1.0, 4.1],
    border: { pt: 0.5, color: C.midNavy },
    fill: { color: C.midNavy },
    rowH: [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4],
    autoPage: false,
  });
}

// =====================================================================
// SLIDE 10: Monte Carlo Validation
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("Monte Carlo SLA \uAC80\uC99D", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  // Left: config
  addCard(s, 0.6, 1.1, 4.2, 1.6, { accent: C.cyan });
  s.addText("Quick Mode", {
    x: 0.85, y: 1.2, w: 1.8, h: 0.35,
    fontSize: 16, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });
  s.addText("32 configs \u00D7 30 seeds = 960 runs (~4\uBD84)", {
    x: 0.85, y: 1.55, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Calibri", color: C.lightGray, margin: 0,
  });

  addCard(s, 5.2, 1.1, 4.2, 1.6, { accent: C.gold });
  s.addText("Full Mode", {
    x: 5.45, y: 1.2, w: 1.8, h: 0.35,
    fontSize: 16, fontFace: "Arial Black", color: C.gold, bold: true, margin: 0,
  });
  s.addText("384 configs \u00D7 100 seeds = 38,400 runs (~3.3h)", {
    x: 5.45, y: 1.55, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Calibri", color: C.lightGray, margin: 0,
  });

  // SLA table
  s.addText("SLA \uD569\uACA9 \uAE30\uC900", {
    x: 0.6, y: 2.9, w: 3, h: 0.4,
    fontSize: 16, fontFace: "Arial Black", color: C.mint, bold: true, margin: 0,
  });

  const slaHeader = [
    { text: "Metric", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11 } },
    { text: "Threshold", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11, align: "center" } },
    { text: "Type", options: { fill: { color: C.teal }, color: C.white, bold: true, fontSize: 11, align: "center" } },
  ];

  const slaRows = [
    ["\uCDA9\uB3CC\uB960", "0\uAC74/1,000h", "Hard"],
    ["\uCDA9\uB3CC \uD574\uACB0\uB960", "\u226599.5%", "Hard"],
    ["\uC751\uB2F5 P99", "\u226410.0\uCD08", "Hard"],
    ["\uCE68\uC785 \uD0D0\uC9C0 P90", "\u22645.0\uCD08", "Hard"],
    ["\uACBD\uB85C \uD6A8\uC728", "\u22641.15", "Soft"],
  ];

  const slaData = [slaHeader, ...slaRows.map(r => r.map((c, i) => ({
    text: c,
    options: { fontSize: 11, color: i === 2 && c === "Hard" ? C.red : C.offWhite, align: i > 0 ? "center" : "left" },
  })))];

  s.addTable(slaData, {
    x: 0.6, y: 3.3, w: 8.8, colW: [3.5, 2.65, 2.65],
    border: { pt: 0.5, color: C.midNavy }, fill: { color: C.midNavy },
    autoPage: false,
  });
}

// =====================================================================
// SLIDE 11: Drone Profiles
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("\uB4DC\uB860 \uD504\uB85C\uD30C\uC77C (5\uC885)", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  const profiles = [
    { name: "COMMERCIAL\nDELIVERY", speed: "15 m/s", battery: "80Wh", endurance: "30min", priority: "2", accent: C.cyan },
    { name: "SURVEILLANCE", speed: "20 m/s", battery: "100Wh", endurance: "45min", priority: "2", accent: C.teal },
    { name: "EMERGENCY", speed: "25 m/s", battery: "60Wh", endurance: "20min", priority: "1", accent: C.red },
    { name: "RECREATIONAL", speed: "10 m/s", battery: "30Wh", endurance: "15min", priority: "3", accent: C.mint },
    { name: "ROGUE\n(\uBBF8\uB4F1\uB85D)", speed: "15 m/s", battery: "50Wh", endurance: "25min", priority: "99", accent: C.gold },
  ];

  profiles.forEach((p, i) => {
    const cx = 0.3 + i * 1.9;
    addCard(s, cx, 1.1, 1.75, 3.8, { accent: p.accent });
    s.addText(p.name, {
      x: cx + 0.15, y: 1.25, w: 1.5, h: 0.7,
      fontSize: 12, fontFace: "Arial Black", color: p.accent, bold: true, align: "center", margin: 0,
    });

    const stats = [
      { label: "Max Speed", val: p.speed },
      { label: "Battery", val: p.battery },
      { label: "Endurance", val: p.endurance },
      { label: "Priority", val: p.priority },
    ];

    stats.forEach((st, j) => {
      const sy = 2.15 + j * 0.65;
      s.addText(st.label, {
        x: cx + 0.15, y: sy, w: 1.5, h: 0.25,
        fontSize: 9, fontFace: "Calibri", color: C.midGray, align: "center", margin: 0,
      });
      s.addText(st.val, {
        x: cx + 0.15, y: sy + 0.22, w: 1.5, h: 0.3,
        fontSize: 14, fontFace: "Calibri", color: C.white, bold: true, align: "center", margin: 0,
      });
    });
  });
}

// =====================================================================
// SLIDE 12: Performance Chart
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("\uC131\uB2A5 \uBD84\uC11D", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 30, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  // Throughput chart
  s.addChart(pres.charts.BAR, [{
    name: "Tick Time (ms)",
    labels: ["20", "50", "100", "200", "500"],
    values: [0.8, 4.2, 16.1, 63.5, 398.0],
  }], {
    x: 0.5, y: 1.0, w: 4.5, h: 3.2,
    barDir: "col",
    showTitle: true, title: "Tick Time vs Drone Count",
    titleColor: C.offWhite, titleFontSize: 12,
    chartColors: [C.cyan],
    chartArea: { fill: { color: C.midNavy }, roundedCorners: true },
    catAxisLabelColor: C.lightGray, catAxisLabelFontSize: 10,
    valAxisLabelColor: C.lightGray, valAxisLabelFontSize: 9,
    valGridLine: { color: "1E3050", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true, dataLabelColor: C.offWhite, dataLabelFontSize: 9,
    showLegend: false,
  });

  // Real-time ratio chart
  s.addChart(pres.charts.BAR, [{
    name: "Real-time Ratio",
    labels: ["20", "50", "100", "200", "500"],
    values: [1250, 238, 62, 16, 2.5],
  }], {
    x: 5.2, y: 1.0, w: 4.5, h: 3.2,
    barDir: "col",
    showTitle: true, title: "Real-time Ratio (higher = better)",
    titleColor: C.offWhite, titleFontSize: 12,
    chartColors: [C.mint],
    chartArea: { fill: { color: C.midNavy }, roundedCorners: true },
    catAxisLabelColor: C.lightGray, catAxisLabelFontSize: 10,
    valAxisLabelColor: C.lightGray, valAxisLabelFontSize: 9,
    valGridLine: { color: "1E3050", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true, dataLabelColor: C.offWhite, dataLabelFontSize: 9,
    showLegend: false,
  });

  s.addText("\uCDA9\uB3CC \uD574\uACB0\uB960 \uACF5\uC2DD:  CR = 1 \u2212 collisions / (conflicts + collisions)", {
    x: 0.6, y: 4.4, w: 8.8, h: 0.4,
    fontSize: 13, fontFace: "Consolas", color: C.gold, margin: 0,
  });
  s.addText("500\uB300 60\uCD08: 58,038 conflicts \u2192 19 collisions \u2192 CR = 99.97%", {
    x: 0.6, y: 4.8, w: 8.8, h: 0.3,
    fontSize: 12, fontFace: "Calibri", color: C.lightGray, margin: 0,
  });
}

// =====================================================================
// SLIDE 13: Multi-Language Architecture
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  darkBg(s);
  addFooter(s, sn, TOTAL_SLIDES);

  s.addText("\uB2E4\uC911 \uC5B8\uC5B4 \uC544\uD0A4\uD14D\uCC98 (50+ Languages)", {
    x: 0.6, y: 0.3, w: 8, h: 0.7,
    fontSize: 26, fontFace: "Arial Black", color: C.cyan, bold: true, margin: 0,
  });

  // Pie chart
  s.addChart(pres.charts.PIE, [{
    name: "Modules",
    labels: ["Python (580)", "Zig (15)", "Rust (15)", "Go (14)", "C++ (14)", "Fortran (9)", "Others (100+)"],
    values: [580, 15, 15, 14, 14, 9, 100],
  }], {
    x: 0.3, y: 1.0, w: 4.5, h: 3.8,
    showPercent: true,
    showLegend: true, legendPos: "b", legendFontSize: 9, legendColor: C.lightGray,
    chartColors: [C.cyan, C.gold, C.orange, C.mint, C.teal, "8B5CF6", C.midGray],
    dataLabelColor: C.white, dataLabelFontSize: 9,
  });

  // Right side: key language roles
  const langs = [
    { lang: "Python", role: "Core: simulation, ML/AI, analytics", count: "580+", accent: C.cyan },
    { lang: "Rust", role: "Safety-critical: satellite, verifier", count: "15", accent: C.orange },
    { lang: "Go", role: "Concurrent: edge AI, monitor", count: "14", accent: C.mint },
    { lang: "C++", role: "Performance: SLAM, physics", count: "14", accent: C.teal },
    { lang: "Fortran", role: "Numerical: wind FDM, CFD", count: "9", accent: "8B5CF6" },
    { lang: "VHDL/Ada", role: "Hardware sim, fault tolerance", count: "14", accent: C.gold },
  ];

  langs.forEach((l, i) => {
    const cy = 1.1 + i * 0.65;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.2, y: cy, w: 0.06, h: 0.5, fill: { color: l.accent },
    });
    s.addText(l.lang, {
      x: 5.45, y: cy, w: 1.5, h: 0.25,
      fontSize: 13, fontFace: "Arial Black", color: l.accent, bold: true, margin: 0,
    });
    s.addText(l.role, {
      x: 5.45, y: cy + 0.25, w: 4, h: 0.25,
      fontSize: 10, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
    s.addText(l.count, {
      x: 8.8, y: cy, w: 0.7, h: 0.5,
      fontSize: 13, fontFace: "Consolas", color: C.offWhite, bold: true, align: "right", margin: 0,
    });
  });
}

// =====================================================================
// SLIDE 14: Thank You / Q&A
// =====================================================================
{
  sn++;
  const s = pres.addSlide();
  s.background = { color: C.darkNavy };

  // decorative bottom bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.cyan },
  });

  // accent
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 1.4, w: 0.08, h: 2.2, fill: { color: C.cyan },
  });

  s.addText("Thank You", {
    x: 1.0, y: 1.4, w: 8, h: 0.9,
    fontSize: 48, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  s.addText("\uAC10\uC0AC\uD569\uB2C8\uB2E4", {
    x: 1.0, y: 2.3, w: 8, h: 0.6,
    fontSize: 24, fontFace: "Calibri", color: C.cyan, margin: 0,
  });

  s.addText("Q & A", {
    x: 1.0, y: 3.1, w: 8, h: 0.5,
    fontSize: 20, fontFace: "Arial Black", color: C.gold, bold: true, margin: 0,
  });

  // info
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 4.0, w: 10, h: 1.3, fill: { color: C.midNavy },
  });

  s.addText([
    { text: "\uC7A5\uC120\uC6B0 (Sunwoo Jang)", options: { bold: true, color: C.white, fontSize: 15, breakLine: true } },
    { text: "\uAD6D\uB9BD \uBAA9\uD3EC\uB300\uD559\uAD50 \uB4DC\uB860\uAE30\uACC4\uACF5\uD559\uACFC  |  \uCEA1\uC2A4\uD1A4 \uB514\uC790\uC778 2026", options: { color: C.lightGray, fontSize: 12, breakLine: true } },
    { text: "github.com/sun475300-sudo/swarm-drone-atc", options: { color: C.cyan, fontSize: 12 } },
  ], { x: 1.0, y: 4.15, w: 8, h: 0.9, margin: 0 });
}

// ── Save ──────────────────────────────────────────────────────────────
const outDir = path.resolve(__dirname, "..", "docs");
const outPath = path.join(outDir, "SDACS_Capstone_Presentation.pptx");

pres.writeFile({ fileName: outPath }).then(() => {
  console.log(`✅ Presentation saved: ${outPath}`);
  console.log(`   ${TOTAL_SLIDES} slides generated`);
}).catch(err => {
  console.error("❌ Error:", err);
  process.exit(1);
});
