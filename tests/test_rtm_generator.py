"""GENESIS Phase 306 -- RTM 자동 생성기 테스트.

simulation/rtm_generator.py의 5계층 안전망 RTM 기능을 검증합니다.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from simulation.rtm_generator import (
    COVERED,
    LAYER_NAMES,
    MODULE_MAP,
    PARTIAL,
    REQUIREMENTS,
    STATUS_LABELS,
    UNCOVERED,
    LayerCoverage,
    Requirement,
    RTMReport,
    TraceabilityLink,
    filter_by_layer,
    generate_rtm,
    get_gaps,
)

# ---------------------------------------------------------------------------
# TestRequirementDataclass
# ---------------------------------------------------------------------------


class TestRequirementDataclass:
    def test_frozen(self) -> None:
        req = Requirement("R1", "desc", 1, "HIGH", "SRS", "unit_test")
        with pytest.raises(AttributeError):
            req.id = "R2"  # type: ignore[misc]

    def test_valid_construction(self) -> None:
        req = Requirement("R1", "desc", 3, "CRITICAL", "SRS-1", "analysis")
        assert req.id == "R1"
        assert req.layer == 3
        assert req.priority == "CRITICAL"

    def test_invalid_layer_raises(self) -> None:
        with pytest.raises(ValueError, match="layer must be 1-5"):
            Requirement("R1", "desc", 0, "HIGH", "SRS", "unit_test")

    def test_invalid_layer_6_raises(self) -> None:
        with pytest.raises(ValueError, match="layer must be 1-5"):
            Requirement("R1", "desc", 6, "HIGH", "SRS", "unit_test")

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid priority"):
            Requirement("R1", "desc", 1, "URGENT", "SRS", "unit_test")

    def test_as_dict(self) -> None:
        req = Requirement("R1", "d", 2, "LOW", "SRS-2", "integration_test")
        d = req.as_dict()
        assert d["id"] == "R1"
        assert d["layer"] == 2
        assert d["priority"] == "LOW"
        assert d["verification_method"] == "integration_test"


# ---------------------------------------------------------------------------
# TestTraceabilityLinkDataclass
# ---------------------------------------------------------------------------


class TestTraceabilityLinkDataclass:
    def test_frozen(self) -> None:
        link = TraceabilityLink("R1", "mod.py", "test.py", COVERED)
        with pytest.raises(AttributeError):
            link.status = UNCOVERED  # type: ignore[misc]

    def test_valid_statuses(self) -> None:
        for status in (COVERED, PARTIAL, UNCOVERED):
            link = TraceabilityLink("R1", "m.py", "t.py", status)
            assert link.status == status

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid status"):
            TraceabilityLink("R1", "m.py", "t.py", "UNKNOWN")

    def test_as_dict(self) -> None:
        link = TraceabilityLink("R1", "a.py", "b.py", PARTIAL)
        d = link.as_dict()
        assert d["req_id"] == "R1"
        assert d["status"] == PARTIAL


# ---------------------------------------------------------------------------
# TestLayerCoverageDataclass
# ---------------------------------------------------------------------------


class TestLayerCoverageDataclass:
    def test_frozen(self) -> None:
        lc = LayerCoverage(1, "APF", 5, 3, 1, 1)
        with pytest.raises(AttributeError):
            lc.covered = 4  # type: ignore[misc]

    def test_coverage_pct(self) -> None:
        lc = LayerCoverage(1, "APF", 10, 7, 2, 1)
        assert lc.coverage_pct == 70.0

    def test_coverage_pct_zero_total(self) -> None:
        lc = LayerCoverage(1, "APF", 0, 0, 0, 0)
        assert lc.coverage_pct == 0.0

    def test_as_dict_rounds(self) -> None:
        lc = LayerCoverage(2, "CPA", 3, 1, 1, 1)
        d = lc.as_dict()
        assert d["coverage_pct"] == 33.3


# ---------------------------------------------------------------------------
# TestRTMReportDataclass
# ---------------------------------------------------------------------------


class TestRTMReportDataclass:
    def test_frozen(self) -> None:
        report = RTMReport((), (), (), 0, 0, 0, 0)
        with pytest.raises(AttributeError):
            report.total_covered = 1  # type: ignore[misc]

    def test_overall_coverage_pct(self) -> None:
        report = RTMReport((), (), (), 20, 15, 3, 2)
        assert report.overall_coverage_pct == 75.0

    def test_overall_coverage_pct_zero(self) -> None:
        report = RTMReport((), (), (), 0, 0, 0, 0)
        assert report.overall_coverage_pct == 0.0

    def test_as_dict_structure(self) -> None:
        report = RTMReport((), (), (), 5, 3, 1, 1)
        d = report.as_dict()
        assert "total_requirements" in d
        assert "overall_coverage_pct" in d
        assert "layer_coverage" in d
        assert "requirements" in d
        assert "links" in d


# ---------------------------------------------------------------------------
# TestRequirementsRegistry
# ---------------------------------------------------------------------------


class TestRequirementsRegistry:
    def test_requirements_is_tuple(self) -> None:
        assert isinstance(REQUIREMENTS, tuple)

    def test_nonempty(self) -> None:
        assert len(REQUIREMENTS) >= 20

    def test_unique_ids(self) -> None:
        ids = [r.id for r in REQUIREMENTS]
        assert len(ids) == len(set(ids))

    def test_all_five_layers_have_requirements(self) -> None:
        layers_present = {r.layer for r in REQUIREMENTS}
        assert layers_present == {1, 2, 3, 4, 5}

    @pytest.mark.parametrize("layer", [1, 2, 3, 4, 5])
    def test_each_layer_has_at_least_three_requirements(
        self, layer: int,
    ) -> None:
        count = sum(1 for r in REQUIREMENTS if r.layer == layer)
        assert count >= 3, f"Layer {layer} has only {count} requirements"

    def test_all_requirements_frozen(self) -> None:
        for req in REQUIREMENTS:
            with pytest.raises(AttributeError):
                req.id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestModuleMap
# ---------------------------------------------------------------------------


class TestModuleMap:
    def test_module_map_covers_all_requirements(self) -> None:
        for req in REQUIREMENTS:
            assert req.id in MODULE_MAP, f"{req.id} missing from MODULE_MAP"

    def test_module_map_is_mapping_proxy(self) -> None:
        with pytest.raises(TypeError):
            MODULE_MAP["NEW"] = ("a.py", "b.py")  # type: ignore[index]


# ---------------------------------------------------------------------------
# TestHonestyBinding (with temp directories)
# ---------------------------------------------------------------------------


class TestHonestyBinding:
    def test_uncovered_when_module_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = generate_rtm(repo_root=pathlib.Path(tmpdir))
            for link in report.links:
                assert link.status == UNCOVERED

    def test_partial_when_module_exists_no_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            mod_dir = root / "simulation" / "apf_engine"
            mod_dir.mkdir(parents=True)
            (mod_dir / "apf.py").write_text("# stub")
            report = generate_rtm(repo_root=root)
            l1_links = [
                ln for ln in report.links if ln.req_id.startswith("REQ-L1")
            ]
            apf_links = [
                ln for ln in l1_links
                if ln.module_path == "simulation/apf_engine/apf.py"
            ]
            for ln in apf_links:
                assert ln.status == PARTIAL

    def test_covered_when_both_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            (root / "simulation" / "apf_engine").mkdir(parents=True)
            (root / "tests").mkdir(parents=True)
            (root / "simulation" / "apf_engine" / "apf.py").write_text("# s")
            (root / "tests" / "test_apf.py").write_text("# s")
            report = generate_rtm(repo_root=root)
            apf_links = [
                ln for ln in report.links
                if ln.module_path == "simulation/apf_engine/apf.py"
            ]
            for ln in apf_links:
                assert ln.status == COVERED


# ---------------------------------------------------------------------------
# TestGenerateRTM
# ---------------------------------------------------------------------------


class TestGenerateRTM:
    def test_returns_rtm_report(self) -> None:
        report = generate_rtm()
        assert isinstance(report, RTMReport)

    def test_total_requirements_matches(self) -> None:
        report = generate_rtm()
        assert report.total_requirements == len(REQUIREMENTS)

    def test_counts_add_up(self) -> None:
        report = generate_rtm()
        total = report.total_covered + report.total_partial + report.total_uncovered
        assert total == report.total_requirements

    def test_layer_coverage_count(self) -> None:
        report = generate_rtm()
        assert len(report.layer_coverage) == 5

    def test_layer_coverage_totals_match(self) -> None:
        report = generate_rtm()
        layer_total = sum(lc.total for lc in report.layer_coverage)
        assert layer_total == report.total_requirements

    def test_each_layer_counts_add_up(self) -> None:
        report = generate_rtm()
        for lc in report.layer_coverage:
            assert lc.covered + lc.partial + lc.uncovered == lc.total


# ---------------------------------------------------------------------------
# TestGetGaps
# ---------------------------------------------------------------------------


class TestGetGaps:
    def test_gaps_exclude_covered(self) -> None:
        report = generate_rtm()
        gaps = get_gaps(report)
        for gap in gaps:
            assert gap.status != COVERED

    def test_all_uncovered_in_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = generate_rtm(repo_root=pathlib.Path(tmpdir))
            gaps = get_gaps(report)
            assert len(gaps) == report.total_requirements


# ---------------------------------------------------------------------------
# TestFilterByLayer
# ---------------------------------------------------------------------------


class TestFilterByLayer:
    def test_filter_returns_correct_layer(self) -> None:
        report = generate_rtm()
        l1_links = filter_by_layer(report, 1)
        l1_req_ids = {r.id for r in REQUIREMENTS if r.layer == 1}
        for ln in l1_links:
            assert ln.req_id in l1_req_ids

    def test_filter_count_matches(self) -> None:
        report = generate_rtm()
        for layer in range(1, 6):
            expected = sum(1 for r in REQUIREMENTS if r.layer == layer)
            actual = len(filter_by_layer(report, layer))
            assert actual == expected


# ---------------------------------------------------------------------------
# TestJSONRoundTrip
# ---------------------------------------------------------------------------


class TestJSONRoundTrip:
    def test_report_json_serializable(self) -> None:
        report = generate_rtm()
        text = json.dumps(report.as_dict(), ensure_ascii=False)
        parsed = json.loads(text)
        assert parsed["total_requirements"] == report.total_requirements

    def test_requirement_json_roundtrip(self) -> None:
        req = Requirement("R1", "desc", 1, "HIGH", "SRS", "unit_test")
        text = json.dumps(req.as_dict())
        parsed = json.loads(text)
        assert parsed["id"] == "R1"
        assert parsed["layer"] == 1

    def test_link_json_roundtrip(self) -> None:
        link = TraceabilityLink("R1", "m.py", "t.py", COVERED)
        text = json.dumps(link.as_dict())
        parsed = json.loads(text)
        assert parsed["status"] == COVERED

    def test_full_report_json_keys(self) -> None:
        report = generate_rtm()
        d = report.as_dict()
        expected_keys = {
            "total_requirements", "total_covered", "total_partial",
            "total_uncovered", "overall_coverage_pct",
            "layer_coverage", "requirements", "links",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# TestConstants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_layer_names_has_five(self) -> None:
        assert len(LAYER_NAMES) == 5

    def test_status_labels_has_three(self) -> None:
        assert len(STATUS_LABELS) == 3

    def test_layer_names_immutable(self) -> None:
        with pytest.raises(TypeError):
            LAYER_NAMES[6] = "New"  # type: ignore[index]

    def test_status_labels_immutable(self) -> None:
        with pytest.raises(TypeError):
            STATUS_LABELS["NEW"] = "val"  # type: ignore[index]


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "rtm_generator.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8",
            env=self.UTF8_ENV, timeout=30,
        )

    def test_report_exits_zero(self) -> None:
        result = self._run("--report")
        assert result.returncode == 0

    def test_report_contains_header(self) -> None:
        result = self._run("--report")
        assert "RTM" in result.stdout

    def test_report_json(self) -> None:
        result = self._run("--report", "--json")
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert "total_requirements" in parsed

    def test_layer_filter(self) -> None:
        result = self._run("--layer", "1")
        assert result.returncode == 0
        assert "REQ-L1" in result.stdout

    def test_layer_json(self) -> None:
        result = self._run("--layer", "3", "--json")
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list)
        assert all("req_id" in item for item in parsed)

    def test_gaps_exits_zero(self) -> None:
        result = self._run("--gaps")
        assert result.returncode == 0

    def test_gaps_json(self) -> None:
        result = self._run("--gaps", "--json")
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list)

    def test_no_args_shows_help(self) -> None:
        result = self._run()
        assert result.returncode != 0

    def test_invalid_layer_rejected(self) -> None:
        result = self._run("--layer", "9")
        assert result.returncode != 0
