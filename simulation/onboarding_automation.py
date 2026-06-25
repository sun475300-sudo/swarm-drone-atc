"""GENESIS Phase 385 -- 후속 기수 온보딩 자동화.

신규 참여자(후속 기수 학생/연구자)가 SDACS 프로젝트에 합류할 때
환경 구축과 아키텍처 이해를 자동화한다.

구성 요소
---------
1. **환경 점검 (EnvironmentCheck)**: Python 버전, 필수 패키지, 선택 패키지,
   디렉토리 구조, 설정 파일 존재 여부를 결정적으로 검사.
2. **아키텍처 투어 (ArchitectureTourStop)**: 4계층 아키텍처의 핵심 파일,
   모듈, 개념을 순서대로 안내하는 투어 스톱 18개.
3. **온보딩 리포트**: 환경 준비도 + 투어 진행률을 통합 보고.

설계 원칙
---------
- frozen dataclass, 결정적, 부수효과 0 (파일 시스템 읽기 전용 검사만)
- 기존 모듈 무수정 순수 추가
- ``shutil.which`` / ``importlib.util.find_spec`` 등 표준 라이브러리만 사용

정직 공시: 환경 점검은 패키지 설치 여부만 확인하며, 실제 설치를 수행하지
않는다. ``pip install`` 명령은 힌트로만 제공된다.

CLI:
    python simulation/onboarding_automation.py --check      # 환경 점검
    python simulation/onboarding_automation.py --tour        # 아키텍처 투어 목록
    python simulation/onboarding_automation.py --tour-stop 1 # 투어 스톱 상세
    python simulation/onboarding_automation.py --report      # 통합 리포트
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class EnvironmentCheck:
    """환경 점검 항목."""

    name: str
    description: str
    category: str
    required: bool
    check_type: str

    def run(self) -> CheckResult:
        """점검 실행 -- 결정적, 읽기 전용."""
        if self.check_type == "python_version":
            r = _check_python_version()
        elif self.check_type == "package":
            r = _check_package(self.name)
        elif self.check_type == "directory":
            r = _check_directory(self.name)
        elif self.check_type == "file":
            r = _check_file(self.name)
        else:
            raise ValueError(f"Unknown check_type: {self.check_type!r} for {self.name!r}")
        return CheckResult(name=r.name, passed=r.passed, detail=r.detail, required=self.required)


@dataclass(frozen=True)
class CheckResult:
    """점검 결과."""

    name: str
    passed: bool
    detail: str
    required: bool = False


@dataclass(frozen=True)
class ArchitectureTourStop:
    """아키텍처 투어 정거장."""

    stop_id: int
    layer: str
    title: str
    description: str
    key_files: tuple[str, ...]
    concepts: tuple[str, ...]
    exercises: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingReport:
    """온보딩 통합 리포트."""

    env_checks: tuple[CheckResult, ...]
    env_pass_rate: float
    required_pass_rate: float
    total_tour_stops: int
    ready: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "env_pass_rate": round(self.env_pass_rate, 1),
            "required_pass_rate": round(self.required_pass_rate, 1),
            "total_tour_stops": self.total_tour_stops,
            "ready": self.ready,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail, "required": c.required}
                for c in self.env_checks
            ],
        }


# -- 환경 점검 함수 --

def _check_python_version() -> CheckResult:
    v = sys.version_info
    passed = v.major == 3 and v.minor >= 10
    label = ">=3.10 OK" if passed else "<3.10 필요"
    return CheckResult(
        name="python_version", passed=passed,
        detail=f"Python {v.major}.{v.minor}.{v.micro} ({label})",
    )


def _check_package(package_name: str) -> CheckResult:
    spec = importlib.util.find_spec(package_name)
    passed = spec is not None
    return CheckResult(
        name=package_name, passed=passed,
        detail="설치됨" if passed else f"미설치 -- pip install {package_name}",
    )


def _check_directory(dir_name: str) -> CheckResult:
    exists = (_REPO_ROOT / dir_name).is_dir()
    return CheckResult(name=dir_name, passed=exists, detail="존재" if exists else "없음")


def _check_file(file_name: str) -> CheckResult:
    exists = (_REPO_ROOT / file_name).is_file()
    return CheckResult(name=file_name, passed=exists, detail="존재" if exists else "없음")


# -- 환경 점검 레지스트리 --

ENVIRONMENT_CHECKS: tuple[EnvironmentCheck, ...] = (
    EnvironmentCheck("python_version", "Python >=3.10", "runtime", True, "python_version"),
    EnvironmentCheck("numpy", "NumPy 수치 라이브러리", "core", True, "package"),
    EnvironmentCheck("simpy", "SimPy 이산 이벤트 시뮬레이션", "core", True, "package"),
    EnvironmentCheck("scipy", "SciPy 과학 계산", "core", True, "package"),
    EnvironmentCheck("yaml", "PyYAML 설정 파서", "core", True, "package"),
    EnvironmentCheck("dash", "Dash 웹 시각화", "core", True, "package"),
    EnvironmentCheck("plotly", "Plotly 그래프 라이브러리", "core", True, "package"),
    EnvironmentCheck("joblib", "Joblib 병렬 처리", "core", True, "package"),
    EnvironmentCheck("tqdm", "tqdm 진행 표시", "core", True, "package"),
    EnvironmentCheck("pandas", "Pandas 데이터 분석", "core", True, "package"),
    EnvironmentCheck("pytest", "pytest 테스트 프레임워크", "dev", False, "package"),
    EnvironmentCheck("hypothesis", "Hypothesis 속성 기반 테스트", "dev", False, "package"),
    EnvironmentCheck("mypy", "mypy 정적 타입 검사", "dev", False, "package"),
    EnvironmentCheck("torch", "PyTorch GPU 가속", "optional", False, "package"),
    EnvironmentCheck("simulation", "simulation/ 디렉토리", "structure", True, "directory"),
    EnvironmentCheck("tests", "tests/ 디렉토리", "structure", True, "directory"),
    EnvironmentCheck("config", "config/ 디렉토리", "structure", True, "directory"),
    EnvironmentCheck("config/default_simulation.yaml", "기본 시뮬레이션 설정", "config", True, "file"),
    EnvironmentCheck("pyproject.toml", "프로젝트 메타데이터", "config", True, "file"),
)

# -- 아키텍처 투어 레지스트리 --

ARCHITECTURE_TOUR: tuple[ArchitectureTourStop, ...] = (
    ArchitectureTourStop(
        stop_id=1, layer="개요",
        title="SDACS 프로젝트 구조",
        description="4계층 아키텍처(드론->제어->시뮬->UI)와 디렉토리 구조를 이해한다.",
        key_files=("CLAUDE.md", "README.md", "ROADMAP.md"),
        concepts=("4계층 아키텍처", "SimPy 이산 이벤트", "Dash 시각화"),
        exercises=("CLAUDE.md의 Architecture 섹션을 읽고 4계층을 요약하라",),
    ),
    ArchitectureTourStop(
        stop_id=2, layer="Layer 1 (드론)",
        title="DroneAgent -- 10Hz SimPy 프로세스",
        description="개별 드론의 상태 머신, 위치 갱신, 텔레메트리 발행을 담당한다.",
        key_files=("simulation/drone_agent.py",),
        concepts=("SimPy Process", "10Hz 갱신 루프", "DroneState"),
        exercises=("DroneAgent의 run() 제너레이터를 따라가며 한 틱의 흐름을 그려라",),
    ),
    ArchitectureTourStop(
        stop_id=3, layer="Layer 2 (제어)",
        title="AirspaceController -- 1Hz 충돌 감지/해결",
        description="공역 전체를 1Hz로 스캔하여 충돌 위험을 감지하고 해결 명령을 발행한다.",
        key_files=("src/airspace_control/controller/",),
        concepts=("CPA 예측", "충돌 해결률 공식", "5계층 안전망"),
        exercises=("충돌해결률 = 1 - collisions/(conflicts + collisions) 를 직접 계산하라",),
    ),
    ArchitectureTourStop(
        stop_id=4, layer="Layer 2 (제어)",
        title="APF 인공 포텐셜 장 충돌 회피",
        description="FIRAS 척력장 + 목표 인력장으로 실시간 충돌 회피 벡터를 산출한다.",
        key_files=("simulation/apf_engine.py",),
        concepts=("FIRAS 장", "인력/척력 합산", "APF_PARAMS_WINDY"),
        exercises=("강풍(>10 m/s)에서 APF_PARAMS_WINDY 자동 전환을 관찰하라",),
    ),
    ArchitectureTourStop(
        stop_id=5, layer="Layer 3 (시뮬)",
        title="SwarmSimulator -- 시뮬레이션 엔진",
        description="SimPy 환경 위에 드론, 제어기, 바람 모델을 통합 관리하는 메인 엔진이다.",
        key_files=("simulation/simulator.py",),
        concepts=("SwarmSimulator", "drones.default_count", "시드 기반 재현성"),
        exercises=("python main.py simulate --duration 60 을 실행하고 KPI를 기록하라",),
    ),
    ArchitectureTourStop(
        stop_id=6, layer="Layer 3 (시뮬)",
        title="WindModel -- 기상 시뮬레이션",
        description="기본/강풍/돌풍 등 기상 조건을 모델링하여 드론 비행에 영향을 준다.",
        key_files=("simulation/wind_model.py",),
        concepts=("풍속 벡터", "난류 모델", "강풍 모드 전환"),
        exercises=("무풍/약풍/강풍에서 시뮬을 돌리고 충돌해결률 변화를 비교하라",),
    ),
    ArchitectureTourStop(
        stop_id=7, layer="Layer 3 (시뮬)",
        title="Monte Carlo 시나리오 검증",
        description="다중 시드로 동일 시나리오를 반복 실행하여 통계적 신뢰도를 확보한다.",
        key_files=("simulation/monte_carlo_sweep.py", "config/monte_carlo.yaml"),
        concepts=("시드 스윕", "95% 신뢰구간", "통계적 유의성"),
        exercises=("python main.py monte-carlo --mode quick 으로 스윕을 실행하라",),
    ),
    ArchitectureTourStop(
        stop_id=8, layer="Layer 4 (UI)",
        title="CLI -- main.py 명령 체계",
        description="simulate, scenario, monte-carlo, visualize 등 CLI 진입점이다.",
        key_files=("main.py",),
        concepts=("argparse", "서브커맨드", "설정 오버라이드"),
        exercises=("python main.py --help 로 전체 명령 목록을 확인하라",),
    ),
    ArchitectureTourStop(
        stop_id=9, layer="Layer 4 (UI)",
        title="Dash 3D 시각화 대시보드",
        description="Plotly 3D 산점도로 드론 궤적, 충돌, CPA 예측선을 실시간 시각화한다.",
        key_files=("visualization/simulator_3d.py",),
        concepts=("Dash callback", "Plotly 3D", "실시간 갱신"),
        exercises=("python main.py visualize 로 대시보드를 열고 CPA 예측선을 관찰하라",),
    ),
    ArchitectureTourStop(
        stop_id=10, layer="안전",
        title="5계층 안전망 아키텍처",
        description="APF, CBS, 긴급착륙, 지오펜스, ATC 개입의 5계층 방어 심도.",
        key_files=("docs/certification/RTM_5LAYER_COVERAGE.md",),
        concepts=("방어 심도", "Ablation 실험", "계층별 기여도"),
        exercises=("5계층 중 하나를 비활성화한 Ablation 실험 결과를 분석하라",),
    ),
    ArchitectureTourStop(
        stop_id=11, layer="시나리오",
        title="시나리오 파라미터 시스템",
        description="YAML 기반 시나리오 정의로 다양한 운용 조건을 시뮬레이션한다.",
        key_files=("config/scenario_params/",),
        concepts=("시나리오 스키마", "NFZ 정의", ".sdacs-scenario"),
        exercises=("config/scenario_params/ 에서 시나리오 하나를 읽고 파라미터를 정리하라",),
    ),
    ArchitectureTourStop(
        stop_id=12, layer="테스트",
        title="테스트 인프라",
        description="pytest + xdist 병렬 실행, Hypothesis 속성 기반 테스트.",
        key_files=("tests/", "pyproject.toml"),
        concepts=("pytest-xdist", "AAA 패턴", "속성 기반 테스트"),
        exercises=("pytest tests/ -v --co -q 로 전체 테스트 수를 확인하라",),
    ),
    ArchitectureTourStop(
        stop_id=13, layer="인증",
        title="항공 규제 적합성 자산",
        description="항공안전법, SORA, KC 전파인증, DO-178C 갭 분석 등 인증 자산 세트.",
        key_files=("docs/certification/", "simulation/sora_calculator.py"),
        concepts=("SORA SAIL", "KC 전파인증", "DO-178C"),
        exercises=("SORA 자동 계산기의 입력 파라미터와 출력 SAIL 등급을 확인하라",),
    ),
    ArchitectureTourStop(
        stop_id=14, layer="교육",
        title="교육 모드 & 실습 과제",
        description="5단계 튜토리얼(Phase 381)과 10종 실습 과제(Phase 382).",
        key_files=("simulation/practice_assignments.py",),
        concepts=("결정적 채점", "학습성과 매핑", "난이도 단계"),
        exercises=("python simulation/practice_assignments.py --list 로 과제 목록을 확인하라",),
    ),
    ArchitectureTourStop(
        stop_id=15, layer="국제",
        title="ODYSSEY -- 국제 확장",
        description="FAA UTM, EASA U-space, ICAO 공역 클래스 등 국제 규제 정렬.",
        key_files=("simulation/faa_utm_gap.py", "simulation/geo_zones.py"),
        concepts=("FAA Part 107", "EASA Open/Specific/Certified", "ICAO A-G"),
        exercises=("simulation/airspace_class.py 의 classify_airspace() API를 호출해보라",),
    ),
    ArchitectureTourStop(
        stop_id=16, layer="웹",
        title="브라우저 3D 시뮬레이터",
        description="Three.js 기반 브라우저 단독 실행 시뮬레이터.",
        key_files=("visualization/swarm_3d_simulator.html",),
        concepts=("Three.js", "WebGL", "CPA 공간해시"),
        exercises=("브라우저에서 simulator.html을 열고 드론 100대 시뮬을 실행하라",),
    ),
    ArchitectureTourStop(
        stop_id=17, layer="배포",
        title="서비스 아키텍처 -- FastAPI + React",
        description="FastAPI REST API + JWT/RBAC 인증 + React 프론트엔드.",
        key_files=("src/api/", "frontend/"),
        concepts=("FastAPI", "JWT", "RBAC", "TimescaleDB"),
        exercises=("src/api/ 의 엔드포인트 목록을 정리하라",),
    ),
    ArchitectureTourStop(
        stop_id=18, layer="마무리",
        title="온보딩 완료 체크리스트",
        description="환경 구축, 아키텍처 이해, 첫 시뮬 실행을 모두 완료했는지 확인한다.",
        key_files=("CLAUDE.md",),
        concepts=("Quick Commands", "Do NOT 목록", "Key Conventions"),
        exercises=(
            "CLAUDE.md의 Quick Commands 5개를 모두 실행하고 결과를 기록하라",
            "Do NOT 목록 6개를 숙지하고 위반 사례를 작성하라",
        ),
    ),
)

_TOUR_MAP: dict[int, ArchitectureTourStop] = {s.stop_id: s for s in ARCHITECTURE_TOUR}


# -- 공개 API --

def run_environment_checks() -> tuple[CheckResult, ...]:
    """전체 환경 점검을 실행하고 결과를 반환한다."""
    return tuple(check.run() for check in ENVIRONMENT_CHECKS)


def get_tour_stop(stop_id: int) -> ArchitectureTourStop:
    """투어 스톱 ID로 조회."""
    if stop_id not in _TOUR_MAP:
        raise ValueError(
            f"Unknown stop_id={stop_id}. Valid: {sorted(_TOUR_MAP)}"
        )
    return _TOUR_MAP[stop_id]


def list_tour_stops() -> list[dict[str, Any]]:
    """투어 스톱 목록 반환."""
    return [
        {
            "id": s.stop_id,
            "layer": s.layer,
            "title": s.title,
            "files_count": len(s.key_files),
            "exercises_count": len(s.exercises),
        }
        for s in ARCHITECTURE_TOUR
    ]


def generate_report() -> OnboardingReport:
    """온보딩 통합 리포트를 생성한다."""
    checks = run_environment_checks()
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    env_rate = (passed / total * 100.0) if total > 0 else 0.0

    required_checks = [c for c in checks if c.required]
    req_total = len(required_checks)
    req_passed = sum(1 for c in required_checks if c.passed)
    req_rate = (req_passed / req_total * 100.0) if req_total > 0 else 0.0

    return OnboardingReport(
        env_checks=checks,
        env_pass_rate=env_rate,
        required_pass_rate=req_rate,
        total_tour_stops=len(ARCHITECTURE_TOUR),
        ready=req_rate >= 100.0,
    )


def setup_command_hint() -> str:
    """환경 구축 1-스크립트 힌트."""
    return (
        "# SDACS 환경 구축 (1-스크립트)\n"
        "# 1. Python >=3.10 설치 확인\n"
        "python --version\n"
        "\n"
        "# 2. 가상 환경 생성 및 활성화\n"
        "python -m venv .venv\n"
        "# Windows: .venv\\Scripts\\activate\n"
        "# macOS/Linux: source .venv/bin/activate\n"
        "\n"
        "# 3. 의존성 설치\n"
        "pip install -e '.[dev]'\n"
        "\n"
        "# 4. 환경 점검\n"
        "python simulation/onboarding_automation.py --check\n"
        "\n"
        "# 5. 테스트 실행 (전체)\n"
        "pytest tests/ -v\n"
        "\n"
        "# 6. 첫 시뮬레이션\n"
        "python main.py simulate --duration 60\n"
        "\n"
        "# 7. 3D 시각화 확인\n"
        "python main.py visualize\n"
    )


# -- CLI --

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 385 -- 후속 기수 온보딩 자동화")
    parser.add_argument("--check", action="store_true", help="환경 점검")
    parser.add_argument("--tour", action="store_true", help="아키텍처 투어 목록")
    parser.add_argument("--tour-stop", type=int, metavar="ID", help="투어 스톱 상세")
    parser.add_argument("--report", action="store_true", help="통합 리포트")
    parser.add_argument("--setup-hint", action="store_true", help="환경 구축 힌트")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.check:
        results = run_environment_checks()
        if args.json:
            print(json.dumps(
                [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in results],
                ensure_ascii=False, indent=2,
            ))
        else:
            for r in results:
                status = "PASS" if r.passed else "FAIL"
                print(f"  [{status}] {r.name:<40} {r.detail}")
            passed = sum(1 for r in results if r.passed)
            print(f"\n  {passed}/{len(results)} 통과")

    elif args.tour:
        stops = list_tour_stops()
        if args.json:
            print(json.dumps(stops, ensure_ascii=False, indent=2))
        else:
            print(f"{'ID':>3} {'계층':<12} {'제목'}")
            print("-" * 50)
            for s in stops:
                print(f"{s['id']:>3} {s['layer']:<12} {s['title']}")

    elif args.tour_stop is not None:
        try:
            stop = get_tour_stop(args.tour_stop)
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps({
                "id": stop.stop_id,
                "layer": stop.layer,
                "title": stop.title,
                "description": stop.description,
                "key_files": list(stop.key_files),
                "concepts": list(stop.concepts),
                "exercises": list(stop.exercises),
            }, ensure_ascii=False, indent=2))
        else:
            print(f"투어 #{stop.stop_id}: {stop.title}")
            print(f"  계층: {stop.layer}")
            print(f"  설명: {stop.description}")
            print(f"  핵심 파일: {', '.join(stop.key_files)}")
            print(f"  개념: {', '.join(stop.concepts)}")
            print("  실습:")
            for i, ex in enumerate(stop.exercises, 1):
                print(f"    {i}. {ex}")

    elif args.report:
        report = generate_report()
        if args.json:
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        else:
            print("=== SDACS 온보딩 리포트 ===")
            print(f"  환경 점검 통과율: {report.env_pass_rate:.1f}%")
            print(f"  필수 항목 통과율: {report.required_pass_rate:.1f}%")
            print(f"  아키텍처 투어:    {report.total_tour_stops}개 스톱")
            print(f"  준비 완료:        {'YES' if report.ready else 'NO'}")

    elif args.setup_hint:
        print(setup_command_hint())

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
