#!/usr/bin/env python3
"""SDACS `_sdacs` API 라이브 실측 추출기 (MASTER_PLAN_2026H2 Track G-1).

시뮬레이터 HTML을 헤드리스 Chromium으로 로드해 window._sdacs의
실제 키 목록·kind(getter/method)·maturity 등급을 추출하고,
docs/SDACS_API.md 와 docs/sdacs.d.ts 를 재생성한다.

사용:
    python scripts/extract_sdacs_api.py            # 두 문서 재생성
    python scripts/extract_sdacs_api.py --check    # 문서와 실측 불일치 시 exit 1 (CI 게이트)

전제: pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import datetime
import http.server
import json
import re
import socketserver
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM_HTML = "swarm_3d_simulator.html"
API_MD = ROOT / "docs" / "SDACS_API.md"
DTS = ROOT / "docs" / "sdacs.d.ts"
PORT = 0  # 0 = OS 임시 포트 할당 (브라우저 자식 프로세스의 fd 상속 충돌 방지)

MATURITY_ICON = {
    "production": "🟢",
    "beta": "🔵",
    "mock": "🟡",
    "speculative": "⚪",
    "(helper)": "🛠",
}


def extract_live() -> dict:
    """로컬 HTTP 서버 + 헤드리스 Chromium으로 _sdacs 실측 추출."""
    from playwright.sync_api import sync_playwright

    handler = http.server.SimpleHTTPRequestHandler

    class _QuietHandler(handler):
        def log_message(self, *args):  # noqa: D102
            pass

        def translate_path(self, path):
            # 항상 리포 루트 기준으로 서빙
            import os
            rel = path.lstrip("/")
            return os.path.join(str(ROOT), rel)

    class _ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    with _ReusableServer(("127.0.0.1", PORT), _QuietHandler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(args=["--use-gl=swiftshader", "--disable-gpu"])
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{port}/{SIM_HTML}", wait_until="load", timeout=60000)
                page.wait_for_function(
                    "() => window._sdacs && typeof window._sdacs.maturityReport === 'function'",
                    timeout=30000,
                )
                data = page.evaluate(
                    """() => {
                        const rep = window._sdacs.maturityReport();
                        const out = [];
                        for (const key of Object.keys(window._sdacs)) {
                            const desc = Object.getOwnPropertyDescriptor(window._sdacs, key);
                            let kind = 'method';
                            if (desc.get && !desc.set) kind = 'get';
                            else if (desc.get && desc.set) kind = 'accessor';
                            else if (typeof desc.value !== 'function') kind = 'value';
                            out.push({ name: key, kind, maturity: rep.byApi[key] || '(helper)' });
                        }
                        return { apis: out, counts: rep.counts, total: rep.total };
                    }"""
                )
                browser.close()
        finally:
            httpd.shutdown()
    return data


def render_api_md(data: dict) -> str:
    apis = sorted(data["apis"], key=lambda a: a["name"].lower())
    c = data["counts"]
    helpers = len(apis) - data["total"]
    today = datetime.date.today().isoformat()

    # 기존 문서의 사용 예시/참고 tail 보존
    tail = ""
    if API_MD.exists():
        old = API_MD.read_text(encoding="utf-8")
        m = (
            re.search(r"\n(## 🧪[\s\S]*)$", old)
            or re.search(r"\n(## 💡[\s\S]*)$", old)
            or re.search(r"\n(## 🔗 참고[\s\S]*)$", old)
        )
        if m:
            tail = m.group(1)

    lines = [
        "# 📚 `window._sdacs` API — Phase 200 (Unity) 완료 시점\n",
        f"*자동 생성: {today} (`scripts/extract_sdacs_api.py` 라이브 실측 추출 · maturity 등급 포함)*\n",
        f"**총 {len(apis)} 항목** (maturity 분류 대상 {data['total']} + 분류 헬퍼 {helpers})"
        " — MEGA 10 + HYPER 40 + STELLAR 50 + ULTIMATE 50 + POST-UNIVERSE 50 = **200 Phase**\n",
        "## 🎯 성숙도 분포 (Phase 201-207 정직성 공시)\n",
        "| 등급 | 개수 | 의미 |",
        "|---|:-:|---|",
        f"| 🟢 production | {c['production']} | 실측 검증 + 회귀 + 실 알고리즘 |",
        f"| 🔵 beta | {c['beta']} | 기능 동작 + E2E 검증, 일부 외부 의존 |",
        f"| 🟡 mock | {c['mock']} | 결정적 mock, 인터페이스만 안정 |",
        f"| ⚪ speculative | {c['speculative']} | 미래 비전 스텁, 호출 안전성만 보장 |",
        f"| 🛠 helper | {helpers} | `apiMaturity` · `maturityReport` 분류기 자체 |",
        "",
        "실시간 조회: `window._sdacs.apiMaturity(name)` · `window._sdacs.maturityReport()`\n",
        "## 📑 전체 API (알파벳순)\n",
        "| Kind | Name | Maturity |",
        "|---|---|---|",
    ]
    for a in apis:
        icon = MATURITY_ICON.get(a["maturity"], "")
        lines.append(f"| `{a['kind']}` | **`{a['name']}`** | {icon} {a['maturity']} |")
    lines.append("")
    return "\n".join(lines) + "\n" + tail


def render_dts(data: dict) -> str:
    apis = data["apis"]
    today = datetime.date.today().isoformat()
    lines = [
        "// SDACS Simulator window._sdacs TypeScript Declaration File",
        f"// 자동 생성: {today} (scripts/extract_sdacs_api.py 라이브 실측 추출)",
        f"// 총 {len(apis)}개 API — 200 Phase + TRANSCENDENCE Phase 201-207 (Maturity)",
        "// 성숙도: window._sdacs.maturityReport() 로 production/beta/mock/speculative 조회",
        "",
        "declare global {",
        "  interface Window { _sdacs: SDACS; }",
        "  interface SDACS {",
    ]
    for a in apis:
        mat = a["maturity"]
        if a["kind"] == "get":
            lines.append(f"    /** [getter · {mat}] */ readonly {a['name']}: any;")
        elif a["kind"] == "accessor":
            lines.append(f"    /** [accessor · {mat}] */ {a['name']}: any;")
        elif a["kind"] == "value":
            lines.append(f"    /** [value · {mat}] */ {a['name']}: any;")
        else:
            lines.append(f"    /** [{mat}] */ {a['name']}(...args: any[]): any;")
    lines += ["  }", "}", "", "export {};", ""]
    return "\n".join(lines)


LEDGER = ROOT / "docs" / "TECH_DEBT_LEDGER.md"

# 격상 난이도 큐레이션 (GENESIS Phase 388) — 접두사 그룹별 수동 평가
LEDGER_DIFFICULTY = {
    "stellar51": ("⭐⭐⭐", "실 LLM 연동 필요 — 현재 상태 기반 결정적 권고로 부분 격상됨"),
    "gpu100k": ("⭐⭐⭐⭐", "WGSL 실 컴파일 + 대규모 버퍼 (TRANSCENDENCE 221)"),
    "cesium": ("⭐⭐⭐", "Cesium ion 토큰 + 외부 타일셋 의존"),
    "ros2": ("⭐⭐⭐⭐", "ROS2 브릿지 실 연결 (src/ros2_bridge.py 재사용 가능)"),
    "qkd": ("⭐⭐⭐⭐⭐", "실 양자 채널 없음 — 영구 mock 후보"),
    "skybrush": ("⭐⭐⭐", "Skybrush 라이브러리 통합"),
    "hitl": ("⭐⭐⭐⭐", "실 Pixhawk HW 필요 (TRANSCENDENCE 261-270)"),
    "satellite": ("⭐⭐⭐⭐⭐", "위성 링크 — 영구 mock 후보"),
}


def render_ledger(data: dict) -> str:
    today = datetime.date.today().isoformat()
    mock = sorted(a["name"] for a in data["apis"] if a["maturity"] == "mock")
    spec = sorted(a["name"] for a in data["apis"] if a["maturity"] == "speculative")

    def group(names: list[str]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for n in names:
            m = re.match(r"^[a-z]+", n)
            key = m.group(0) if m else n
            out.setdefault(key, []).append(n)
        return out

    lines = [
        "# 📒 SDACS 기술 부채 대장 (GENESIS Phase 388)\n",
        f"*자동 생성: {today} (`scripts/extract_sdacs_api.py --ledger` 라이브 실측)*\n",
        "> 정직성 공시: 아래 API는 **결정적 mock 또는 speculative 스텁**이다. "
        "인터페이스는 안정적이나 실측 알고리즘/외부 연동이 없다. "
        "호출 시 console.warn 1회 + `maturityReport().mockCalls` 카운트 (Phase 203 Mock Detector).\n",
        f"## 요약 — mock {len(mock)} + speculative {len(spec)} = {len(mock) + len(spec)} 항목\n",
        "| 구분 | 의미 | 격상 경로 |",
        "|---|---|---|",
        f"| 🟡 mock ({len(mock)}) | 결정적 가짜 구현 | TRANSCENDENCE Track 🔬 (221-240) 실측 교체 |",
        f"| ⚪ speculative ({len(spec)}) | 미래 비전 스텁 | `_sdacs.experimental.*` 격리 (Phase 206) — 격상 비목표 |",
        "",
        "## 🟡 mock 그룹별 격상 난이도\n",
        "| 접두사 그룹 | API 수 | 난이도 | 격상 메모 |",
        "|---|:-:|:-:|---|",
    ]
    for prefix, names in sorted(group(mock).items()):
        diff, note = LEDGER_DIFFICULTY.get(prefix, ("⭐⭐", "결정적 mock — 실 데이터/라이브러리 연결로 격상 가능"))
        lines.append(f"| `{prefix}*` | {len(names)} | {diff} | {note} |")
    lines += [
        "",
        "## 🟡 mock 전체 목록\n",
        "<details><summary>펼치기</summary>\n",
        "\n".join(f"- `{n}`" for n in mock),
        "\n</details>\n",
        "## ⚪ speculative 전체 목록 (experimental.* 경유 접근)\n",
        "<details><summary>펼치기</summary>\n",
        "\n".join(f"- `{n}`" for n in spec),
        "\n</details>\n",
        "## 🔗 관련",
        "- [`SDACS_API.md`](SDACS_API.md) — 전체 API maturity 레퍼런스",
        "- [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) — 격상 로드맵 (Track 🔬)",
        "- [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) — Phase 388 본 대장 정의",
        "",
    ]
    return "\n".join(lines)


BADGE = ROOT / "docs" / "badges" / "maturity.svg"

# maturity 배지 세그먼트 (단축 라벨, counts 키, 색상) — SDACS_API.md 등급 색과 일치
_BADGE_SEGMENTS = [
    ("prod", "production", "#22c55e"),
    ("beta", "beta", "#3b82f6"),
    ("mock", "mock", "#f59e0b"),
    ("spec", "speculative", "#9ca3af"),
]
_BADGE_LABEL = "maturity"
_BADGE_LABEL_W = 74   # 좌측 라벨 세그먼트 폭
_BADGE_CHAR_W = 6     # font-size 10 대략 글자 폭
_BADGE_PAD = 14       # 세그먼트 좌우 여백


def badge_title(counts: dict) -> str:
    """배지 <title>/정합성 게이트용 counts 요약 문자열."""
    return " / ".join(f"{key} {counts[key]}" for _, key, _ in _BADGE_SEGMENTS)


def render_badge(data: dict) -> str:
    """maturityReport().counts → shields 스타일 maturity 배지 SVG (Phase 207).

    실측 counts 로부터 세그먼트 폭을 계산해 docs/badges/maturity.svg 를 재생성한다.
    순수 함수 — 브라우저/playwright 불필요(단위 테스트 가능).
    """
    counts = data["counts"]
    segs = []
    x = _BADGE_LABEL_W
    for short, key, color in _BADGE_SEGMENTS:
        text = f"{short} {counts[key]}"
        w = _BADGE_PAD + _BADGE_CHAR_W * len(text)
        segs.append((x, w, color, text))
        x += w
    total = x

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" '
        'role="img" aria-label="API Maturity">',
        f"  <title>API Maturity: {badge_title(counts)}</title>",
        '  <linearGradient id="s" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/></linearGradient>',
        f'  <rect rx="3" width="{total}" height="20" fill="#555"/>',
    ]
    for x0, w, color, _ in segs:
        lines.append(f'  <rect x="{x0}" width="{w}" height="20" fill="{color}"/>')
    lines.append(f'  <rect rx="3" width="{total}" height="20" fill="url(#s)"/>')
    lines.append(
        '  <g fill="#fff" text-anchor="middle" '
        'font-family="DejaVu Sans,Verdana,sans-serif" font-size="10">'
    )
    lines.append(f'    <text x="{_BADGE_LABEL_W // 2}" y="14">{_BADGE_LABEL}</text>')
    for x0, w, _, text in segs:
        lines.append(f'    <text x="{x0 + w // 2}" y="14">{text}</text>')
    lines += ["  </g>", "</svg>", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="문서 불일치 시 exit 1 (재생성 안 함)")
    parser.add_argument("--ledger", action="store_true", help="docs/TECH_DEBT_LEDGER.md 도 재생성")
    parser.add_argument("--badge", action="store_true", help="docs/badges/maturity.svg 도 재생성")
    args = parser.parse_args()

    data = extract_live()
    print(
        f"실측: 총 {len(data['apis'])} API | 분류 {data['total']} | "
        f"counts={json.dumps(data['counts'], ensure_ascii=False)}"
    )

    api_md = render_api_md(data)
    dts = render_dts(data)

    if args.check:
        ok = True
        current_md = API_MD.read_text(encoding="utf-8") if API_MD.exists() else ""
        if f"**총 {len(data['apis'])} 항목**" not in current_md:
            print(f"❌ SDACS_API.md 총 항목 수가 실측({len(data['apis'])})과 불일치")
            ok = False
        current_dts = DTS.read_text(encoding="utf-8") if DTS.exists() else ""
        if f"총 {len(data['apis'])}개 API" not in current_dts:
            print(f"❌ sdacs.d.ts 총 항목 수가 실측({len(data['apis'])})과 불일치")
            ok = False
        current_badge = BADGE.read_text(encoding="utf-8") if BADGE.exists() else ""
        if badge_title(data["counts"]) not in current_badge:
            print(f"❌ maturity.svg 배지 counts 가 실측({badge_title(data['counts'])})과 불일치")
            ok = False
        print("✅ 문서-실측 일치" if ok else "⚠️ 재생성 필요: python scripts/extract_sdacs_api.py --ledger --badge")
        return 0 if ok else 1

    API_MD.write_text(api_md, encoding="utf-8")
    DTS.write_text(dts, encoding="utf-8")
    print(f"✅ {API_MD.relative_to(ROOT)} · {DTS.relative_to(ROOT)} 재생성 완료")
    if args.ledger:
        LEDGER.write_text(render_ledger(data), encoding="utf-8")
        print(f"✅ {LEDGER.relative_to(ROOT)} 재생성 완료")
    if args.badge:
        BADGE.write_text(render_badge(data), encoding="utf-8")
        print(f"✅ {BADGE.relative_to(ROOT)} 재생성 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
