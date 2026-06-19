"""ODYSSEY Phase 483 — Three.js 업그레이드 리허설 감사 테스트.

핵심 계약 검증: REVISION 파싱·export/사용 심볼 파싱·판정 우선순위
(BREAK > REVIEW > GREEN)·워치리스트가 현 벤더 빌드와 어긋나지 않음
(추측 항목 차단)·결정론·매니페스트 JSON 직렬화·리포 현 상태(GREEN) 정직성.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simulation.threejs_upgrade_audit import (
    DEFAULT_WATCHLIST,
    SIMULATOR_HTML,
    VENDOR_MODULE,
    VERDICT_BREAK,
    VERDICT_GREEN,
    VERDICT_REVIEW,
    UpgradeAuditReport,
    WatchEntry,
    audit,
    audit_repo,
    detect_revision,
    main,
    parse_addon_imports,
    parse_exports,
    parse_used_symbols,
    policy_manifest,
)

_GEOMETRY_WATCH = (WatchEntry("Geometry", "removed", "BufferGeometry", "테스트용"),)

REPO_ROOT = Path(__file__).resolve().parent.parent

# 결정적 미니 빌드/HTML 픽스처(파서·판정 단위 검증용).
_MINI_MODULE = (
    "class WebGLRenderer {}\n"
    "const REVISION = '162';\n"
    "export { BufferGeometry, Mesh, MeshBasicMaterial, Vector3, "
    "WebGLRenderer, Group as Grp };\n"
)
_MINI_HTML = """
<script type="importmap">{ "imports": { "three": "./vendor/three/three.module.js" } }</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const m = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial());
const v = new THREE.Vector3(1, 2, 3);
</script>
"""


# --- 파싱 --------------------------------------------------------------------
def test_detect_revision_extracts_number():
    assert detect_revision(_MINI_MODULE) == "162"


def test_detect_revision_missing_returns_none():
    assert detect_revision("no revision here") is None


def test_detect_revision_double_quotes():
    assert detect_revision('REVISION = "170";') == "170"


def test_parse_exports_collects_names():
    exports = parse_exports(_MINI_MODULE)
    assert "BufferGeometry" in exports
    assert "Mesh" in exports
    assert "Vector3" in exports


def test_parse_exports_resolves_alias_to_exposed_name():
    exports = parse_exports(_MINI_MODULE)
    assert "Grp" in exports        # `Group as Grp` → 노출명 Grp
    assert "Group" not in exports


def test_parse_exports_empty_when_no_block():
    assert parse_exports("const x = 1;") == frozenset()


def test_parse_used_symbols_includes_digit_names():
    used = parse_used_symbols(_MINI_HTML)
    assert "Mesh" in used
    assert "BufferGeometry" in used
    assert "Vector3" in used        # 숫자 포함 심볼 캡처


def test_parse_addon_imports():
    addons = parse_addon_imports(_MINI_HTML)
    assert "three/addons/controls/OrbitControls.js" in addons


# --- 판정 우선순위 -----------------------------------------------------------
def test_audit_green_when_all_present():
    report = audit(_MINI_HTML, _MINI_MODULE, watchlist=())
    assert report.verdict == VERDICT_GREEN
    assert report.is_clean()
    assert report.missing == ()
    assert "Mesh" in report.present


def test_audit_break_when_symbol_absent_from_build():
    # 빌드 export 에 Vector3 가 없는 축소 빌드 → 사용 심볼이 깨짐.
    stripped = "const REVISION = '162';\nexport { Mesh, BufferGeometry, MeshBasicMaterial };\n"
    report = audit(_MINI_HTML, stripped, watchlist=())
    assert report.verdict == VERDICT_BREAK
    assert "Vector3" in report.missing
    assert not report.is_clean()


def test_audit_review_when_watchlist_symbol_used():
    html = "<script>const g = new THREE.Geometry();</script>"
    # Geometry 를 일부러 export 에 넣어 BREAK 가 아닌 REVIEW 경로만 격리.
    module = "const REVISION='162';\nexport { Geometry };\n"
    report = audit(html, module, watchlist=_GEOMETRY_WATCH)
    assert report.verdict == VERDICT_REVIEW
    assert "Geometry" in report.watch_hits


def test_break_outranks_review():
    # 워치 심볼(Geometry)을 쓰되 빌드에 없음 → BREAK 가 REVIEW 보다 우선.
    html = "<script>new THREE.Geometry(); new THREE.Mesh();</script>"
    module = "const REVISION='162';\nexport { Mesh };\n"
    report = audit(html, module, watchlist=_GEOMETRY_WATCH)
    assert report.verdict == VERDICT_BREAK
    assert "Geometry" in report.missing


def test_empty_build_is_break_never_green():
    # 빌드 export 0개(벤더 빌드 부재/형식 오류) → 감사 불가, 절대 GREEN 아님.
    report = audit(_MINI_HTML, "", watchlist=())
    assert report.verdict == VERDICT_BREAK
    assert not report.is_clean()


def test_comment_three_usage_ignored():
    # 주석 안의 THREE.Geometry 는 실제 사용이 아니므로 워치 적중 0(거짓 REVIEW 방지).
    html = (
        "<script>\n"
        "// THREE.Geometry was removed — use THREE.BufferGeometry instead\n"
        "/* legacy: THREE.Face3 */\n"
        "const m = new THREE.Mesh();\n"
        "const url = 'https://example.com/three';\n"
        "</script>"
    )
    used = parse_used_symbols(html)
    assert "Mesh" in used
    assert "Geometry" not in used        # 라인 주석 무시
    assert "Face3" not in used           # 블록 주석 무시


def test_line_comment_strip_preserves_url_lines():
    # `://` 룩비하인드 배제로 URL 뒤 같은 줄의 코드가 잘리지 않는다.
    html = "<script>fetch('http://x'); new THREE.Mesh();</script>"
    assert "Mesh" in parse_used_symbols(html)


# --- 워치리스트 정직성 -------------------------------------------------------
def test_watchlist_symbols_absent_from_real_build():
    """워치리스트 항목은 *현 벤더 빌드 export 에 실재하지 않아야* 한다.

    이 테스트가 추측성(실제로는 빌드에 있는) 항목이 워치리스트에 끼는 것을
    막는다 — 워치리스트와 빌드의 일치를 강제하는 정직성 게이트.
    """
    module_source = (REPO_ROOT / VENDOR_MODULE).read_text(encoding="utf-8")
    exports = parse_exports(module_source)
    assert exports, "벤더 빌드 export 파싱 실패"
    for entry in DEFAULT_WATCHLIST:
        assert entry.symbol not in exports, (
            f"워치 심볼 {entry.symbol} 이 현 빌드 export 에 실재함 — "
            f"제거된 API 가 아니므로 워치리스트에서 빼야 함"
        )


def test_watchlist_entries_well_formed():
    for entry in DEFAULT_WATCHLIST:
        assert isinstance(entry, WatchEntry)
        assert entry.symbol and entry.replacement and entry.note
        assert entry.change in {"removed", "moved_to_addons", "renamed"}


# --- 결정론·매니페스트 -------------------------------------------------------
def test_audit_deterministic():
    a = audit(_MINI_HTML, _MINI_MODULE)
    b = audit(_MINI_HTML, _MINI_MODULE)
    assert a == b


def test_manifest_json_serializable():
    manifest = policy_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert "watchlist" in manifest
    assert json.loads(dumped)["vendor_module"] == VENDOR_MODULE


# --- 리포 현 상태 정직성 -----------------------------------------------------
def test_repo_audit_is_green():
    """현 리포(시뮬 HTML + 벤더 r162)는 리허설을 통과(GREEN)해야 한다.

    시뮬레이터가 쓰는 모든 THREE.* 심볼이 벤더 빌드 export 로 뒷받침됨을
    실파일로 검증 — 회귀 시 즉시 BREAK/REVIEW 로 표면화된다.
    """
    report = audit_repo()
    assert report.revision == "162"
    assert report.verdict == VERDICT_GREEN, report.summary()
    assert report.missing == ()
    assert "three/addons/controls/OrbitControls.js" in report.addon_imports
    assert len(report.used_symbols) > 20      # 풍부한 API 표면 사용 확인


def test_repo_audit_uses_real_paths():
    assert (REPO_ROOT / SIMULATOR_HTML).is_file()
    assert (REPO_ROOT / VENDOR_MODULE).is_file()


def test_audit_repo_missing_files_is_not_clean(tmp_path):
    """감사 대상 파일이 없으면 *조용히 GREEN* 이 아니라 BREAK 여야 한다.

    "감사 안 한 것을 통과로 포장하지 않는다" 는 정직성 계약의 기계 검증.
    """
    report = audit_repo(tmp_path)
    assert report.verdict == VERDICT_BREAK
    assert not report.is_clean()
    assert any("부재" in r for r in report.reasons)


# --- CLI -------------------------------------------------------------------
def test_cli_manifest_exit_zero(capsys):
    code = main(["--manifest"])
    assert code == 0
    out = capsys.readouterr().out
    assert json.loads(out)["schema"] == "sdacs-threejs-upgrade-audit"


def test_cli_unknown_arg_exit_two():
    assert main(["--bogus"]) == 2


def test_cli_status_and_watchlist_exit_zero(capsys):
    assert main(["--watchlist"]) == 0
    assert main(["--status"]) == 0
