"""Audit every local and origin branch before consolidating into main.

The script is read-only with respect to refs and the working tree. Git's
``merge-tree`` may create unreachable tree objects while simulating merges, but
it does not move branches or modify checked-out files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class BranchRecord:
    ref: str
    short_name: str
    scope: str
    oid: str
    commit_date: str
    subject: str
    is_main: bool
    merged_into_main: bool
    main_behind_count: int
    branch_ahead_count: int
    cherry_novel_commits: int
    cherry_equivalent_commits: int
    changed_file_count: int
    residual_file_count: int
    overlap_with_main_count: int
    merge_status: str
    classification: str
    pr_numbers: list[int]
    pr_states: list[str]
    changed_files: list[str]
    residual_files: list[str]
    overlap_with_main_files: list[str]
    conflict_summary: str
    residual_fingerprint: str


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{detail}")
    return result


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], check=check)


def git_text(*args: str, check: bool = True) -> str:
    return git(*args, check=check).stdout.strip()


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return git("merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode == 0


def nul_paths(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Git path query failed: git {' '.join(args)}\n{detail}")
    return sorted(
        {
            item.decode("utf-8", errors="surrogateescape")
            for item in result.stdout.split(b"\0")
            if item
        }
    )


def tree_entry(ref: str, path: str) -> str:
    result = git("ls-tree", ref, "--", path, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return "<missing>"
    return result.stdout.split("\t", 1)[0].strip()


def load_prs() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    fields = "number,title,headRefName,baseRefName,state,isDraft,mergeable,mergedAt,closedAt,url,updatedAt"
    result = run(
        ["gh", "pr", "list", "--state", "all", "--limit", "1000", "--json", fields],
        check=False,
    )
    if result.returncode != 0:
        return [], {}
    prs = json.loads(result.stdout)
    by_head: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pr in prs:
        by_head[pr["headRefName"]].append(pr)
    return prs, by_head


def list_refs() -> list[dict[str, str]]:
    fmt = "%(refname)%09%(refname:short)%09%(objectname)%09%(committerdate:iso-strict)%09%(subject)"
    output = git_text("for-each-ref", f"--format={fmt}", "refs/heads", "refs/remotes/origin")
    refs: list[dict[str, str]] = []
    for line in output.splitlines():
        ref, short_name, oid, commit_date, subject = line.split("\t", 4)
        if ref == "refs/remotes/origin/HEAD":
            continue
        refs.append(
            {
                "ref": ref,
                "short_name": short_name,
                "oid": oid,
                "commit_date": commit_date,
                "subject": subject,
                "scope": "local" if ref.startswith("refs/heads/") else "remote",
            }
        )
    return refs


def cherry_counts(main_ref: str, branch_ref: str) -> tuple[int, int]:
    output = git_text("cherry", main_ref, branch_ref, check=False)
    novel = 0
    equivalent = 0
    for line in output.splitlines():
        if line.startswith("+"):
            novel += 1
        elif line.startswith("-"):
            equivalent += 1
    return novel, equivalent


def simulate_merge(main_ref: str, branch_ref: str) -> tuple[str, str]:
    result = git("merge-tree", "--write-tree", "--name-only", main_ref, branch_ref, check=False)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode == 0:
        return "clean", ""
    summary_lines = [
        line
        for line in output.splitlines()
        if "CONFLICT" in line or "Auto-merging" in line or "warning:" in line.lower()
    ]
    return "conflict", " | ".join(summary_lines[:12]) or output[:1000]


def classify(
    *,
    is_main: bool,
    merged: bool,
    changed_files: list[str],
    residual_files: list[str],
    cherry_novel: int,
    merge_status: str,
) -> str:
    if is_main:
        return "main"
    if merged:
        return "merged"
    if not changed_files:
        return "no_branch_delta"
    if not residual_files:
        return "content_subsumed"
    if cherry_novel == 0:
        return "patch_equivalent_stale"
    if merge_status == "conflict":
        return "merge_conflict"
    return "merge_clean"


def analyze_ref(
    ref_info: dict[str, str],
    *,
    main_ref: str,
    main_oid: str,
    prs_by_head: dict[str, list[dict[str, Any]]],
) -> BranchRecord:
    ref = ref_info["ref"]
    short_name = ref_info["short_name"]
    oid = ref_info["oid"]
    is_main = oid == main_oid and short_name in {main_ref, f"origin/{main_ref}"}
    merged = is_ancestor(ref, main_ref)
    counts = git_text("rev-list", "--left-right", "--count", f"{main_ref}...{ref}")
    main_behind, branch_ahead = (int(value) for value in counts.split())
    cherry_novel, cherry_equivalent = cherry_counts(main_ref, ref)

    changed_files = [] if is_main else nul_paths("diff", "--name-only", "-z", f"{main_ref}...{ref}")
    residual_files = [
        path for path in changed_files if tree_entry(main_ref, path) != tree_entry(ref, path)
    ]

    merge_base = git_text("merge-base", main_ref, ref)
    main_changed_files = (
        [] if merge_base == main_oid else nul_paths("diff", "--name-only", "-z", f"{merge_base}..{main_ref}")
    )
    overlap_files = sorted(set(changed_files).intersection(main_changed_files))

    merge_status = "not_needed"
    conflict_summary = ""
    if residual_files and not merged:
        merge_status, conflict_summary = simulate_merge(main_ref, ref)

    fingerprint_source = "\n".join(
        f"{path}\t{tree_entry(ref, path)}" for path in residual_files
    ).encode("utf-8", errors="surrogateescape")
    residual_fingerprint = hashlib.sha256(fingerprint_source).hexdigest() if residual_files else ""

    head_name = short_name.removeprefix("origin/")
    prs = prs_by_head.get(head_name, [])
    classification = classify(
        is_main=is_main,
        merged=merged,
        changed_files=changed_files,
        residual_files=residual_files,
        cherry_novel=cherry_novel,
        merge_status=merge_status,
    )
    return BranchRecord(
        ref=ref,
        short_name=short_name,
        scope=ref_info["scope"],
        oid=oid,
        commit_date=ref_info["commit_date"],
        subject=ref_info["subject"],
        is_main=is_main,
        merged_into_main=merged,
        main_behind_count=main_behind,
        branch_ahead_count=branch_ahead,
        cherry_novel_commits=cherry_novel,
        cherry_equivalent_commits=cherry_equivalent,
        changed_file_count=len(changed_files),
        residual_file_count=len(residual_files),
        overlap_with_main_count=len(overlap_files),
        merge_status=merge_status,
        classification=classification,
        pr_numbers=sorted(pr["number"] for pr in prs),
        pr_states=sorted({pr["state"] for pr in prs}),
        changed_files=changed_files,
        residual_files=residual_files,
        overlap_with_main_files=overlap_files,
        conflict_summary=conflict_summary,
        residual_fingerprint=residual_fingerprint,
    )


def canonical_records(records: list[BranchRecord], main_ref: str) -> list[BranchRecord]:
    """Prefer origin refs and collapse local tracking aliases with the same tip."""
    by_oid: dict[str, list[BranchRecord]] = defaultdict(list)
    for record in records:
        if not record.is_main:
            by_oid[record.oid].append(record)

    canonical: list[BranchRecord] = []
    for group in by_oid.values():
        preferred = sorted(
            group,
            key=lambda item: (
                0 if item.short_name.startswith("origin/") else 1,
                0 if item.short_name == f"origin/{main_ref}" else 1,
                item.short_name,
            ),
        )[0]
        canonical.append(preferred)
    return sorted(canonical, key=lambda item: item.short_name)


def overlap_pairs(records: list[BranchRecord]) -> list[dict[str, Any]]:
    candidates = [
        record
        for record in records
        if record.classification in {"merge_clean", "merge_conflict"}
    ]
    pairs: list[dict[str, Any]] = []
    for index, left in enumerate(candidates):
        left_paths = set(left.residual_files)
        for right in candidates[index + 1 :]:
            right_paths = set(right.residual_files)
            common = sorted(left_paths.intersection(right_paths))
            if not common:
                continue
            union_size = len(left_paths.union(right_paths))
            jaccard = len(common) / union_size if union_size else 0.0
            pairs.append(
                {
                    "left": left.short_name,
                    "right": right.short_name,
                    "common_file_count": len(common),
                    "jaccard": round(jaccard, 4),
                    "common_files": common,
                }
            )
    return sorted(
        pairs,
        key=lambda item: (-item["common_file_count"], -item["jaccard"], item["left"], item["right"]),
    )


def write_csv(path: Path, records: list[BranchRecord]) -> None:
    scalar_fields = [
        "ref",
        "short_name",
        "scope",
        "oid",
        "commit_date",
        "subject",
        "is_main",
        "merged_into_main",
        "main_behind_count",
        "branch_ahead_count",
        "cherry_novel_commits",
        "cherry_equivalent_commits",
        "changed_file_count",
        "residual_file_count",
        "overlap_with_main_count",
        "merge_status",
        "classification",
        "pr_numbers",
        "pr_states",
        "changed_files",
        "residual_files",
        "overlap_with_main_files",
        "conflict_summary",
        "residual_fingerprint",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=scalar_fields)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            for key in (
                "pr_numbers",
                "pr_states",
                "changed_files",
                "residual_files",
                "overlap_with_main_files",
            ):
                row[key] = " | ".join(str(item) for item in row[key])
            writer.writerow(row)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def write_report(
    path: Path,
    *,
    main_ref: str,
    main_oid: str,
    records: list[BranchRecord],
    canonical: list[BranchRecord],
    prs: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> None:
    counts = Counter(record.classification for record in canonical)
    scopes = Counter(record.scope for record in records)
    open_prs = [pr for pr in prs if pr["state"] == "OPEN"]
    merge_candidates = [
        record
        for record in canonical
        if record.classification in {"merge_clean", "merge_conflict"}
    ]
    clean_candidates = [record for record in merge_candidates if record.classification == "merge_clean"]
    conflict_candidates = [record for record in merge_candidates if record.classification == "merge_conflict"]

    tip_groups: dict[str, list[str]] = defaultdict(list)
    fingerprint_groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        tip_groups[record.oid].append(record.short_name)
    for record in canonical:
        if record.residual_fingerprint:
            fingerprint_groups[record.residual_fingerprint].append(record.short_name)

    duplicate_tips = [names for names in tip_groups.values() if len(names) > 1]
    duplicate_content = [names for names in fingerprint_groups.values() if len(names) > 1]

    candidate_rows = [
        [
            record.short_name,
            record.classification,
            str(record.branch_ahead_count),
            str(record.residual_file_count),
            str(record.overlap_with_main_count),
            ",".join(str(number) for number in record.pr_numbers) or "-",
            "<br>".join(record.residual_files[:5]) + ("<br>..." if len(record.residual_files) > 5 else ""),
        ]
        for record in sorted(
            merge_candidates,
            key=lambda item: (
                item.classification != "merge_conflict",
                not item.pr_numbers,
                item.short_name,
            ),
        )
    ]

    conflict_rows = [
        [
            record.short_name,
            str(record.branch_ahead_count),
            str(record.residual_file_count),
            "<br>".join(record.overlap_with_main_files[:8]) or "-",
            record.conflict_summary[:300] or "-",
        ]
        for record in conflict_candidates
    ]

    report = f"""# 전체 브랜치 병합 준비 보고서

