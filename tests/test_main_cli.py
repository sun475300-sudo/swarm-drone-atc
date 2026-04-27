"""main.py CLI 스모크 테스트.

argparse 구조가 깨지면 simulate / scenario / monte-carlo / visualize 등
모든 진입점이 동시에 죽음. 이 테스트는 CLI 파서가 정상 빌드되고
주요 서브커맨드가 등록되어 있는지를 빠르게 검증.

회귀 방어 대상:
- main 임포트 단계의 syntax/import 오류
- 서브파서 누락
- --help 호출이 SystemExit(0) 으로 끝나는지
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_MAIN = _ROOT / "main.py"


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    """main.py --help 류 명령을 서브프로세스로 실행하고 결과 반환.

    Windows cp949 기본 인코딩과 충돌하지 않도록 utf-8 + replace 처리.
    """
    return subprocess.run(
        [sys.executable, str(_MAIN), *args],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def test_main_help_exits_clean():
    """python main.py --help 가 exit code 0 으로 끝나야 한다."""
    result = _run_help("--help")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # 기본 sub-commands 가 사용법에 보여야 함
    out = result.stdout + result.stderr
    assert "simulate" in out
    assert "scenario" in out
    assert "monte-carlo" in out
    assert "visualize" in out


@pytest.mark.parametrize(
    "subcommand",
    ["simulate", "scenario", "monte-carlo", "visualize", "ops-report"],
)
def test_subcommand_help_exits_clean(subcommand: str):
    """각 서브커맨드의 --help 가 exit 0 이어야 한다."""
    result = _run_help(subcommand, "--help")
    assert result.returncode == 0, (
        f"subcommand={subcommand} returncode={result.returncode} stderr={result.stderr}"
    )


def test_simulate_rejects_unknown_flag():
    """명백히 잘못된 인자는 비-제로 exit 으로 거부되어야 한다."""
    result = _run_help("simulate", "--this-flag-does-not-exist")
    assert result.returncode != 0


def test_main_imports_without_error():
    """main 모듈 자체가 import 단계에서 예외 없이 로드되어야 한다.

    GPU 가속 모듈의 graceful fallback 가드(`docs/REGRESSION_NOTES_2026-04-26.md`)
    가 동작하면, torch 미설치/DLL 차단 환경에서도 임포트가 성공해야 한다.
    """
    # 새 서브프로세스에서 임포트만 수행
    result = subprocess.run(
        [sys.executable, "-c", "import main; print('OK')"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout
