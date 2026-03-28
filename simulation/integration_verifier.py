"""
시스템 통합 검증
===============
모듈 간 의존성 검증 + 인터페이스 적합성 + 회귀 감지.

사용법:
    iv = IntegrationVerifier()
    iv.register_module("apf", provides=["collision_avoidance"], requires=["drone_positions"])
    iv.register_module("controller", provides=["drone_positions"], requires=[])
    report = iv.verify()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleSpec:
    """모듈 사양"""
    name: str
    provides: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class VerificationResult:
    """검증 결과"""
    passed: bool
    missing_deps: list[tuple[str, str]]  # (module, missing_dep)
    circular_deps: list[list[str]]
    unused_provides: list[tuple[str, str]]  # (module, unused_interface)
    score: float  # 0~100


class IntegrationVerifier:
    """시스템 통합 검증."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleSpec] = {}
        self._test_results: dict[str, bool] = {}

    def register_module(
        self, name: str,
        provides: list[str] | None = None,
        requires: list[str] | None = None,
        version: str = "1.0",
    ) -> None:
        self._modules[name] = ModuleSpec(
            name=name, provides=provides or [],
            requires=requires or [], version=version,
        )

    def _all_provides(self) -> dict[str, str]:
        """인터페이스 → 제공 모듈 매핑"""
        mapping: dict[str, str] = {}
        for mod in self._modules.values():
            for iface in mod.provides:
                mapping[iface] = mod.name
        return mapping

    def _find_missing_deps(self) -> list[tuple[str, str]]:
        provides = set(self._all_provides().keys())
        missing = []
        for mod in self._modules.values():
            for req in mod.requires:
                if req not in provides:
                    missing.append((mod.name, req))
        return missing

    def _find_circular_deps(self) -> list[list[str]]:
        """순환 의존성 탐지"""
        provides_map = self._all_provides()
        cycles = []

        for mod in self._modules.values():
            visited = set()
            stack = [mod.name]
            path = [mod.name]

            while stack:
                current = stack[-1]
                current_mod = self._modules.get(current)
                if not current_mod:
                    stack.pop()
                    if path:
                        path.pop()
                    continue

                found_next = False
                for req in current_mod.requires:
                    provider = provides_map.get(req)
                    if provider and provider not in visited:
                        if provider == mod.name:
                            cycles.append(list(path) + [provider])
                        else:
                            visited.add(provider)
                            stack.append(provider)
                            path.append(provider)
                            found_next = True
                            break

                if not found_next:
                    stack.pop()
                    if path:
                        path.pop()

        return cycles

    def _find_unused(self) -> list[tuple[str, str]]:
        all_requires = set()
        for mod in self._modules.values():
            all_requires.update(mod.requires)

        unused = []
        for mod in self._modules.values():
            for iface in mod.provides:
                if iface not in all_requires:
                    unused.append((mod.name, iface))
        return unused

    def verify(self) -> VerificationResult:
        missing = self._find_missing_deps()
        circular = self._find_circular_deps()
        unused = self._find_unused()

        score = 100.0
        score -= len(missing) * 15
        score -= len(circular) * 20
        score -= len(unused) * 2
        score = max(0, min(100, score))

        passed = len(missing) == 0 and len(circular) == 0

        return VerificationResult(
            passed=passed, missing_deps=missing,
            circular_deps=circular, unused_provides=unused,
            score=round(score, 1),
        )

    def record_test(self, module: str, passed: bool) -> None:
        self._test_results[module] = passed

    def regression_check(self) -> list[str]:
        """테스트 실패 모듈"""
        return [m for m, p in self._test_results.items() if not p]

    def dependency_graph(self) -> dict[str, list[str]]:
        provides_map = self._all_provides()
        graph: dict[str, list[str]] = {}
        for mod in self._modules.values():
            deps = []
            for req in mod.requires:
                provider = provides_map.get(req)
                if provider:
                    deps.append(provider)
            graph[mod.name] = deps
        return graph

    def summary(self) -> dict[str, Any]:
        result = self.verify()
        return {
            "modules": len(self._modules),
            "passed": result.passed,
            "score": result.score,
            "missing_deps": len(result.missing_deps),
            "regressions": len(self.regression_check()),
        }