- 생성일: {date.today().isoformat()}
- 기준 브랜치: `{main_ref}` (`{main_oid[:12]}`)
- 분석 범위: 로컬 {scopes["local"]}개 + 원격 {scopes["remote"]}개 = 참조 {len(records)}개
- 동일 tip 별칭을 합친 고유 비-main tip: {len(canonical)}개
- GitHub PR 메타데이터: 전체 {len(prs)}개, 열린 PR {len(open_prs)}개
- 분석 방법: ancestry, `git cherry`, branch-side blob 비교, merge-base 파일 중첩, `git merge-tree --write-tree`

## 결론 요약

{markdown_table(
    ["분류", "개수", "조치"],
    [
        ["이미 main에 병합", str(counts["merged"]), "병합 금지. 원격 브랜치 정리 후보"],
        ["내용이 main에 흡수됨", str(counts["content_subsumed"]), "병합 금지. 계보만 달라진 중복"],
        ["패치 동등/구버전", str(counts["patch_equivalent_stale"]), "병합 금지. 최신 main을 되돌릴 위험"],
        ["브랜치 실질 변경 없음", str(counts["no_branch_delta"]), "병합 불필요"],
        ["자동 병합 가능 후보", str(counts["merge_clean"]), "PR·테스트 확인 후 선택 병합"],
        ["충돌 예상 후보", str(counts["merge_conflict"]), "직접 병합 금지. 별도 통합 브랜치 필요"],
    ],
)}

