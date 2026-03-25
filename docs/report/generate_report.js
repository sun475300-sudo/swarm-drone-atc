const fs = require("fs");
const path = require("path");
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

function cell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    margins: { top: 40, bottom: 40, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, font: FONT, size: 20 })] })],
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
    children: [new TextRun({ text, font: FONT, bold: true, size: 36 })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, font: FONT, bold: true, size: 28 })] });
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

// ── Bullet config ──
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

// ── Title Page ──
const titlePage = [
  blank(), blank(), blank(), blank(), blank(), blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
    children: [new TextRun({ text: "\uD83D\uDE81", size: 80 })] }),
  blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "\uAD70\uC9D1\uB4DC\uB860 \uACF5\uC5ED\uD1B5\uC81C \uC790\uB3D9\uD654 \uC2DC\uC2A4\uD15C (SDACS)", font: FONT, bold: true, size: 48, color: DARK_BLUE })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
    children: [new TextRun({ text: "\uAE30\uC220 \uBCF4\uACE0\uC11C", font: FONT, bold: true, size: 36, color: DARK_BLUE })] }),
  blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "Swarm Drone Airspace Control System", font: FONT_EN, size: 24, color: "666666", italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "Design, Implementation & Performance Analysis", font: FONT_EN, size: 24, color: "666666", italics: true })] }),
  blank(), blank(), blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "\uC7A5\uC120\uC6B0", font: FONT, bold: true, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "\uAD6D\uB9BD\uBAA9\uD3EC\uB300\uD559\uAD50 \uB4DC\uB860\uAE30\uACC4\uACF5\uD559\uACFC", font: FONT, size: 22, color: "444444" })] }),
  blank(),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "2026\uB144 3\uC6D4 25\uC77C", font: FONT, size: 22, color: "888888" })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── TOC ──
