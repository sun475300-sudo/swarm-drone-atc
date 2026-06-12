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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="문서 불일치 시 exit 1 (재생성 안 함)")
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
        print("✅ 문서-실측 일치" if ok else "⚠️ 재생성 필요: python scripts/extract_sdacs_api.py")
        return 0 if ok else 1

    API_MD.write_text(api_md, encoding="utf-8")
    DTS.write_text(dts, encoding="utf-8")
    print(f"✅ {API_MD.relative_to(ROOT)} · {DTS.relative_to(ROOT)} 재생성 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