## 병합 준비 원칙

1. 모든 브랜치를 일괄 병합하지 않는다. 이미 병합되었거나 내용이 흡수된 브랜치는 닫고 삭제한다.
2. `merge_clean` 후보도 파일 내용과 PR 목적을 검토한 뒤 하나씩 병합한다.
3. 동일 residual fingerprint 그룹은 대표 브랜치 하나만 선택한다.
4. 파일 중첩이 큰 브랜치는 독립 병합하지 말고 최신 브랜치 또는 열린 PR 하나로 통합한다.
5. Dependabot 브랜치는 생태계별로 분리해 CI를 통과한 항목만 병합한다.
6. 각 병합 후 `ruff`, 전체 pytest, 대표 시뮬레이션을 재실행한다.

## 선택 병합 검토 대상

자동 병합 가능 {len(clean_candidates)}개, 충돌 예상 {len(conflict_candidates)}개입니다.

{markdown_table(
    ["브랜치", "상태", "ahead", "잔여 파일", "main과 중첩", "PR", "잔여 파일 예시"],
    candidate_rows,
) if candidate_rows else "선택 병합 후보가 없습니다."}

## 충돌 예상 브랜치

{markdown_table(
    ["브랜치", "ahead", "잔여 파일", "중첩 파일", "merge-tree 메시지"],
    conflict_rows,
) if conflict_rows else "충돌 예상 브랜치가 없습니다."}

