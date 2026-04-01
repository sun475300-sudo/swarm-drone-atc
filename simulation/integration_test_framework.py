"""Phase 305: Integration Test Framework — E2E 통합 테스트 프레임워크.

다중 모듈 통합 시나리오, 자동 검증, 성능 프로파일링,
회귀 방지 및 리포트 생성.
"""

from __future__ import annotations
import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any


class IntegrationTestResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class IntegrationTest:
    name: str
    description: str
    test_fn: Callable
    tags: List[str] = field(default_factory=list)
    timeout_sec: float = 30.0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class IntegrationTestOutcome:
    name: str
    result: IntegrationTestResult
    duration_ms: float = 0.0
    message: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class TestSuiteReport:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    outcomes: List[IntegrationTestOutcome] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / max(self.total, 1) * 100


class IntegrationTestFramework:
    """E2E 통합 테스트 프레임워크.

    - 테스트 등록 및 의존성 관리
    - 자동 실행 및 결과 수집
    - 태그 기반 필터링
    - 리포트 생성
    """

    def __init__(self):
        self._tests: Dict[str, IntegrationTest] = {}
        self._results: List[IntegrationTestOutcome] = []
        self._setup_hooks: List[Callable] = []
        self._teardown_hooks: List[Callable] = []

    def register(self, name: str, test_fn: Callable, description: str = "",
                 tags: Optional[List[str]] = None, timeout_sec: float = 30.0,
                 dependencies: Optional[List[str]] = None):
        test = IntegrationTest(
            name=name, description=description, test_fn=test_fn,
            tags=tags or [], timeout_sec=timeout_sec,
            dependencies=dependencies or [],
        )
        self._tests[name] = test

    def add_setup(self, hook: Callable):
        self._setup_hooks.append(hook)

    def add_teardown(self, hook: Callable):
        self._teardown_hooks.append(hook)

    def run_test(self, name: str) -> IntegrationTestOutcome:
        test = self._tests.get(name)
        if not test:
            return IntegrationTestOutcome(name=name, result=IntegrationTestResult.ERROR, message="Test not found")
        # Check dependencies
        for dep in test.dependencies:
            dep_passed = any(r.name == dep and r.result == IntegrationTestResult.PASS for r in self._results)
            if not dep_passed:
                outcome = IntegrationTestOutcome(name=name, result=IntegrationTestResult.SKIP, message=f"Dependency '{dep}' not passed")
                self._results.append(outcome)
                return outcome
        start = time.perf_counter()
        try:
            result = test.test_fn()
            duration = (time.perf_counter() - start) * 1000
            if result is False:
                outcome = IntegrationTestOutcome(name=name, result=IntegrationTestResult.FAIL, duration_ms=duration)
            else:
                outcome = IntegrationTestOutcome(name=name, result=IntegrationTestResult.PASS, duration_ms=duration,
                                     details=result if isinstance(result, dict) else {})
        except AssertionError as e:
            duration = (time.perf_counter() - start) * 1000
            outcome = IntegrationTestOutcome(name=name, result=IntegrationTestResult.FAIL, duration_ms=duration, message=str(e))
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            outcome = IntegrationTestOutcome(name=name, result=IntegrationTestResult.ERROR, duration_ms=duration, message=str(e))
        self._results.append(outcome)
        return outcome

    def run_all(self, tags: Optional[List[str]] = None) -> TestSuiteReport:
        # Setup
        for hook in self._setup_hooks:
            try:
                hook()
            except Exception:
                pass
        # Topological sort by dependencies
        order = self._resolve_order()
        report = TestSuiteReport()
        for name in order:
            test = self._tests[name]
            if tags and not any(t in test.tags for t in tags):
                continue
            outcome = self.run_test(name)
            report.outcomes.append(outcome)
            report.total += 1
            report.duration_ms += outcome.duration_ms
            if outcome.result == IntegrationTestResult.PASS:
                report.passed += 1
            elif outcome.result == IntegrationTestResult.FAIL:
                report.failed += 1
            elif outcome.result == IntegrationTestResult.SKIP:
                report.skipped += 1
            else:
                report.errors += 1
        # Teardown
        for hook in self._teardown_hooks:
            try:
                hook()
            except Exception:
                pass
        return report

    def _resolve_order(self) -> List[str]:
        visited = set()
        order = []
        def visit(name):
            if name in visited:
                return
            visited.add(name)
            test = self._tests.get(name)
            if test:
                for dep in test.dependencies:
                    visit(dep)
            order.append(name)
        for name in self._tests:
            visit(name)
        return order

    def get_results(self) -> List[IntegrationTestOutcome]:
        return self._results.copy()

    def clear_results(self):
        self._results.clear()

    def summary(self) -> dict:
        passed = sum(1 for r in self._results if r.result == IntegrationTestResult.PASS)
        failed = sum(1 for r in self._results if r.result == IntegrationTestResult.FAIL)
        return {
            "total_tests": len(self._tests),
            "total_runs": len(self._results),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / max(len(self._results), 1) * 100, 1),
        }