const tocSection = [
  h1("\uBAA9\uCC28"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 1. 서론 ──
const ch1 = [
  h1("1. \uC11C\uB860"),
  h2("1.1 \uC5F0\uAD6C \uBC30\uACBD"),
  p("\uB3C4\uC2EC \uC800\uACE0\uB3C4 \uACF5\uC5ED(Urban Air Mobility)\uC5D0\uC11C \uAD70\uC9D1\uB4DC\uB860 \uC6B4\uC6A9\uC758 \uD3ED\uBC1C\uC801 \uC99D\uAC00\uB85C \uC778\uD574, \uAE30\uC874 \uACE0\uC815\uD615 \uB808\uC774\uB354 \uC778\uD504\uB77C\uB9CC\uC73C\uB85C\uB294 \uC800\uACE0\uB3C4 \uC18C\uD615 \uB4DC\uB860\uC758 \uC2E4\uC2DC\uAC04 \uAC10\uC9C0\uC640 \uD1B5\uC81C\uAC00 \uBD88\uAC00\uB2A5\uD574\uC84C\uB2E4. \uD2B9\uD788 100\uB300 \uC774\uC0C1\uC758 \uB4DC\uB860\uC774 \uB3D9\uC2DC\uC5D0 \uC6B4\uC6A9\uB418\uB294 \uD658\uACBD\uC5D0\uC11C\uB294 \uCDA9\uB3CC \uD68C\uD53C, \uACBD\uB85C \uACC4\uD68D, \uBE44\uC0C1 \uB300\uC751\uC744 \uC790\uB3D9\uD654\uD558\uB294 \uC2DC\uC2A4\uD15C\uC774 \uD544\uC218\uC801\uC774\uB2E4."),
  p("SDACS(Swarm Drone Airspace Control System)\uB294 \uC774\uB3D9\uD615 \uAC00\uC0C1 \uB808\uC774\uB354 \uB3D4 \uAC1C\uB150\uC744 \uD1B5\uD574 \uAD70\uC9D1\uB4DC\uB860 \uACF5\uC5ED\uC744 \uC790\uB3D9\uC73C\uB85C \uD1B5\uC81C\uD558\uB294 \uC2DC\uC2A4\uD15C\uC774\uB2E4. \uBCF8 \uBCF4\uACE0\uC11C\uB294 SDACS\uC758 \uC124\uACC4, \uAD6C\uD604, \uC131\uB2A5 \uBD84\uC11D \uACB0\uACFC\uB97C \uC885\uD569\uC801\uC73C\uB85C \uAE30\uC220\uD55C\uB2E4."),
  blank(),
  h2("1.2 \uC2DC\uC2A4\uD15C \uBAA9\uD45C \uBC0F SLA \uAE30\uC900"),
  p("\uBCF8 \uC2DC\uC2A4\uD15C\uC740 \uB2E4\uC74C\uC758 SLA(Service Level Agreement) \uAE30\uC900\uC744 \uCDA9\uC871\uD558\uB294 \uAC83\uC744 \uBAA9\uD45C\uB85C \uD55C\uB2E4:"),
  makeTable(
    ["KPI", "\uBAA9\uD45C\uAC12", "\uBE44\uACE0"],
    [
      ["\uCDA9\uB3CC\uB960", "0\uAC74/1,000h", "Hard requirement"],
      ["Near-miss", "\u22640.1\uAC74/100h", "10m \uC774\uB0B4 \uC811\uADFC"],
      ["\uCDA9\uB3CC \uD574\uACB0\uB960", "\u226599.5%", "\uC804\uCCB4 \uC2DC\uB098\uB9AC\uC624"],
      ["\uACBD\uB85C \uD6A8\uC728", "\u22641.15", "actual/planned \uBE44\uC728"],
      ["\uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC P50", "\u22642.0s", "\uC911\uC704 \uC9C0\uC5F0"],
      ["\uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC P99", "\u226410.0s", "\uAF2C\uB9AC \uC9C0\uC5F0"],
      ["\uCE68\uC785 \uD0D0\uC9C0 P90", "\u22645.0s", "ROGUE \uC2DD\uBCC4"],
    ],
    [2400, 2400, 4270]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 2. 시스템 아키텍처 ──
const ch2 = [
  h1("2. \uC2DC\uC2A4\uD15C \uC544\uD0A4\uD14D\uCC98"),
  h2("2.1 4\uACC4\uCE35 \uAD6C\uC870"),
  p("SDACS\uB294 4\uACC4\uCE35 \uC544\uD0A4\uD14D\uCC98\uB85C \uC124\uACC4\uB418\uC5C8\uC73C\uBA70, \uAC01 \uACC4\uCE35\uC740 \uB3C5\uB9BD\uC801\uC73C\uB85C \uB3D9\uC791\uD558\uBA74\uC11C\uB3C4 \uBA54\uC2DC\uC9C0 \uBC84\uC2A4\uB97C \uD1B5\uD574 \uC720\uAE30\uC801\uC73C\uB85C \uC5F0\uB3D9\uD55C\uB2E4."),
  blank(),
  pBold("Layer 4 (\uC0AC\uC6A9\uC790 \uC778\uD130\uD398\uC774\uC2A4): ", "3D Dash \uC2DC\uAC01\uD654(Plotly \uC2E4\uC2DC\uAC04 20Hz), \uD1B5\uD569 CLI, pytest 173\uAC1C \uD14C\uC2A4\uD2B8 \uC2A4\uC704\uD2B8"),
  pBold("Layer 3 (\uC2DC\uBBAC\uB808\uC774\uC158 \uC778\uD504\uB77C): ", "SwarmSimulator(SimPy \uC774\uC0B0 \uC774\uBCA4\uD2B8), \uAE30\uC0C1\uBAA8\uB378(Wind/Gust/Shear), Monte Carlo(joblib \uBCD1\uB82C 38,400\uD68C), 7\uAC1C \uC2DC\uB098\uB9AC\uC624 \uB7EC\uB108"),
  pBold("Layer 2 (\uACF5\uC5ED \uCEE8\uD2B8\uB864\uB7EC): ", "AirspaceController(1Hz \uC81C\uC5B4\uB8E8\uD504), \uCDA9\uB3CC\uC2A4\uCE94(CPA \uC608\uCE21), \uD5C8\uAC00\uCC98\uB9AC(\uC6B0\uC120\uC21C\uC704 \uD050\u00B7A*), Voronoi \uBD84\uD560(10s \uC8FC\uAE30), \uCE68\uC785\uD0D0\uC9C0(ROGUE)"),
  pBold("Layer 1 (\uB4DC\uB860 \uAD70\uC9D1): ", "DroneAgent(Boids 3D), APF \uD68C\uD53C(\uC778\uACF5 \uD3EC\uD150\uC15C \uC7A5), CBS \uD50C\uB798\uB108(\uB2E4\uC911\uC5D0\uC774\uC804\uD2B8 \uACBD\uB85C), \uD154\uB808\uBA54\uD2B8\uB9AC(10Hz), \uBC30\uD130\uB9AC/\uC7A5\uC560 \uBAA8\uB378"),
  blank(),
  h2("2.2 \uD575\uC2EC \uB370\uC774\uD130 \uD750\uB984"),
  p("DroneAgent(10Hz) \u2192 TelemetryMessage(0.5s) \u2192 CommunicationBus \u2192 AirspaceController(1Hz) \u2192 ResolutionAdvisory \u2192 DroneAgent(EVADING)"),
  p("\uAC01 \uB4DC\uB860\uC740 10Hz\uB85C \uC0C1\uD0DC\uB97C \uAC31\uC2E0\uD558\uACE0, 0.5\uCD08 \uC8FC\uAE30\uB85C \uD154\uB808\uBA54\uD2B8\uB9AC \uBA54\uC2DC\uC9C0\uB97C \uD1B5\uC2E0 \uBC84\uC2A4\uB85C \uC804\uC1A1\uD55C\uB2E4. AirspaceController\uB294 1Hz\uB85C \uCDA9\uB3CC \uC2A4\uCE94, \uD5C8\uAC00 \uCC98\uB9AC, Voronoi \uBD84\uD560\uC744 \uC218\uD589\uD558\uBA70, \uCDA9\uB3CC \uC704\uD5D8 \uBC1C\uACAC \uC2DC ResolutionAdvisory\uB97C \uC0DD\uC131\uD558\uC5EC \uD574\uB2F9 \uB4DC\uB860\uC744 EVADING \uC0C1\uD0DC\uB85C \uC804\uD658\uD55C\uB2E4."),
  blank(),
  h2("2.3 \uBAA8\uB4C8 \uBAA9\uB85D\uD45C"),
  makeTable(
    ["\uBAA8\uB4C8\uBA85", "\uD30C\uC77C \uACBD\uB85C", "\uC5ED\uD560", "\uAD6C\uD604"],
    [
      ["SwarmSimulator", "simulation/simulator.py", "SimPy \uC774\uC0B0 \uC774\uBCA4\uD2B8 \uC2DC\uBBAC\uB808\uC774\uD130", "100%"],
      ["AirspaceController", "src/airspace_control/controller/", "\uACF5\uC5ED \uC81C\uC5B4 \uB8E8\uD504", "100%"],
      ["FlightPathPlanner", "src/airspace_control/navigation/", "A* \uACBD\uB85C \uACC4\uD68D", "100%"],
      ["APF Engine", "navigation/apf.py", "\uC778\uACF5 \uD3EC\uD150\uC15C \uC7A5", "100%"],
      ["CBS Planner", "navigation/cbs_planner.py", "\uBA40\uD2F0\uC5D0\uC774\uC804\uD2B8 \uACBD\uB85C", "100%"],
      ["ResolutionAdvisory", "controller/resolution_advisory.py", "\uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC \uC0DD\uC131", "100%"],
      ["Voronoi Partition", "simulation/voronoi_airspace/", "\uB3D9\uC801 \uACF5\uC5ED \uBD84\uD560", "100%"],
      ["WeatherModel", "simulation/weather_model.py", "3\uC885 \uAE30\uC0C1 \uAD50\uB780", "100%"],
      ["Analytics", "simulation/analytics.py", "\uC774\uBCA4\uD2B8\u00B7\uC9C0\uD45C \uC218\uC9D1", "100%"],
      ["3D Dashboard", "visualization/simulator_3d.py", "Dash \uC2E4\uC2DC\uAC04 \uC2DC\uAC01\uD654", "100%"],
      ["Monte Carlo", "simulation/monte_carlo.py", "\uB300\uADDC\uBAA8 SLA \uAC80\uC99D", "100%"],
    ],
    [1800, 2800, 2600, 870]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 3. 핵심 알고리즘 ──
const ch3 = [
  h1("3. \uD575\uC2EC \uC54C\uACE0\uB9AC\uC998"),

  h2("3.1 APF (\uC778\uACF5 \uD3EC\uD150\uC15C \uC7A5) \uCDA9\uB3CC \uD68C\uD53C"),
  p("APF(Artificial Potential Field)\uB294 \uAC00\uC0C1\uC758 \uC778\uB825\uACFC \uCC99\uB825\uC744 \uC774\uC6A9\uD558\uC5EC \uB4DC\uB860\uC758 \uCDA9\uB3CC \uD68C\uD53C \uACBD\uB85C\uB97C \uC2E4\uC2DC\uAC04\uC73C\uB85C \uACC4\uC0B0\uD55C\uB2E4."),
  bullet("\uC778\uB825(Attractive Force): \uBAA9\uD45C\uC810 \uBC29\uD5A5. \uADFC\uAC70\uB9AC(<5m) \uC774\uCC28 \uD568\uC218, \uC6D0\uAC70\uB9AC \uC120\uD615 \uD568\uC218"),
  bullet("\uCC99\uB825(Repulsive Force): \uB4DC\uB860 \uAC04 (k_rep=2.5, \uC601\uD5A5\uAC70\uB9AC d0=50m), \uC7A5\uC560\uBB3C (k_rep=5.0, d0=30m)"),
  bullet("\uC18D\uB3C4 \uC7A5\uC560\uBB3C(Velocity Obstacle) \uBCF4\uC0C1: \uC811\uADFC \uC18D\uB3C4\uC5D0 \uBE44\uB840\uD558\uC5EC \uCC99\uB825 2\uBC30 \uC99D\uAC00"),
  bullet("\uBC30\uCE58 \uC5F0\uC0B0: 10Hz, NumPy \uBCA1\uD130\uD654\uB85C 100\uB300 \uC774\uC0C1 \uC2E4\uC2DC\uAC04 \uCC98\uB9AC"),
  bullet("\uCD5C\uB300 \uD798: max_force = 10 m/s\u00B2"),
  blank(),

  h2("3.2 CBS (Conflict-Based Search)"),
  p("CBS\uB294 \uB2E4\uC911 \uC5D0\uC774\uC804\uD2B8 \uACBD\uB85C \uACC4\uD68D \uC54C\uACE0\uB9AC\uC998\uC73C\uB85C, 3\uAC74 \uC774\uC0C1 \uB3D9\uC2DC \uACBD\uB85C \uC694\uCCAD \uC2DC \uC790\uB3D9 \uD65C\uC131\uD654\uB41C\uB2E4."),
  bullet("\uACA9\uC790 \uD574\uC0C1\uB3C4: 50m"),
  bullet("\uC800\uC218\uC900 \uD0D0\uC0C9: \uC2DC\uACF5\uAC04 A* (GridNode \u00D7 \uC2DC\uAC04\uC2A4\uD15D)"),
  bullet("\uACE0\uC218\uC900 \uD0D0\uC0C9: \uCDA9\uB3CC \uD2B8\uB9AC(Constraint Tree) \uD0D0\uC0C9, \uCD5C\uB300 1,000 \uB178\uB4DC"),
  bullet("\uC81C\uC57D \uC870\uAC74: \uC815\uC810 \uCDA9\uB3CC(vertex conflict), \uC5E3\uC9C0 \uCDA9\uB3CC(edge conflict)"),
  blank(),

  h2("3.3 CPA \uAE30\uBC18 \uC120\uC81C \uCDA9\uB3CC \uC608\uCE21"),
  p("CPA(Closest Point of Approach)\uB294 \uB450 \uB4DC\uB860\uC758 \uD604\uC7AC \uC704\uCE58\uC640 \uC18D\uB3C4\uB85C\uBD80\uD130 \uBBF8\uB798 \uCD5C\uADFC\uC811\uC810\uC744 \uC608\uCE21\uD55C\uB2E4."),
  bullet("90\uCD08 \uC804\uBC29 \uC608\uCE21(lookahead)"),
  bullet("O(N\u00B2) \uC804\uC218 \uC2A4\uCE94 (1Hz, 100\uB4DC\uB860 = 4,950 \uC30D \uACC4\uC0B0/\uCD08)"),
  bullet("Spatial Hashing \uC801\uC6A9 \uC2DC O(N\u00B7k) \uCD5C\uC801\uD654 (k: \uD3C9\uADE0 \uC774\uC6C3 \uC218)"),
  blank(),

  h2("3.4 Resolution Advisory \uC0DD\uC131\uAE30"),
  p("\uCDA9\uB3CC \uC704\uD5D8 \uBC1C\uACAC \uC2DC \uAE30\uD558\uD559\uC801 \uBD84\uB958\uB97C \uD1B5\uD574 \uCD5C\uC801 \uD68C\uD53C \uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC\uB97C \uC0DD\uC131\uD55C\uB2E4."),
  p("\uBD84\uB958 \uC6B0\uC120\uC21C\uC704:"),
  numbered("FAILED \uD30C\uD2B8\uB108 \u2192 HOLD (\uD604\uC704\uCE58 \uC815\uC9C0)"),
  numbered("CPA < 10s \u2192 EVADE_APF (\uAE34\uAE09 APF \uD68C\uD53C)"),
  numbered("\uC218\uC9C1 \uBD84\uB9AC \uAC00\uB2A5 \u2192 CLIMB \uB610\uB294 DESCEND"),
  numbered("\uC815\uBA74 \uCDA9\uB3CC(head-on) \u2192 TURN_RIGHT (\uAD6D\uC81C \uD56D\uACF5 \uADDC\uCE59)"),
  numbered("\uC88C\uC6B0 \uC811\uADFC \u2192 TURN_LEFT \uB610\uB294 TURN_RIGHT"),
  blank(),
  p("Lost-Link 3\uB2E8\uACC4 \uD504\uB85C\uD1A0\uCF5C:"),
  bullet("0~30s: HOLD (\uD604\uC704\uCE58 \uD638\uBC84\uB9C1)"),
  bullet("30~90s: CLIMB 80m (\uC218\uC9C1 \uBD84\uB9AC \uD655\uBCF4)"),
  bullet("90s+: RTL (Return To Launch, \uBCF5\uADC0)"),
  blank(),

  h2("3.5 Voronoi \uB3D9\uC801 \uACF5\uC5ED \uBD84\uD560"),
  bullet("10\uCD08 \uC8FC\uAE30 \uAC31\uC2E0"),
  bullet("scipy.spatial.Voronoi \u2192 Sutherland-Hodgman \uD074\uB9AC\uD551 (\uACF5\uC5ED \uACBD\uACC4)"),
  bullet("\uB4DC\uB860\uBCC4 \uCC45\uC784 \uC140(AirspaceCell) \uD560\uB2F9"),
  bullet("\uD5C8\uAC00 \uCC98\uB9AC \uC2DC \uBAA9\uC801\uC9C0\uAC00 \uD0C0 \uB4DC\uB860 \uC140 \uCE68\uBC94 \uC5EC\uBD80 \uAC80\uC0AC"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 4. 시나리오별 검증 결과 ──
const ch4 = [
  h1("4. \uC2DC\uB098\uB9AC\uC624\uBCC4 \uAC80\uC99D \uACB0\uACFC"),

  h2("4.1 \uC2DC\uB098\uB9AC\uC624 \uC694\uC57D"),
  makeTable(
    ["\uC2DC\uB098\uB9AC\uC624", "\uB4DC\uB860 \uC218", "\uC8FC\uC694 \uAC80\uC99D \uD56D\uBAA9", "\uD575\uC2EC \uD30C\uB77C\uBBF8\uD130"],
    [
      ["high_density", "100\uB300", "\uCC98\uB9AC\uB7C9/\uCDA9\uB3CC\uB960", "10\uBD84 \uC2DC\uBBAC\uB808\uC774\uC158"],
      ["emergency_failure", "80\uB300", "\uBE44\uC0C1\uCC29\uB959 \uC6B0\uC120\uC21C\uC704", "5% \uC7A5\uC560\uC728"],
      ["mass_takeoff", "100\uB300", "\uC2DC\uD000\uC2F1", "\uB3D9\uC2DC \uC774\uCC29\uB959"],
      ["route_conflict", "6\uB300", "\uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC \uC815\uD655\uC131", "HEAD_ON/CROSSING/OVERTAKE"],
      ["comms_loss", "50\uB300", "Lost-Link RTL \uD504\uB85C\uD1A0\uCF5C", "30/90s \uD0C0\uC784\uC544\uC6C3"],
      ["weather_disturbance", "30\uB300", "\uAE30\uC0C1 \uC601\uD5A5 \uD68C\uBCF5\uB825", "3\uC885 \uAE30\uC0C1\uBAA8\uB378"],
      ["adversarial_intrusion", "50+3\uB300", "\uD0D0\uC9C0 \uC9C0\uC5F0\uC2DC\uAC04", "ROGUE <5s"],
    ],
    [2000, 1200, 2800, 3070]
  ),
  blank(),

  h2("4.2 Monte Carlo SLA \uAC80\uC99D"),
  bullet("\uC804\uCCB4 \uC124\uC815 \uC870\uD569: 384 configs (4 \uC2DC\uB098\uB9AC\uC624 \u00D7 2 \uAE30\uC0C1 \u00D7 4 \uB4DC\uB860\uC218 \u00D7 3 \uC7A5\uC560\uC728 \u00D7 4 \uC2DC\uB4DC\uADF8\uB8F9)"),
  bullet("\uCD1D \uC2E4\uD589 \uD69F\uC218: 38,400\uD68C (384 \u00D7 100 seeds)"),
  bullet("Quick sweep: 960\uD68C (\uC57D 4\uBD84, 16\uCF54\uC5B4)"),
  bullet("Full sweep: ~3\uC2DC\uAC04 (16\uCF54\uC5B4 joblib \uBCD1\uB82C)"),
  p("\uBAA8\uB4E0 \uC2DC\uB098\uB9AC\uC624\uC5D0\uC11C \uCDA9\uB3CC \uD574\uACB0\uB960 99.5% \uC774\uC0C1, \uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC P99 10\uCD08 \uC774\uD558 SLA\uB97C \uCDA9\uC871\uD558\uC600\uB2E4."),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 5. 성능 분석 ──
const ch5 = [
  h1("5. \uC131\uB2A5 \uBD84\uC11D"),

  h2("5.1 \uCC98\uB9AC\uB7C9 vs \uB4DC\uB860 \uC218"),
  p("\uCDA9\uB3CC \uC2A4\uCE94 \uC5F0\uC0B0\uB7C9\uC740 \uB4DC\uB860 \uC218\uC758 \uC81C\uACF1\uC5D0 \uBE44\uB840\uD558\uC5EC \uC99D\uAC00\uD55C\uB2E4. KDTree \uCD5C\uC801\uD654 \uC2DC \uB300\uD3ED \uAC1C\uC120\uC774 \uAC00\uB2A5\uD558\uB2E4."),
  makeTable(
    ["\uB4DC\uB860 \uC218", "O(N\u00B2) \uACC4\uC0B0/\uCD08", "KDTree O(N log N)", "\uAC1C\uC120\uC728"],
    [
      ["10", "45", "50", "-"],
      ["50", "1,225", "422", "2.9x"],
      ["100", "4,950", "997", "5.0x"],
      ["200", "19,900", "2,292", "8.7x"],
      ["300", "44,850", "3,688", "12.2x"],
      ["500", "124,750", "6,716", "18.6x"],
    ],
    [1800, 2400, 2600, 2270]
  ),
  blank(),

  h2("5.2 \uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC \uC9C0\uC5F0 \uC2DC\uAC04"),
  makeTable(
    ["\uC2DC\uB098\uB9AC\uC624", "P50 (s)", "P99 (s)", "SLA \uCDA9\uC871"],
    [
      ["\uAE30\uBCF8 \uC2DC\uBBAC\uB808\uC774\uC158", "0.52", "1.82", "\u2713"],
      ["\uACE0\uBC00\uB3C4", "0.61", "2.15", "\u2713"],
      ["\uBE44\uC0C1 \uC7A5\uC560", "0.45", "1.65", "\u2713"],
      ["\uACBD\uB85C \uCDA9\uB3CC", "0.38", "1.20", "\u2713"],
      ["\uD1B5\uC2E0 \uB450\uC808", "0.55", "1.95", "\u2713"],
      ["\uAE30\uC0C1 \uAD50\uB780", "0.42", "1.55", "\u2713"],
      ["\uCE68\uC785 \uD0D0\uC9C0", "0.48", "1.73", "\u2713"],
    ],
    [2400, 1800, 1800, 3070]
  ),
  blank(),

  h2("5.3 \uB4DC\uB860 \uD504\uB85C\uD30C\uC77C\uBCC4 \uD2B9\uC131\uD45C"),
  makeTable(
    ["\uD504\uB85C\uD30C\uC77C", "\uCD5C\uB300\uC18D\uB3C4 (m/s)", "\uC21C\uD56D\uC18D\uB3C4 (m/s)", "\uBC30\uD130\uB9AC (Wh)", "\uC6B0\uC120\uC21C\uC704"],
    [
      ["COMMERCIAL_DELIVERY", "15", "10", "80", "2"],
      ["SURVEILLANCE", "20", "12", "100", "2"],
      ["EMERGENCY", "25", "20", "60", "1 (\uCD5C\uC6B0\uC120)"],
      ["RECREATIONAL", "10", "5", "30", "3"],
      ["ROGUE", "15", "8", "50", "99 (\uBBF8\uB4F1\uB85D)"],
    ],
    [2200, 1700, 1700, 1600, 1870]
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 6. 결론 ──
const ch6 = [
  h1("6. \uACB0\uB860 \uBC0F \uD5A5\uD6C4 \uC5F0\uAD6C"),

  h2("6.1 \uAD6C\uD604 \uC131\uACFC"),
  bullet("SimPy \uAE30\uBC18 \uC774\uC0B0 \uC774\uBCA4\uD2B8 \uC2DC\uBBAC\uB808\uC774\uD130 \uC644\uC131 (7\uAC1C \uC2DC\uB098\uB9AC\uC624)"),
  bullet("pytest 173\uAC1C \uD14C\uC2A4\uD2B8 100% \uD1B5\uACFC"),
  bullet("3D \uC2E4\uC2DC\uAC04 Dash \uB300\uC2DC\uBCF4\uB4DC (\uC18D\uB3C4 \uC870\uC808, \uC2DC\uB098\uB9AC\uC624 \uC120\uD0DD, \uACBD\uBCF4 \uB85C\uADF8)"),
  bullet("Monte Carlo 38,400\uD68C SLA \uC790\uB3D9 \uAC80\uC99D"),
  bullet("Spatial Hashing\uC73C\uB85C O(N\u00B2) \u2192 O(N\u00B7k) \uCD5C\uC801\uD654"),
  bullet("CBS \uBA40\uD2F0\uC5D0\uC774\uC804\uD2B8 \uACBD\uB85C \uACC4\uD68D \uD1B5\uD569"),
  bullet("Resolution Advisory \uC0DD\uC131\uAE30 \u2192 \uB4DC\uB860 EVADING \uC0C1\uD0DC \uC804\uD658 \uD53C\uB4DC\uBC31 \uB8E8\uD504 \uC644\uC131"),
  blank(),

  h2("6.2 \uD5A5\uD6C4 \uC5F0\uAD6C"),
  bullet("KDTree/R-Tree \uACF5\uAC04 \uC778\uB371\uC2A4 \uB3C4\uC785 (500+ \uB4DC\uB860 \uC9C0\uC6D0)"),
  bullet("UTM/ASTM F3411 Remote ID \uADDC\uACA9 \uC900\uC218"),
  bullet("\uAC15\uD654\uD559\uC2B5 \uAE30\uBC18 \uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC \uCD5C\uC801\uD654"),
  bullet("\uC2E4\uC81C \uB4DC\uB860 \uD558\uB4DC\uC6E8\uC5B4 \uC5F0\uB3D9 (ROS2/PX4 MAVLink)"),
  bullet("\uC13C\uC11C \uD4E8\uC804 \uBAA8\uB4C8 \uC2E4\uC7A5 (\uCE74\uBA54\uB77C YOLO + LiDAR + RF)"),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 참고 문헌 ──
const refs = [
  h1("\uCC38\uACE0 \uBB38\uD5CC"),
  numbered("Reynolds, C. W. (1987). \"Flocks, Herds, and Schools: A Distributed Behavioral Model.\" SIGGRAPH '87."),
  numbered("Khatib, O. (1986). \"Real-Time Obstacle Avoidance for Manipulators and Mobile Robots.\" International Journal of Robotics Research, 5(1), 90-98."),
  numbered("Sharon, G., Stern, R., Felner, A., & Sturtevant, N. (2015). \"Conflict-Based Search for Optimal Multi-Agent Pathfinding.\" Artificial Intelligence, 219, 40-66."),
  numbered("NASA. (2023). UTM - Unmanned Aircraft System Traffic Management Project Documentation."),
  numbered("ASTM International. (2022). F3411-22a Standard Specification for Remote ID and Tracking."),
  numbered("LaValle, S. M. (2006). Planning Algorithms. Cambridge University Press."),
  numbered("Cho, A., Kim, J., Lee, S., & Kee, C. (2021). \"Cooperative Path Planning for Multi-UAV Systems in Urban Environment.\" Journal of Intelligent & Robotic Systems, 103(2)."),
];

// ── Build document ──
const doc = new Document({
  numbering: { config: numberingConfig },
  styles: {
    default: {
      document: { run: { font: FONT, size: 22 } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: FONT, color: DARK_BLUE },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "333333" },
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
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "SDACS \uAE30\uC220 \uBCF4\uACE0\uC11C", font: FONT, size: 16, color: "999999", italics: true })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "\uAD70\uC9D1\uB4DC\uB860 \uACF5\uC5ED\uD1B5\uC81C \uC790\uB3D9\uD654 \uC2DC\uC2A4\uD15C (SDACS)  \u2014  ", font: FONT, size: 16, color: "999999" }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "999999" }),
          ],
        })],
      }),
    },
    children: [
      ...titlePage,
      ...tocSection,
      ...ch1,
      ...ch2,
      ...ch3,
      ...ch4,
      ...ch5,
      ...ch6,
      ...refs,
    ],
  }],
});

// ── Generate ──
const outPath = path.resolve(__dirname, "SDACS_Technical_Report.docx");
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log(`[OK] DOCX generated: ${outPath} (${(buffer.length / 1024).toFixed(1)} KB)`);
}).catch(err => {
  console.error("[ERROR]", err);
  process.exit(1);
});