## 완전 중복 tip 그룹

동일 커밋을 가리키는 별칭 그룹은 {len(duplicate_tips)}개입니다. 로컬 추적 브랜치와 원격 브랜치 중복이 포함됩니다.

{chr(10).join("- " + ", ".join(f"`{name}`" for name in sorted(names)) for names in duplicate_tips[:40]) or "- 없음"}

## 동일 잔여 내용 그룹

브랜치 이름과 커밋은 다르지만 main에 없는 최종 파일 내용이 동일한 그룹은 {len(duplicate_content)}개입니다.

{chr(10).join("- " + ", ".join(f"`{name}`" for name in sorted(names)) for names in duplicate_content[:40]) or "- 없음"}

## 변경 파일 중첩 상위 쌍

{markdown_table(
    ["브랜치 A", "브랜치 B", "공통 파일", "Jaccard", "파일 예시"],
    [
        [
            pair["left"],
            pair["right"],
            str(pair["common_file_count"]),
            f'{pair["jaccard"]:.2f}',
            "<br>".join(pair["common_files"][:6]),
        ]
        for pair in pairs[:60]
    ],
) if pairs else "잔여 변경 파일이 겹치는 후보가 없습니다."}

## 권장 실행 순서

1. 현재 작업을 커밋하거나 별도 브랜치로 보존한다.
2. `git fetch --all --prune --tags`를 재실행한다.
3. 이 보고서의 `merged`, `content_subsumed`, `patch_equivalent_stale`, `no_branch_delta` 브랜치는 병합 대상에서 제외한다.
4. 열린 PR이 연결된 `merge_clean` 후보를 우선 검토한다.
5. 동일 내용/높은 중첩 그룹에서는 가장 최신이고 테스트가 있는 브랜치 하나만 선택한다.
6. 선택 브랜치를 임시 통합 브랜치에 하나씩 병합한다.
7. 충돌 후보는 기능별로 cherry-pick 또는 수동 재구현하고, 오래된 README/CHANGELOG 변경은 가져오지 않는다.
8. 검증 완료 후에만 통합 브랜치를 `main` 대상으로 PR 생성한다.

## 검증 명령

```powershell
python -m ruff check .
python -m pytest -q -n 0 --no-cov
python main.py simulate --duration 60 --drones 100 --seed 42
```

## 전체 목록

모든 브랜치 참조의 상세 결과는 같은 디렉터리의 `branches.csv`와 `branches.json`에 있습니다.
중복/중첩 쌍 전체는 `overlap_pairs.json`에 있습니다.
"""
    path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main", default="main", help="Main branch ref")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs") / f"BRANCH_AUDIT_{date.today().isoformat()}",
    )
    args = parser.parse_args()

    main_oid = git_text("rev-parse", args.main)
    refs = list_refs()
    prs, prs_by_head = load_prs()
    records: list[BranchRecord] = []
    for index, ref_info in enumerate(refs, start=1):
        record = analyze_ref(
            ref_info,
            main_ref=args.main,
            main_oid=main_oid,
            prs_by_head=prs_by_head,
        )
        records.append(record)
        print(
            f"[{index:03d}/{len(refs):03d}] {record.short_name}: "
            f"{record.classification}, residual={record.residual_file_count}"
        )

    canonical = canonical_records(records, args.main)
    pairs = overlap_pairs(canonical)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "branches.json").write_text(
        json.dumps([asdict(record) for record in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(output_dir / "branches.csv", records)
    (output_dir / "overlap_pairs.json").write_text(
        json.dumps(pairs, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "pull_requests.json").write_text(
        json.dumps(prs, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_report(
        output_dir / "BRANCH_MERGE_PREPARATION.md",
        main_ref=args.main,
        main_oid=main_oid,
        records=records,
        canonical=canonical,
        prs=prs,
        pairs=pairs,
    )
    print(f"Wrote audit to {output_dir}")


if __name__ == "__main__":
    main()
