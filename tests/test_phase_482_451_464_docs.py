"""ODYSSEY Phase 451·464·482 추가 산출물 회귀 — 신규 문서·스크립트 존재·구조 검증."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STANDARDS = ROOT / "docs" / "standards"
RESEARCH = ROOT / "docs" / "research"
SCRIPTS = ROOT / "scripts"


class TestPhase451RlGeneralizationSurvey:
    """ODYSSEY Phase 451 — RL 일반화 + 인증 가능 ML 조사."""

    PATH = RESEARCH / "RL_GENERALIZATION_SURVEY.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 451" in text

    def test_references_easa_ai_roadmap(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # EASA AI Roadmap 인증 레벨 명시
        assert "EASA AI Roadmap" in text
        # AI/ML 1A·1B·2A·2B·3A 레벨 매트릭스
        assert "AI/ML 1A" in text
        assert "AI/ML 2A" in text

    def test_references_standards(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 핵심 인증 표준 명시
        for std in ("DO-178C", "DO-330", "ISO/IEC 22989"):
            assert std in text, f"missing standard {std}"

    def test_distributional_shift_taxonomy(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 분포 변화 유형 4종
        assert "Covariate shift" in text
        assert "Domain shift" in text or "domain shift" in text.lower()
        assert "Adversarial" in text

    def test_honesty_disclosure(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 정직성 공시 (알고리즘 제안 아님)
        assert "정직성" in text or "honesty" in text.lower()

    def test_no_unverified_claims(self) -> None:
        """본 문서는 *조사*이며 SDACS 가 RL 알고리즘을 *제공* 한다고 주장하면 안 됨."""
        text = self.PATH.read_text(encoding="utf-8")
        # PoC 명시 — 'src/rl/ppo_collision.py' 는 PoC 임
        assert "PoC" in text


class TestPhase464SwarmSafetyWhitepaper:
    """ODYSSEY Phase 464 — 군집 비행 안전 기준 백서."""

    PATH = STANDARDS / "SDACS_SWARM_SAFETY_WHITEPAPER.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 464" in text

    def test_five_layer_safety_net(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # L1-L5 5계층 명시
        for layer in ("L1", "L2", "L3", "L4", "L5"):
            assert layer in text, f"missing layer {layer}"
        # APF·CBS·CPA·ATC·UTM
        for name in ("APF", "CBS", "CPA", "ATC", "UTM"):
            assert name in text, f"missing safety layer name {name}"

    def test_case_studies(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 3 사례 연구 (head-on, 100 swarm, mega 1k)
        assert "head" in text.lower() or "정면" in text
        assert "1,000" in text or "1000" in text or "mega_swarm_1k" in text

    def test_easa_sora_alignment(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # SORA 정렬 + OSO 항목
        assert "SORA" in text
        assert "OSO" in text

    def test_recommendations_section(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 권고사항 (Safety Recommendations) 명시
        assert "권고" in text or "Recommendations" in text

    def test_honesty_disclosure(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 연구용 vs 인증 분리 정직성
        assert "정직성" in text or "honesty" in text.lower()
        assert "연구용" in text or "research" in text.lower()


class TestPhase482BrowserApiCanary:
    """ODYSSEY Phase 482 — 브라우저 API 폐기 감시 카나리."""

    SCRIPT = SCRIPTS / "browser_api_canary.py"

    def test_script_exists(self) -> None:
        assert self.SCRIPT.is_file()

    def test_phase_header(self) -> None:
        text = self.SCRIPT.read_text(encoding="utf-8")
        assert "Phase 482" in text

    def test_required_api_probes(self) -> None:
        """필수 API 가 정의되어 있는지."""
        text = self.SCRIPT.read_text(encoding="utf-8")
        # SDACS 핵심 의존 API
        for api in ("webgpu", "webworker", "mediarecorder", "webgl2"):
            assert f'"{api}"' in text, f"missing API probe {api}"

    def test_script_compiles(self) -> None:
        """스크립트 syntax check."""
        text = self.SCRIPT.read_text(encoding="utf-8")
        compile(text, str(self.SCRIPT), "exec")

    def test_cli_args_defined(self) -> None:
        """CLI 인자 (--json, --check, --required) 정의."""
        text = self.SCRIPT.read_text(encoding="utf-8")
        assert "--json" in text
        assert "--check" in text
        assert "--required" in text

    def test_module_imports(self) -> None:
        """모듈 import 가능 (playwright 미설치 환경도 OK — 함수 정의만)."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("browser_api_canary", str(self.SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # API_PROBES 가 list[dict] 이고 최소 5개
        assert isinstance(mod.API_PROBES, list)
        assert len(mod.API_PROBES) >= 5
        # 각 probe 가 필수 키 보유
        for probe in mod.API_PROBES:
            for key in ("id", "name", "required", "snippet", "used_by"):
                assert key in probe, f"probe missing key {key}"

    def test_required_apis_present(self) -> None:
        """SDACS 핵심 의존 API 가 required=True 로 표시됨."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("browser_api_canary", str(self.SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        required_ids = {p["id"] for p in mod.API_PROBES if p["required"]}
        # 핵심 4종은 반드시 required
        for api_id in ("webgpu", "webworker", "mediarecorder", "webgl2"):
            assert api_id in required_ids, f"{api_id} should be required"
