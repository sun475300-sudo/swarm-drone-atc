#!/usr/bin/env python3
"""
PostToolUse hook: git push 후 README.md 변경 이력 자동 업데이트
- [changelog] 마커가 있는 커밋은 건너뜀 (무한 루프 방지)
- 최신 항목이 표 상단에 위치 (newest-first)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

README_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
SECTION_HEADER = "## 변경 이력 (Changelog)"
TABLE_HEADER   = "| 날짜/시간 (KST) | 커밋 | 작업 내용 | 수정 파일 |"
TABLE_SEP      = "| --- | --- | --- | --- |"
SKIP_MARKER    = "[changelog]"


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def main():
    # ── 1. 입력 확인 ──────────────────────────────────────────
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if "git push" not in command:
        sys.exit(0)

    # ── 2. 무한루프 방지 (changelog 자동커밋 무시) ──────────
    latest_msg = run(["git", "log", "-1", "--format=%s"],
                     cwd=os.path.dirname(README_PATH)).stdout.strip()
    if SKIP_MARKER in latest_msg:
        sys.exit(0)

    # ── 3. 커밋 정보 수집 ────────────────────────────────────
    repo = os.path.dirname(README_PATH)
    h    = run(["git", "log", "-1", "--format=%h"],  cwd=repo).stdout.strip()
    msg  = run(["git", "log", "-1", "--format=%s"],  cwd=repo).stdout.strip()
    files_raw = run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"], cwd=repo
    ).stdout.strip()
    files = ", ".join(files_raw.split("\n")[:6]) if files_raw else "-"
    if files_raw and len(files_raw.split("\n")) > 6:
        files += " …"

    # KST(UTC+9) 시간
    kst = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    entry = f"| {kst} | `{h}` | {msg} | {files} |"

    # ── 4. README.md 업데이트 ────────────────────────────────
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if SECTION_HEADER in content:
        # 기존 섹션: 구분자(| --- |) 다음 줄에 새 항목 삽입 (최신순)
        lines = content.split("\n")
        new_lines = []
        in_section = False
        inserted = False
        for line in lines:
            if line.startswith(SECTION_HEADER):
                in_section = True
            if in_section and not inserted and line.startswith("| ---"):
                new_lines.append(line)
                new_lines.append(entry)
                inserted = True
                continue
            new_lines.append(line)
        content = "\n".join(new_lines)
    else:
        # 섹션 없음: 마지막 <div> 직전 또는 파일 끝에 삽입
        footer_marker = "**Made with heart"
        if footer_marker in content:
            # 마지막 --- 구분자 바로 앞에 삽입
            idx = content.rfind("\n---\n\n", 0, content.find(footer_marker))
            if idx != -1:
                insert_point = idx  # '\n---\n\n' 직전
                content = (
                    content[:insert_point]
                    + f"\n\n{SECTION_HEADER}\n\n{TABLE_HEADER}\n{TABLE_SEP}\n{entry}\n"
                    + content[insert_point:]
                )
            else:
                content = content.rstrip() + f"\n\n{SECTION_HEADER}\n\n{TABLE_HEADER}\n{TABLE_SEP}\n{entry}\n"
        else:
            content = content.rstrip() + f"\n\n{SECTION_HEADER}\n\n{TABLE_HEADER}\n{TABLE_SEP}\n{entry}\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    # ── 5. 자동 커밋 & 푸시 ──────────────────────────────────
    run(["git", "add", README_PATH], cwd=repo)
    run(["git", "commit", "-m", f"docs: 변경 이력 업데이트 {kst} {SKIP_MARKER}"], cwd=repo)
    run(["git", "push"], cwd=repo)

    print(f"[changelog] README.md 업데이트 완료: {h} {kst}", file=sys.stderr)


if __name__ == "__main__":
    main()
