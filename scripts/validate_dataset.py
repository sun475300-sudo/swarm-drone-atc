"""P703 — 벤치마크 데이터셋 검증 + Zenodo 형식 내보내기"""

import argparse
import json
import sys
from pathlib import Path

# jsonschema는 선택적 의존성
try:
    import jsonschema
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

SCHEMA_PATH = Path(__file__).parent.parent / "benchmarks" / "_schema" / "manifest.schema.json"
SCENARIOS_DIR = Path(__file__).parent.parent / "benchmarks" / "scenarios"

REQUIRED_KEYS = ["id", "category", "difficulty", "description", "drones", "duration_s"]
VALID_CATEGORIES = {"corridor", "urban", "emergency", "weather", "density", "delivery"}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "extreme"}
ID_PATTERN_RE = None

try:
    import re
    ID_PATTERN_RE = re.compile(r"^[0-9]{2}_[a-z_]+$")
except ImportError:
    pass


def _load_schema():
    if not SCHEMA_PATH.exists():
        return None
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _basic_validate(manifest: dict) -> list[str]:
    """jsonschema 없을 때 기본 키 검사."""
    errors = []

    for key in REQUIRED_KEYS:
        if key not in manifest:
            errors.append(f"필수 키 누락: '{key}'")

    if "id" in manifest and ID_PATTERN_RE:
        if not ID_PATTERN_RE.match(str(manifest["id"])):
            errors.append(f"id 패턴 불일치: '{manifest['id']}' (예: '01_corridor_crossing')")

    if "category" in manifest and manifest["category"] not in VALID_CATEGORIES:
        errors.append(f"category 값 오류: '{manifest['category']}' (허용: {sorted(VALID_CATEGORIES)})")

    if "difficulty" in manifest and manifest["difficulty"] not in VALID_DIFFICULTIES:
        errors.append(f"difficulty 값 오류: '{manifest['difficulty']}' (허용: {sorted(VALID_DIFFICULTIES)})")

    if "drones" in manifest:
        d = manifest["drones"]
        if not isinstance(d, int) or d < 2 or d > 200:
            errors.append(f"drones 범위 오류: {d} (허용: 2~200)")

    if "duration_s" in manifest:
        dur = manifest["duration_s"]
        if not isinstance(dur, (int, float)) or dur < 10 or dur > 3600:
            errors.append(f"duration_s 범위 오류: {dur} (허용: 10~3600)")

    return errors


def validate_manifest(path: str | Path) -> tuple[bool, list[str]]:
    """JSON 매니페스트 파일 검증.

    Returns:
        (ok, errors) — ok=True이면 유효, errors는 오류 메시지 목록
    """
    path = Path(path)
    errors = []

    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON 파싱 오류: {e}"]
    except OSError as e:
        return False, [f"파일 읽기 오류: {e}"]

    if _HAS_JSONSCHEMA:
        schema = _load_schema()
        if schema:
            validator = jsonschema.Draft202012Validator(schema)
            for err in validator.iter_errors(manifest):
                errors.append(err.message)
        else:
            errors.extend(_basic_validate(manifest))
    else:
        errors.extend(_basic_validate(manifest))

    return len(errors) == 0, errors


def export_zenodo(manifest_paths: list[Path], output_dir: str | Path) -> Path:
    """Zenodo 형식 데이터셋 요약 JSON 생성.

    Args:
        manifest_paths: 검증할 매니페스트 파일 경로 목록
        output_dir: 출력 디렉터리

    Returns:
        생성된 dataset_summary.json 경로
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_scenarios = []
    invalid_scenarios = []

    for p in manifest_paths:
        ok, errors = validate_manifest(p)
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        entry = {
            "file": str(p.name),
            "id": data.get("id", str(p.stem)),
            "valid": ok,
        }
        if not ok:
            entry["errors"] = errors

        if ok:
            valid_scenarios.append(entry)
        else:
            invalid_scenarios.append(entry)

    summary = {
        "total": len(manifest_paths),
        "valid": len(valid_scenarios),
        "invalid": len(invalid_scenarios),
        "scenarios": valid_scenarios + invalid_scenarios,
    }

    out_path = output_dir / "dataset_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return out_path


def main():
    parser = argparse.ArgumentParser(description="P703 벤치마크 데이터셋 검증기")
    parser.add_argument(
        "--export",
        metavar="DIR",
        default=None,
        help="Zenodo 요약 JSON 출력 디렉터리 (예: dist/)",
    )
    args = parser.parse_args()

    manifest_paths = sorted(SCENARIOS_DIR.glob("*.json"))

    if not manifest_paths:
        print(f"매니페스트 파일 없음: {SCENARIOS_DIR}")
        sys.exit(0)

    total = len(manifest_paths)
    ok_count = 0

    for p in manifest_paths:
        ok, errors = validate_manifest(p)
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {p.name}")
        if not ok:
            for err in errors:
                print(f"       - {err}")
        if ok:
            ok_count += 1

    print(f"\n결과: {ok_count}/{total} OK")

    if args.export:
        out_path = export_zenodo(manifest_paths, args.export)
        print(f"Zenodo 요약 내보내기 완료: {out_path}")

    if ok_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
