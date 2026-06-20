"""ODYSSEY Phase 483 — Three.js 메이저 업그레이드 리허설 감사.

Continuum 트랙(Phase 481-500)의 한 칸. 웹 시뮬레이터(``swarm_3d_simulator.
html``)는 벤더링된 Three.js(현재 ``vendor/three/three.module.js`` REVISION
162)에 의존한다. 라이브러리를 다음 메이저로 올릴 때 *어떤 심볼이 사라져
조용히 깨지는지* 를 사람이 매번 직관으로 점검하지 않도록, 본 모듈은 업그레이드
리허설을 *결정적 감사*로 명문화한다 — 같은 입력(시뮬 HTML + 벤더 빌드)은
항상 같은 판정을 낸다.

설계 원칙
--------
- **빌드가 진실의 근원**: 가장 단단한 보증은 "시뮬레이터가 쓰는 모든
  ``THREE.<심볼>`` 이 실제로 벤더 빌드의 export 인가" 다. export 목록은
  ``three.module.js`` 의 ``export { ... }`` 블록에서 *직접* 파싱하므로 추측이
  없다. 새 빌드를 떨어뜨리고 본 감사를 다시 돌리면, 사라진 심볼이 즉시
  ``MISSING`` 으로 표면화된다 — 이것이 "리허설" 의 기계적 본체다.
- **워치리스트는 검증된 사실만**: Three.js 역사에서 제거·이전된 API
  (예: 레거시 ``Geometry``·``Face3``·``sRGBEncoding``)를 워치리스트로 둔다.
  각 항목은 *현 벤더 빌드의 export 에 실재하지 않음* 을 테스트가 강제하므로
  (``_watchlist_absent_from_build``), 추측성 항목이 섞일 수 없다. 권위 있는
  마이그레이션 근거는 항상 공식 ``three.js/MIGRATION.md`` 이며, 본 워치리스트는
  그 일부를 기계 점검 가능하게 굳힌 것이다(정직성).
- **자문이지 집행 아님**: 본 모듈은 *판정*할 뿐 HTML 을 수정하거나 빌드를
  바꾸지 않는다(부수효과 0). 사람/CI 가 실제 업그레이드를 집행한다.

무작위성 0 · 결정적 · 기존 파일 무수정 순수 추가.

CLI:
    python -m simulation.threejs_upgrade_audit --status     # 리포 현 상태 감사
    python -m simulation.threejs_upgrade_audit --watchlist  # 워치리스트 출력
    python -m simulation.threejs_upgrade_audit --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- 감사 대상 경로(리포 상대) ---------------------------------------------
SIMULATOR_HTML = "swarm_3d_simulator.html"
VENDOR_MODULE = "vendor/three/three.module.js"

# --- 감사 판정 -------------------------------------------------------------
VERDICT_GREEN = "GREEN"    # 사라진 심볼 0 · 워치 적중 0 — 리허설 통과
VERDICT_REVIEW = "REVIEW"  # 워치리스트 심볼 사용 — 사람 확인 필요
VERDICT_BREAK = "BREAK"    # 쓰는 심볼이 빌드 export 에 없음 — 깨짐 확정

# --- 파싱 정규식(결정적) ---------------------------------------------------
# REVISION = '162'  (작은/큰따옴표 모두 허용). \b 로 APP_REVISION 등 오매칭 방지.
_REVISION = re.compile(r"\bREVISION\s*=\s*['\"]([0-9]+)['\"]")
# export { A, B, C };  — 번들된 단일 파일 three.module.js 의 집계/재export 블록을
# 통째로 캡처(분할 빌드 형식은 대상 외). 재export(`{ X } from './m'`)도 X 는
# 유효 export 이므로 수집이 맞다.
_EXPORT_BLOCK = re.compile(r"export\s*\{([^}]*)\}")
# THREE.<Symbol> — 숫자·$ 포함(Vector3·Matrix4·FogExp2 등). $ 는 _IDENT 와 대칭.
_THREE_USE = re.compile(r"\bTHREE\.([A-Za-z_$][A-Za-z0-9_$]*)")
# three/addons/... 임포트 경로(따옴표 짝 일치 — 역참조)
_ADDON_USE = re.compile(r"(['\"])(three/addons/[A-Za-z0-9_./-]+)\1")
# 유효 JS 식별자(export 항목 필터)
_IDENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
# JS 주석 제거용 — 주석 안의 THREE.* 가 사용으로 오집계되는 것을 막는다.
# 라인 주석은 `://`(http·ws·file 등 URL) 오인을 피하려 앞 `:` 를 룩비하인드로 배제.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"(?<!:)//[^\n]*")


def detect_revision(module_source: str) -> str | None:
    """벤더 빌드 소스에서 Three.js REVISION 문자열을 추출한다.

    찾지 못하면 None(빌드 형식 불명 — 감사가 이를 표면화한다).
    """
    match = _REVISION.search(module_source)
    return match.group(1) if match else None


def parse_exports(module_source: str) -> frozenset[str]:
    """``three.module.js`` 의 ``export { ... }`` 블록에서 export 이름을 파싱한다.

    여러 블록이 있으면 모두 합친다. 쉼표로 나누고 공백 제거 후 유효 식별자만
    취한다(``as`` 별칭·빈 토큰은 보수적으로 제외).
    """
    names: set[str] = set()
    for block in _EXPORT_BLOCK.findall(module_source):
        for raw in block.split(","):
            token = raw.strip()
            if not token:
                continue
            # `X as Y` 형태는 노출 이름(Y)을 취한다.
            if " as " in token:
                token = token.split(" as ")[-1].strip()
            if _IDENT.match(token):
                names.add(token)
    return frozenset(names)


def parse_used_symbols(html_source: str) -> frozenset[str]:
    """시뮬레이터 HTML 에서 쓰이는 고유 ``THREE.<심볼>`` 이름을 파싱한다.

    JS 주석(``//``·``/* */``) 안의 ``THREE.*`` 는 *실제 사용이 아니므로* 먼저
    제거한다 — 마이그레이션 메모가 오탐(거짓 REVIEW/BREAK)을 일으키는 것을
    방지한다. 문자열 리터럴 내부는 범위 외(자문 도구 한도, 실 HTML 무해).
    """
    stripped = _BLOCK_COMMENT.sub(" ", html_source)
    stripped = _LINE_COMMENT.sub(" ", stripped)
    return frozenset(_THREE_USE.findall(stripped))


def parse_addon_imports(html_source: str) -> frozenset[str]:
    """시뮬레이터 HTML 에서 임포트하는 ``three/addons/...`` 경로를 파싱한다."""
    return frozenset(m.group(2) for m in _ADDON_USE.finditer(html_source))


@dataclass(frozen=True)
class WatchEntry:
    """Three.js 역사에서 제거·이전된 API 한 건(불변, 자문용).

    Attributes:
        symbol: 사라진 ``THREE.<심볼>`` 이름.
        change: 변경 성격(``removed``·``moved_to_addons``·``renamed``).
        replacement: 권장 대체.
        note: 사람이 읽는 짧은 근거.
    """

    symbol: str
    change: str
    replacement: str
    note: str


# 워치리스트 — *현 벤더 빌드(r162)의 export 에 실재하지 않는* 심볼만.
# 테스트(`_watchlist_absent_from_build`)가 각 항목이 정말 export 에 없음을
# 강제하므로, 빌드와 어긋난 추측 항목은 들어올 수 없다. 권위 근거는 공식
# three.js/MIGRATION.md. 시뮬레이터가 이 중 하나라도 쓰면 REVIEW 로 격상한다.
DEFAULT_WATCHLIST: tuple[WatchEntry, ...] = (
    WatchEntry(
        "Geometry", "removed", "BufferGeometry",
        "레거시 Geometry 는 BufferGeometry 로 일원화되어 제거됨",
    ),
    WatchEntry(
        "Face3", "removed", "BufferGeometry index/attributes",
        "Face3 는 레거시 Geometry 와 함께 제거됨",
    ),
    WatchEntry(
        "Font", "moved_to_addons", "three/addons/loaders/FontLoader.js",
        "Font/FontLoader 는 addons(examples) 로 이전됨",
    ),
    WatchEntry(
        "sRGBEncoding", "renamed", "SRGBColorSpace (texture.colorSpace)",
        "encoding 상수 체계가 ColorSpace 로 대체됨",
    ),
    WatchEntry(
        "LinearEncoding", "renamed", "LinearSRGBColorSpace / NoColorSpace",
        "encoding 상수 체계가 ColorSpace 로 대체됨",
    ),
    WatchEntry(
        "VertexColors", "removed", "Material.vertexColors = true",
        "VertexColors 상수는 불리언 플래그로 대체되어 제거됨",
    ),
)


@dataclass(frozen=True)
class UpgradeAuditReport:
    """업그레이드 리허설 감사 결과(불변)."""

    revision: str | None
    used_symbols: tuple[str, ...]      # 정렬된 고유 THREE.* 사용
    present: tuple[str, ...]           # 빌드 export 로 뒷받침되는 심볼
    missing: tuple[str, ...]           # 쓰지만 export 에 없음 — 깨짐
    addon_imports: tuple[str, ...]     # three/addons/* 임포트
    watch_hits: tuple[str, ...]        # 워치리스트와 겹치는 사용 심볼
    verdict: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_clean(self) -> bool:
        """업그레이드 리허설을 추가 조치 없이 통과하는가."""
        return self.verdict == VERDICT_GREEN

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        rev = f"r{self.revision}" if self.revision else "r?(미상)"
        return f"{self.verdict} (Three.js {rev}): {'; '.join(self.reasons)}"


def _verdict_for(missing: tuple[str, ...], watch_hits: tuple[str, ...]) -> str:
    """판정 핵심 규칙(우선순위: 깨짐 > 검토 > 통과)."""
    if missing:
        return VERDICT_BREAK
    if watch_hits:
        return VERDICT_REVIEW
    return VERDICT_GREEN


def audit(
    html_source: str,
    module_source: str,
    watchlist: tuple[WatchEntry, ...] = DEFAULT_WATCHLIST,
) -> UpgradeAuditReport:
    """시뮬레이터 HTML 을 벤더 Three.js 빌드에 대해 결정적으로 감사한다.

    1. 빌드 export 와 HTML 사용 심볼을 파싱.
    2. 사용 심볼 중 export 에 없는 것 → ``missing``(깨짐 확정).
    3. 사용 심볼 중 워치리스트와 겹치는 것 → ``watch_hits``(사람 확인).
    4. 판정: missing 있으면 BREAK, 아니면 watch_hits 있으면 REVIEW, 아니면 GREEN.
    """
    revision = detect_revision(module_source)
    exports = parse_exports(module_source)
    used = parse_used_symbols(html_source)
    addons = parse_addon_imports(html_source)
    watch_names = {entry.symbol for entry in watchlist}

    present = tuple(sorted(s for s in used if s in exports))
    missing = tuple(sorted(s for s in used if s not in exports))
    watch_hits = tuple(sorted(s for s in used if s in watch_names))

    # 빌드 export 를 하나도 파싱 못 하면(벤더 빌드 부재/형식 오류) 감사 불가 →
    # 절대 GREEN 으로 가지 않는다(정직성: 감사 안 한 것을 통과로 포장 금지).
    if not exports:
        verdict = VERDICT_BREAK
    else:
        verdict = _verdict_for(missing, watch_hits)

    reasons: list[str] = []
    if not exports:
        reasons.append("빌드 export 파싱 실패 또는 벤더 빌드 부재 — 감사 불가(BREAK)")
    reasons.append(
        f"사용 심볼 {len(used)}개 중 {len(present)}개 빌드 export 로 확인"
    )
    if missing:
        reasons.append(f"빌드에 없는 심볼 {len(missing)}개: {', '.join(missing)}")
    if watch_hits:
        reasons.append(
            f"워치리스트 적중 {len(watch_hits)}개: {', '.join(watch_hits)}"
        )
    if verdict == VERDICT_GREEN:
        reasons.append("모든 사용 심볼이 빌드와 일치 — 리허설 통과")

    return UpgradeAuditReport(
        revision=revision,
        used_symbols=tuple(sorted(used)),
        present=present,
        missing=missing,
        addon_imports=tuple(sorted(addons)),
        watch_hits=watch_hits,
        verdict=verdict,
        reasons=tuple(reasons),
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def audit_repo(repo_root: str | Path | None = None) -> UpgradeAuditReport:
    """리포의 *현 실제 파일* 로 감사를 수행한다(정직 공시).

    시뮬레이터 HTML 또는 벤더 빌드가 없으면 *감사 불가* → ``BREAK`` 로
    표면화한다(없는 파일을 조용히 GREEN 으로 통과시키지 않는다 — 정직성).
    """
    root = Path(repo_root) if repo_root is not None else _repo_root()
    html_path = root / SIMULATOR_HTML
    module_path = root / VENDOR_MODULE
    absent = [p.name for p in (html_path, module_path) if not p.is_file()]
    if absent:
        return UpgradeAuditReport(
            revision=None,
            used_symbols=(),
            present=(),
            missing=(),
            addon_imports=(),
            watch_hits=(),
            verdict=VERDICT_BREAK,
            reasons=(f"감사 대상 파일 부재: {', '.join(absent)} — 감사 불가",),
        )
    html_source = html_path.read_text(encoding="utf-8")
    module_source = module_path.read_text(encoding="utf-8")
    return audit(html_source, module_source)


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-threejs-upgrade-audit",
        "version": "1.0",
        "simulator_html": SIMULATOR_HTML,
        "vendor_module": VENDOR_MODULE,
        "verdicts": [VERDICT_GREEN, VERDICT_REVIEW, VERDICT_BREAK],
        "watchlist": [
            {
                "symbol": e.symbol,
                "change": e.change,
                "replacement": e.replacement,
                "note": e.note,
            }
            for e in DEFAULT_WATCHLIST
        ],
    }


def _cmd_status() -> None:
    report = audit_repo()
    print("Three.js 업그레이드 리허설 감사(리포 현 상태):")
    print(f"  벤더 빌드 REVISION : {report.revision or '미상'}")
    print(f"  사용 THREE.* 심볼  : {len(report.used_symbols)}개")
    print(f"  빌드 export 로 확인 : {len(report.present)}개")
    print(f"  addons 임포트      : {', '.join(report.addon_imports) or '없음'}")
    if report.missing:
        print(f"  ⚠ 빌드에 없음      : {', '.join(report.missing)}")
    if report.watch_hits:
        print(f"  ⚠ 워치 적중        : {', '.join(report.watch_hits)}")
    print(f"\n판정: {report.summary()}")


def _cmd_watchlist() -> None:
    print("Three.js 제거·이전 API 워치리스트(현 빌드에 부재):")
    print(f"{'SYMBOL':<18}{'CHANGE':<18}REPLACEMENT")
    for entry in DEFAULT_WATCHLIST:
        print(f"{entry.symbol:<18}{entry.change:<18}{entry.replacement}")
    print("\n권위 근거: three.js 공식 MIGRATION.md")


_KNOWN_FLAGS = ("--status", "--watchlist", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(policy_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--watchlist" in args:
        _cmd_watchlist()
        return 0
    _cmd_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
