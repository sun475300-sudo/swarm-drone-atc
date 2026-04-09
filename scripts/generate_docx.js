/**
 * SDACS Technical Report v3 Generator
 * Usage: node scripts/generate_docx.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat, TableOfContents,
} = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellPad = { top: 60, bottom: 60, left: 100, right: 100 };

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: "1B6CA8", type: ShadingType.CLEAR },
    margins: cellPad,
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF", font: "Arial", size: 20 })] })],
  });
}

function cell(text, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: opts.shade ? { fill: "F0F5FA", type: ShadingType.CLEAR } : undefined,
    margins: cellPad,
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      children: [new TextRun({ text, font: "Arial", size: 20, bold: opts.bold })],
    })],
  });
}

function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({ children: headers.map((h, i) => headerCell(h, colWidths[i])) }),
      ...rows.map((row, ri) =>
        new TableRow({
          children: row.map((c, ci) => cell(c, colWidths[ci], { shade: ri % 2 === 1 })),
        })
      ),
    ],
  });
}

function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text, bold: true, font: "Arial", size: 32 })] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 }, children: [new TextRun({ text, bold: true, font: "Arial", size: 26 })] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 120 }, children: [new TextRun({ text, bold: true, font: "Arial", size: 22 })] }); }
function p(text) { return new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text, font: "Arial", size: 20 })] }); }
function pb(label, value) {
  return new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: label + ": ", bold: true, font: "Arial", size: 20 }),
    new TextRun({ text: value, font: "Arial", size: 20 }),
  ]});
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1B6CA8" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "0A1628" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [
    // ── Title Page ──
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 2880, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children: [
        new Paragraph({ spacing: { after: 600 }, alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "SDACS", font: "Arial", size: 72, bold: true, color: "1B6CA8" }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [
          new TextRun({ text: "Swarm Drone Airspace Control System", font: "Arial", size: 28, color: "333333" }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [
          new TextRun({ text: "\uAD70\uC9D1\uB4DC\uB860 \uACF5\uC5ED\uD1B5\uC81C \uC790\uB3D9\uD654 \uC2DC\uC2A4\uD15C", font: "Arial", size: 24, color: "666666" }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, border: { top: { style: BorderStyle.SINGLE, size: 3, color: "1B6CA8" } }, children: [] }),
        new Paragraph({ spacing: { before: 400, after: 80 }, alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "\uAE30\uC220 \uBCF4\uACE0\uC11C v3.0", font: "Arial", size: 22, bold: true }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [
          new TextRun({ text: "\uAD6D\uB9BD \uBAA9\uD3EC\uB300\uD559\uAD50 \uB4DC\uB860\uAE30\uACC4\uACF5\uD559\uACFC", font: "Arial", size: 20 }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [
          new TextRun({ text: "\uCEA1\uC2A4\uD1A4 \uB514\uC790\uC778 2026", font: "Arial", size: 20 }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [
          new TextRun({ text: "\uC7A5\uC120\uC6B0 (Sunwoo Jang)", font: "Arial", size: 20, bold: true }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [
          new TextRun({ text: "\uC791\uC131\uC77C: 2026\uB144 4\uC6D4 6\uC77C", font: "Arial", size: 18, color: "666666" }),
        ]}),
      ],
    },
    // ── TOC ──
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      headers: {
        default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "SDACS Technical Report v3.0", font: "Arial", size: 16, color: "999999" })] })] }),
      },
      footers: {
        default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Page ", font: "Arial", size: 16 }), new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16 })] })] }),
      },
      children: [
        h1("\uBAA9\uCC28 (Table of Contents)"),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 1: Overview ──
        h1("1. \uC2DC\uC2A4\uD15C \uAC1C\uC694"),
        p("SDACS(Swarm Drone Airspace Control System)\uB294 \uAD70\uC9D1\uB4DC\uB860\uC744 \uC774\uB3D9\uD615 \uAC00\uC0C1 \uB808\uC774\uB354 \uB3D4(Dome)\uC73C\uB85C \uD65C\uC6A9\uD558\uC5EC, \uB3C4\uC2EC \uC800\uACE0\uB3C4 \uACF5\uC5ED\uC744 \uC790\uC728\uC801\uC73C\uB85C \uAC10\uC2DC\uD558\uACE0 \uCDA9\uB3CC\uC744 \uC0AC\uC804\uC5D0 \uBC29\uC9C0\uD558\uB294 \uBD84\uC0B0\uD615 \uACF5\uC5ED\uD1B5\uC81C \uC2DC\uBBAC\uB808\uC774\uC158 \uC2DC\uC2A4\uD15C\uC785\uB2C8\uB2E4."),
        p("\uACE0\uC815\uD615 \uB808\uC774\uB354 \uC778\uD504\uB77C \uC5C6\uC774 30\uBD84 \uB0B4 \uAE34\uAE09 \uBC30\uCE58\uAC00 \uAC00\uB2A5\uD558\uBA70, \uD0D0\uC9C0\uBD80\uD130 \uD68C\uD53C\uAE4C\uC9C0 \uC644\uC804 \uC790\uB3D9\uD654\uB85C 90\uCD08 \uC804 \uC120\uC81C \uCDA9\uB3CC \uC608\uCE21 \uBC0F 6\uC885 \uC790\uB3D9 \uC5B4\uB4DC\uBC14\uC774\uC800\uB9AC\uB97C \uBC1C\uD589\uD569\uB2C8\uB2E4."),

        h2("1.1 \uD575\uC2EC \uC131\uACFC \uC694\uC57D"),
        makeTable(
          ["Metric", "Value", "Description"],
          [
            ["Collision Resolution", "99.9%", "500\uB300 \uBA54\uAC00\uC2A4\uC6DC: 58,038 conflicts \u2192 19 collisions"],
            ["Prediction Lookahead", "90 seconds", "CPA \uAE30\uBC18 \uC120\uC81C \uCDA9\uB3CC \uD0D0\uC9C0 (1Hz)"],
            ["Advisory Latency", "< 1 second", "6\uC885 \uD68C\uD53C \uBA85\uB839: CLIMB/DESCEND/TURN/EVADE/HOLD"],
            ["Monte Carlo Validation", "38,400 runs", "384 configurations \u00D7 100 seeds"],
            ["Concurrent Drones", "500+", "\uBD84\uC0B0 \uC790\uC728 \uC81C\uC5B4"],
            ["Automated Tests", "2,620+", "pytest \uAE30\uBC18 \uC790\uB3D9\uD654 \uD14C\uC2A4\uD2B8 \uC2A4\uC704\uD2B8"],
            ["Languages", "50+", "Python + Rust/Go/C++/Zig/Fortran/Ada/VHDL \uB4F1"],
            ["Total Modules", "590+", "Phase 660 \uC644\uB8CC"],
          ],
          [2500, 2000, 4860],
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 2: Architecture ──
        h1("2. \uC2DC\uC2A4\uD15C \uC544\uD0A4\uD14D\uCC98"),
        p("SDACS\uB294 4\uAC1C\uC758 \uB3C5\uB9BD\uC801 \uACC4\uCE35\uC73C\uB85C \uAD6C\uC131\uB429\uB2C8\uB2E4. \uAC01 \uACC4\uCE35\uC740 \uBA85\uD655\uD55C \uC5ED\uD560\uACFC \uC778\uD130\uD398\uC774\uC2A4\uB97C \uAC00\uC9C0\uBA70, \uB3C5\uB9BD\uC801\uC73C\uB85C \uD14C\uC2A4\uD2B8 \uAC00\uB2A5\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Layer", "\uC5ED\uD560", "\uC8FC\uAE30", "\uD575\uC2EC \uBAA8\uB4C8"],
          [
            ["Layer 1: Drone Agent", "\uAC1C\uBCC4 \uB4DC\uB860 \uBB3C\uB9AC \uC2DC\uBBAC\uB808\uC774\uC158", "10Hz", "_DroneAgent (SimPy process)"],
            ["Layer 2: Control", "\uACF5\uC5ED \uAD00\uC81C + \uCDA9\uB3CC \uD0D0\uC9C0/\uD574\uACB0", "1Hz", "AirspaceController"],
            ["Layer 3: Simulation", "\uC2DC\uBBAC\uB808\uC774\uC158 \uC5D4\uC9C4 + MC \uAC80\uC99D", "Batch", "SwarmSimulator"],
            ["Layer 4: UI", "CLI + 3D \uC2DC\uAC01\uD654", "60fps", "main.py + Dash"],
          ],
          [2000, 2500, 1200, 3660],
        ),

        h2("2.1 \uB4DC\uB860 \uC5D0\uC774\uC804\uD2B8 (Layer 1)"),
        p("\uAC01 \uB4DC\uB860\uC740 SimPy \uC774\uC0B0 \uC774\uBCA4\uD2B8 \uD504\uB85C\uC138\uC2A4\uB85C \uBAA8\uB378\uB9C1\uB429\uB2C8\uB2E4. 10Hz \uC8FC\uAE30\uB85C \uC704\uCE58/\uC18D\uB3C4/\uBC30\uD130\uB9AC \uC0C1\uD0DC\uB97C \uAC31\uC2E0\uD558\uBA70, FSM(Finite State Machine)\uC5D0 \uB530\uB77C Idle \u2192 Takeoff \u2192 Cruise \u2192 Avoid \u2192 Landing \uC804\uC774\uB97C \uC218\uD589\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Constant", "Value", "Description"],
          [
            ["CRUISE_ALT", "60.0 m", "\uAE30\uBCF8 \uC21C\uD56D \uACE0\uB3C4"],
            ["TAKEOFF_RATE", "3.5 m/s", "\uC774\uB959 \uC0C1\uC2B9\uB960"],
            ["LAND_RATE", "2.5 m/s", "\uCC29\uB959 \uD558\uAC15\uB960"],
            ["WAYPOINT_TOL", "80.0 m", "\uC6E8\uC774\uD3EC\uC778\uD2B8 \uB3C4\uB2EC \uD5C8\uC6A9 \uC624\uCC28"],
            ["BATTERY_CRITICAL", "5.0%", "\uBC30\uD130\uB9AC \uC704\uAE30 \uC784\uACC4\uCE58"],
            ["EMERGENCY_WIND", "10.0 m/s", "\uAC15\uD48D \uBAA8\uB4DC \uC804\uD658 \uAE30\uC900"],
          ],
          [2500, 2000, 4860],
        ),

        h2("2.2 \uACF5\uC5ED \uAD00\uC81C\uAE30 (Layer 2)"),
        p("AirspaceController\uB294 1Hz \uC81C\uC5B4 \uB8E8\uD504\uB85C \uB3D9\uC791\uD558\uBA70, \uBAA8\uB4E0 \uD65C\uC131 \uB4DC\uB860\uC758 \uCDA9\uB3CC \uC704\uD5D8\uC744 \uC2E4\uC2DC\uAC04 \uD3C9\uAC00\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Parameter", "Value", "Description"],
          [
            ["\uC218\uD3C9 \uBD84\uB9AC", "50.0 m", "\uB450 \uB4DC\uB860 \uAC04 \uC218\uD3C9 \uCD5C\uC18C \uAC70\uB9AC"],
            ["\uC218\uC9C1 \uBD84\uB9AC", "15.0 m", "\uC218\uC9C1 \uCD5C\uC18C \uAC70\uB9AC"],
            ["\uB2C8\uC5B4\uBBF8\uC2A4 \uC218\uD3C9", "10.0 m", "\uB2C8\uC5B4\uBBF8\uC2A4 \uD310\uC815 \uC218\uD3C9"],
            ["\uCDA9\uB3CC \uC608\uCE21", "90.0 s", "CPA \uC120\uC81C \uD0D0\uC9C0 \uBC94\uC704"],
            ["Voronoi \uAC31\uC2E0", "10.0 s", "\uACF5\uC5ED \uBD84\uD560 \uC7AC\uACC4\uC0B0"],
            ["\uD48D\uC18D \uBD84\uB9AC \uBC30\uC728", "1.0\u00D7~1.6\u00D7", "\uD48D\uC18D \uC5F0\uB3D9 \uB3D9\uC801 \uC870\uC815"],
          ],
          [2500, 2000, 4860],
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 3: Core Algorithms ──
        h1("3. \uD575\uC2EC \uC54C\uACE0\uB9AC\uC998"),

        h2("3.1 CPA (Closest Point of Approach)"),
        p("O(N\u00B2) \uC30D\uBCC4 \uC2A4\uCE94\uC73C\uB85C \uBAA8\uB4E0 \uB4DC\uB860 \uC30D\uC758 \uCD5C\uADFC\uC811\uC810 \uC2DC\uAC01/\uAC70\uB9AC\uB97C 90\uCD08 \uC55E\uAE4C\uC9C0 \uC608\uCE21\uD569\uB2C8\uB2E4. \uBD84\uB9AC \uAE30\uC900 \uC774\uD558\uC77C \uACBD\uC6B0 ConflictAlert\uB97C \uC0DD\uC131\uD569\uB2C8\uB2E4."),

        h2("3.2 APF (Artificial Potential Field)"),
        p("\uC778\uB825\uC7A5(\uBAA9\uD45C \uBC29\uD5A5) + \uCC99\uB825\uC7A5(\uC7A5\uC560\uBB3C \uBC29\uD5A5) \uD569\uB825\uC73C\uB85C \uC548\uC804 \uADA4\uC801\uC744 \uC0DD\uC131\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Parameter", "Normal (\u22646m/s)", "Windy (\u226512m/s)", "Description"],
          [
            ["k_rep_drone", "2.5", "6.5", "\uB4DC\uB860 \uAC04 \uCC99\uB825 \uC774\uB4DD"],
            ["k_rep_obs", "5.0", "7.0", "\uC7A5\uC560\uBB3C \uCC99\uB825 \uC774\uB4DD"],
            ["d0_drone", "50.0 m", "80.0 m", "\uB4DC\uB860 \uCC99\uB825 \uC720\uD6A8 \uBC18\uACBD"],
            ["max_force", "10.0 m/s\u00B2", "22.0 m/s\u00B2", "\uD569\uB825 \uC0C1\uD55C"],
          ],
          [2000, 2000, 2000, 3360],
        ),
        p("\uD48D\uC18D 6~12 m/s \uAD6C\uAC04\uC5D0\uC11C\uB294 \uB450 \uD30C\uB77C\uBBF8\uD130 \uC14B\uC744 \uC120\uD615 \uBCF4\uAC04(lerp)\uD558\uC5EC \uBD80\uB4DC\uB7EC\uC6B4 \uC804\uD658\uC744 \uAD6C\uD604\uD569\uB2C8\uB2E4."),

        h2("3.3 CBS (Conflict-Based Search)"),
        p("\uB2E4\uC911 \uC5D0\uC774\uC804\uD2B8 \uCD5C\uC801 \uBE44\uCDA9\uB3CC \uACBD\uB85C\uB97C \uACC4\uC0B0\uD558\uB294 \uD0D0\uC0C9 \uC54C\uACE0\uB9AC\uC998\uC785\uB2C8\uB2E4. High-level\uC5D0\uC11C \uCDA9\uB3CC \uD2B8\uB9AC\uB97C \uD0D0\uC0C9\uD558\uACE0, Low-level\uC5D0\uC11C \uC2DC\uACF5\uAC04 A*\uB85C \uAC1C\uBCC4 \uACBD\uB85C\uB97C \uACC4\uD68D\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Parameter", "Value", "Description"],
          [
            ["GRID_RESOLUTION", "50.0 m", "3D \uACA9\uC790 \uC140 \uD06C\uAE30"],
            ["TIME_STEP", "1.0 s", "\uC2DC\uACF5\uAC04 \uACC4\uD68D \uB2E8\uC704"],
            ["Max Expansions", "100,000", "\uB4DC\uB860\uB2F9 A* \uB178\uB4DC \uD0D0\uC0C9 \uC0C1\uD55C"],
            ["Timeout (A*)", "5.0 s", "Wall-clock timeout"],
            ["Timeout (CBS)", "10.0 s", "\uC804\uCCB4 CBS \uD0D0\uC0C9 \uC2DC\uAC04 \uC81C\uD55C"],
          ],
          [2500, 2000, 4860],
        ),

        h2("3.4 Resolution Advisory"),
        p("6\uC885 \uD68C\uD53C \uBA85\uB839\uC744 \uAE30\uD558\uD559\uC801 \uBD84\uB958\uB85C \uC790\uB3D9 \uACB0\uC815\uD569\uB2C8\uB2E4: CLIMB, DESCEND, TURN_LEFT, TURN_RIGHT, EVADE_APF, HOLD. \uC218\uC9C1 \uBD84\uB9AC \uC6B0\uC120, 360\u00B0 \uBC29\uC704\uAC01 \uD310\uC815, \uD3D0\uC1C4\uC18D\uB3C4 \uBE44\uB840 \uC9C0\uC18D\uC2DC\uAC04 \uC124\uC815 \uC21C\uC73C\uB85C \uC9C4\uD589\uB429\uB2C8\uB2E4."),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 4: Simulation ──
        h1("4. \uC2DC\uBBAC\uB808\uC774\uC158 \uAC80\uC99D"),

        h2("4.1 7\uB300 \uD575\uC2EC \uC2DC\uB098\uB9AC\uC624"),
        makeTable(
          ["#", "Scenario", "Drones", "Duration", "Key Test"],
          [
            ["1", "Normal Operation", "20", "60s", "\uAE30\uBCF8 \uCDA9\uB3CC \uD574\uACB0\uB960"],
            ["2", "High Density", "50", "60s", "\uBC00\uC9D1 \uD658\uACBD \uC131\uB2A5"],
            ["3", "Weather Disturbance", "20", "60s", "\uD48D\uC18D 15m/s \uAC15\uD48D \uB300\uC751"],
            ["4", "Communication Loss", "20", "60s", "\uD1B5\uC2E0 \uB450\uC808 \uC2DC \uC790\uC728 \uD68C\uD53C"],
            ["5", "Intruder Response", "20", "60s", "\uBBF8\uB4F1\uB85D \uB4DC\uB860 \uD0D0\uC9C0/\uB300\uC751"],
            ["6", "Emergency Landing", "20", "60s", "\uBAA8\uD130/\uBC30\uD130\uB9AC/GPS \uACE0\uC7A5"],
            ["7", "Mass Delivery", "100", "120s", "\uB300\uADDC\uBAA8 \uBC30\uC1A1 \uB3D9\uC2DC \uC6B4\uC6A9"],
          ],
          [500, 2200, 1000, 1000, 4660],
        ),

        h2("4.2 Monte Carlo SLA \uAC80\uC99D"),
        p("384\uAC1C \uD30C\uB77C\uBBF8\uD130 \uC870\uD569 \u00D7 100 \uB79C\uB364 \uC2DC\uB4DC = \uCD1D 38,400\uD68C \uC2DC\uBBAC\uB808\uC774\uC158\uC744 \uC2E4\uD589\uD558\uC5EC \uD1B5\uACC4\uC801 \uC2E0\uB8B0\uC131\uC744 \uD655\uBCF4\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Metric", "Threshold", "Type"],
          [
            ["\uCDA9\uB3CC\uB960", "0\uAC74/1,000h", "Hard"],
            ["\uCDA9\uB3CC \uD574\uACB0\uB960", "\u226599.5%", "Hard"],
            ["\uC751\uB2F5 P99", "\u226410.0\uCD08", "Hard"],
            ["\uCE68\uC785 \uD0D0\uC9C0 P90", "\u22645.0\uCD08", "Hard"],
            ["\uACBD\uB85C \uD6A8\uC728", "\u22641.15", "Soft"],
          ],
          [3500, 3000, 2860],
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 5: Performance ──
        h1("5. \uC131\uB2A5 \uBD84\uC11D"),

        h2("5.1 \uCC98\uB9AC \uC131\uB2A5"),
        makeTable(
          ["Drones", "Tick Time", "Real-time Ratio", "Status"],
          [
            ["20", "0.8 ms", "1,250\u00D7", "Excellent"],
            ["50", "4.2 ms", "238\u00D7", "Excellent"],
            ["100", "16.1 ms", "62\u00D7", "Good"],
            ["200", "63.5 ms", "16\u00D7", "Acceptable"],
            ["500", "398.0 ms", "2.5\u00D7", "Near real-time"],
          ],
          [2000, 2500, 2500, 2360],
        ),

        h2("5.2 \uCDA9\uB3CC \uD574\uACB0\uB960"),
        p("\uCDA9\uB3CC \uD574\uACB0\uB960 = 1 \u2212 collisions / (conflicts + collisions)"),
        p("500\uB300 60\uCD08 \uC2DC\uBBAC\uB808\uC774\uC158: 58,038 conflicts \u2192 19 collisions \u2192 CR = 99.97%"),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 6: Drone Profiles ──
        h1("6. \uB4DC\uB860 \uD504\uB85C\uD30C\uC77C"),
        makeTable(
          ["Profile", "Max Speed", "Battery", "Endurance", "Priority"],
          [
            ["COMMERCIAL_DELIVERY", "15.0 m/s", "80 Wh", "30 min", "2"],
            ["SURVEILLANCE", "20.0 m/s", "100 Wh", "45 min", "2"],
            ["EMERGENCY", "25.0 m/s", "60 Wh", "20 min", "1 (\uCD5C\uC6B0\uC120)"],
            ["RECREATIONAL", "10.0 m/s", "30 Wh", "15 min", "3"],
            ["ROGUE (\uBBF8\uB4F1\uB85D)", "15.0 m/s", "50 Wh", "25 min", "99 (\uCD5C\uD558)"],
          ],
          [2500, 1500, 1500, 1500, 2360],
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 7: Multi-language ──
        h1("7. \uB2E4\uC911 \uC5B8\uC5B4 \uC544\uD0A4\uD14D\uCC98"),
        p("SDACS\uB294 Python \uD575\uC2EC \uC5D4\uC9C4 \uC678\uC5D0 50\uAC1C \uC774\uC0C1\uC758 \uD504\uB85C\uADF8\uB798\uBC0D \uC5B8\uC5B4\uB85C \uAD6C\uD604\uB41C 220+ \uBCF4\uC870 \uBAA8\uB4C8\uC744 \uD3EC\uD568\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Language", "Modules", "Use Case"],
          [
            ["Python", "580+", "Core: simulation, ML/AI, analytics"],
            ["Rust", "15", "Safety-critical: satellite comm, verifier"],
            ["Go", "14", "Concurrent: edge AI, realtime monitor"],
            ["C++", "14", "Performance: SLAM, physics, particle filter"],
            ["Zig", "15", "Low-level: PBFT consensus, ring buffer"],
            ["Fortran", "9", "Numerical: wind FDM, CFD wind tunnel"],
            ["Ada/VHDL", "14", "Hardware sim, fault tolerance"],
            ["Others (40+)", "100+", "TypeScript, Swift, Kotlin, Prolog, etc."],
          ],
          [2000, 1500, 5860],
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 8: CI/CD ──
        h1("8. CI/CD \uD30C\uC774\uD504\uB77C\uC778"),
        p("GitHub Actions \uAE30\uBC18 CI/CD \uD30C\uC774\uD504\uB77C\uC778\uC73C\uB85C Python 3.10/3.11/3.12 \uB9E4\uD2B8\uB9AD\uC2A4 \uD14C\uC2A4\uD2B8\uB97C \uC218\uD589\uD569\uB2C8\uB2E4."),
        makeTable(
          ["Step", "\uB0B4\uC6A9"],
          [
            ["Lint", "flake8 --select=E9,F63,F7,F82 (\uAD6C\uBB38 \uC624\uB958 + \uBBF8\uC815\uC758 \uC774\uB984)"],
            ["Test", "pytest tests/ -v --timeout=60 --cov=simulation --cov=src"],
            ["Coverage", "HTML \uB9AC\uD3EC\uD2B8 \uC0DD\uC131 + \uC544\uD2F0\uD329\uD2B8 \uC5C5\uB85C\uB4DC (30\uC77C \uBCF4\uC874)"],
            ["Import Check", "\uD575\uC2EC 3\uAC1C \uBAA8\uB4C8 \uC784\uD3EC\uD2B8 \uAC80\uC99D"],
            ["Ops Report", "main \uD478\uC2DC \uC2DC JSON \uBC88\uB4E4 \uC0DD\uC131 (90\uC77C \uBCF4\uC874)"],
          ],
          [2500, 6860],
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ── Chapter 9: Conclusion ──
        h1("9. \uACB0\uB860 \uBC0F \uD5A5\uD6C4 \uACC4\uD68D"),
        p("SDACS\uB294 \uAD70\uC9D1\uB4DC\uB860\uC744 \uC774\uB3D9\uD615 \uAC00\uC0C1 \uB808\uC774\uB354\uB85C \uD65C\uC6A9\uD558\uC5EC \uACE0\uC815 \uC778\uD504\uB77C \uC5C6\uC774 \uC800\uACE0\uB3C4 \uACF5\uC5ED\uC744 \uC790\uC728\uC801\uC73C\uB85C \uD1B5\uC81C\uD558\uB294 \uC2DC\uC2A4\uD15C\uC744 \uAD6C\uD604\uD588\uC2B5\uB2C8\uB2E4. 660\uAC1C Phase\uC5D0 \uAC78\uCE5C \uC810\uC9C4\uC801 \uAC1C\uBC1C\uC744 \uD1B5\uD574 590+ \uBAA8\uB4C8, 2,620+ \uD14C\uC2A4\uD2B8, 50+ \uC5B8\uC5B4\uB85C \uAD6C\uC131\uB41C \uB300\uADDC\uBAA8 \uC2DC\uC2A4\uD15C\uC744 \uC644\uC131\uD588\uC73C\uBA70, 99.9% \uCDA9\uB3CC \uD574\uACB0\uB960\uACFC 38,400\uD68C Monte Carlo \uAC80\uC99D\uC744 \uB2EC\uC131\uD588\uC2B5\uB2C8\uB2E4."),
        p("\uD5A5\uD6C4\uB294 \uC2E4\uC81C \uB4DC\uB860 \uD558\uB4DC\uC6E8\uC5B4 \uC5F0\uB3D9, \uB354 \uC815\uAD50\uD55C AI \uAE30\uBC18 \uACBD\uB85C \uACC4\uD68D, \uADF8\uB9AC\uACE0 UAM \uC5F0\uB3D9\uC744 \uD1B5\uD55C \uD655\uC7A5\uC744 \uACC4\uD68D\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4."),

        h2("\uCC38\uACE0 \uBB38\uD5CC"),
        p("[1] SimPy \u2014 Discrete Event Simulation for Python"),
        p("[2] Khatib, O. (1986). Real-time obstacle avoidance for manipulators and mobile robots."),
        p("[3] Sharon, G. et al. (2015). CBS for optimal multi-agent pathfinding."),
        p("[4] Kuchar, J.K. & Yang, L.C. (2000). Conflict detection and resolution modeling methods."),
        p("[5] Aurenhammer, F. (1991). Voronoi diagrams \u2014 a survey."),
        p("[6] Reynolds, C.W. (1987). Flocks, herds and schools: A distributed behavioral model."),
      ],
    },
  ],
});

const outPath = path.resolve(__dirname, "..", "docs", "report", "SDACS_Technical_Report_v3.docx");
Packer.toBuffer(doc).then(buffer => {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buffer);
  console.log(`\u2705 Technical Report saved: ${outPath}`);
}).catch(err => {
  console.error("\u274C Error:", err);
  process.exit(1);
});
