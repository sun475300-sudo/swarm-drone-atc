#!/usr/bin/env python3
"""`window._sdacs` API 레퍼런스 자동 생성기.

`swarm_3d_simulator.html`의 `window._sdacs = { ... }` 객체를 파싱해
top-level 항목(getter/method/property)을 추출하고, 객체 내부의
`// ===== Phase N — ... =====` 섹션 주석을 기준으로 그룹핑하여
`docs/SDACS_API.md`를 생성한다.

사용:
    python scripts/gen_sdacs_api.py            # docs/SDACS_API.md 갱신
    python scripts/gen_sdacs_api.py --check    # 최신 여부만 검사(미갱신 시 exit 1)

설계 원칙(KISS): 정규식 한 줄 매칭이 아니라 중괄호 깊이를 추적해
top-level 항목만 잡는다. 다중 라인 함수 본문에 오탐하지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM_HTML = ROOT / "swarm_3d_simulator.html"
OUT_MD = ROOT / "docs" / "SDACS_API.md"

# top-level 항목 헤더: `get name(` / `name(` / `name:` (들여쓰기 무관, 한 줄 매칭은 깊이 0에서만 적용)
_ENTRY_RE = re.compile(r"^(get\s+)?([A-Za-z_]\w*)\s*([(:])")
_SECTION_RE = re.compile(r"^//\s*=+\s*(.+?)\s*=+\s*$")
_SIG_MAX = 200  # 표에 넣는 시그니처 최대 길이

# 손으로 작성한 사용 예시·관련 문서 — 자동 표 뒤에 그대로 보존(재생성 시 유지)
_FOOTER = """## 🧪 사용 예시

```javascript
// 시뮬 시작 + 첫 드론 선택 + ATC HOLD 명령
window._sdacs.startSim();
const id = window._sdacs.selectDrone(0);
window._sdacs.atcCommand(id, 'HOLD');

// 시네마틱 모드: 동적 태양 + 비 + 녹화 시작
window._sdacs.setSunCycle(true);
window._sdacs.setSunAuto(true);
window._sdacs.setRain(true, 0.7);
window._sdacs.startRecording();

// 임무 5종 템플릿 일괄 할당
['search_grid', 'recon_orbit', 'delivery', 'spray_voronoi', 'medical_heap']
  .forEach((tmpl, i) => window._sdacs.missionAssignTemplate(i, tmpl));

// 장애 시나리오 EMP + LaTeX 표 출력
window._sdacs.injectScenario('EMP');
window._sdacs.exportLatexKpi();

// HYPER Phase 14/15: 시나리오 갤러리 열기 + 다국어 전환
window._sdacs.openGallery();
window._sdacs.setLang('ja');
```

## 🔗 관련 문서

- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) — Phase 1-9 마스터
- [`SIMULATOR_PHASE_PLANS.md`](SIMULATOR_PHASE_PLANS.md) — 상세 명세
- [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) — Phase 10-50 미래
- [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md) — 데스크탑 v1.1 빌드 절차
"""


def extract_block(html: str) -> str:
    """`window._sdacs = {` 의 매칭 닫는 중괄호까지 객체 본문을 반환."""
    anchor = html.index("window._sdacs = {")
    start = html.index("{", anchor)
    depth = 0
    for j in range(start, len(html)):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start + 1 : j]
    raise ValueError("window._sdacs 객체의 닫는 중괄호를 찾지 못했습니다.")


def classify(entry_line: str, has_get: bool) -> str:
    if has_get:
        return "get"
    # `name:` 형태(값/화살표 프로퍼티)와 `name(` 형태(메서드) 구분
    return "method" if "(" in entry_line.split(":", 1)[0] else "prop"


def parse_entries(block: str):
    """[(section, kind, name, signature), ...] 순서 보존 반환."""
    out = []
    section = "Phase 0 — 코어 / 기본"
    depth = 0
    for raw in block.split("\n"):
        line = raw.strip()
        if depth == 0 and line:
            sec = _SECTION_RE.match(line)
            if sec:
                section = sec.group(1).strip()
            elif not line.startswith("//"):
                m = _ENTRY_RE.match(line)
                if m:
                    has_get = bool(m.group(1))
                    name = m.group(2)
                    if name != "get":
                        kind = classify(line, has_get)
                        sig = line.rstrip()
                        if len(sig) > _SIG_MAX:
                            sig = sig[:_SIG_MAX] + " …"
                        out.append((section, kind, name, sig))
        depth += raw.count("{") - raw.count("}")
    return out


def _esc(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render(entries, src_hash: str) -> str:
    today = _dt.date.today().isoformat()
    # 섹션 순서 보존(첫 등장 순)
    sections: list[str] = []
    by_section: dict[str, list] = {}
    for section, kind, name, sig in entries:
        if section not in by_section:
            by_section[section] = []
            sections.append(section)
        by_section[section].append((kind, name, sig))

    lines = [
        "# 📚 `window._sdacs` API 레퍼런스",
        "",
        f"*자동 생성: {today} — `scripts/gen_sdacs_api.py` · "
        f"source `swarm_3d_simulator.html` (md5 `{src_hash}`)*",
        "",
        f"**전체 항목 수: {len(entries)}개**",
        "",
        "> 이 문서는 스크립트로 생성됩니다. 직접 수정하지 말고 "
        "`python scripts/gen_sdacs_api.py` 를 실행하세요.",
        "",
        "---",
        "",
        "## 📋 Phase별 분류",
        "",
    ]
    for section in sections:
        lines.append(f"### {section}")
        lines.append("")
        lines.append("| Kind | Name | Signature |")
        lines.append("|---|---|---|")
        for kind, name, sig in by_section[section]:
            lines.append(f"| `{kind}` | **`{name}`** | `{_esc(sig)}` |")
        lines.append("")

    # 알파벳순 전체 인덱스(자동)
    lines += ["## 🔎 전체 알파벳순", "", "| Kind | Name | Signature |", "|---|---|---|"]
    for _section, kind, name, sig in sorted(entries, key=lambda e: e[2].lower()):
        lines.append(f"| `{kind}` | **`{name}`** | `{_esc(sig)}` |")
    lines.append("")

    lines.append(_FOOTER)
    return "\n".join(lines).rstrip() + "\n"


def generate() -> str:
    html = SIM_HTML.read_text(encoding="utf-8")
    src_hash = hashlib.md5(html.encode("utf-8")).hexdigest()[:8]
    block = extract_block(html)
    entries = parse_entries(block)
    return render(entries, src_hash)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="갱신 필요 여부만 검사")
    args = ap.parse_args()

    new_md = generate()
    if args.check:
        cur = OUT_MD.read_text(encoding="utf-8") if OUT_MD.exists() else ""

        # 생성 날짜 줄은 매일 바뀌므로 비교에서 제외
        def norm(s: str) -> str:
            return re.sub(r"\*자동 생성:.*?\*", "", s)

        if norm(cur) == norm(new_md):
            print(f"✅ {OUT_MD.relative_to(ROOT)} 최신 (항목 수 일치)")
            return 0
        print(f"❌ {OUT_MD.relative_to(ROOT)} 갱신 필요 — gen_sdacs_api.py 실행")
        return 1

    OUT_MD.write_text(new_md, encoding="utf-8")
    count = new_md.split("전체 항목 수: ", 1)[1].split("개", 1)[0]
    print(f"✅ {OUT_MD.relative_to(ROOT)} 생성 — {count}개 항목")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
