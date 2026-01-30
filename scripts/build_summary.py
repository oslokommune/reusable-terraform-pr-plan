#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def env_rank(stack: str) -> int:
    if "/dev/" in stack:
        return 0
    if "/prod/" in stack:
        return 1
    return 2


def normalize_stack(stack: str) -> str:
    return stack.replace("/dev/", "/", 1).replace("/prod/", "/", 1)


def write_github_output(path: Path, key: str, value: str) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a combined summary markdown file.")
    parser.add_argument("--summaries-dir", default="summaries")
    parser.add_argument("--stacks-json", default="[]")
    parser.add_argument("--github-run-id", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--is-pull-request", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args()

    try:
        stacks = json.loads(args.stacks_json) if args.stacks_json else []
    except json.JSONDecodeError:
        stacks = []

    stack_total = len(stacks)
    stack_word = "stack" if stack_total == 1 else "stacks"

    summary_lines = [f"## Summary ({stack_total} {stack_word})"]

    summaries_dir = Path(args.summaries_dir)
    summary_files = list(summaries_dir.glob("*.json"))
    create_table = len(summary_files) > 0

    success = True
    has_changes = False

    if create_table:
        summary_lines.append("| Status | Stack | Template | Details |")
        summary_lines.append("|:---:|------------|----------------|------------|")

        rows = []
        for summary_file in summary_files:
            try:
                rows.append(json.loads(summary_file.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue

        rows.sort(key=lambda row: (normalize_stack(str(row.get("stack", ""))), env_rank(str(row.get("stack", ""))), str(row.get("stack", ""))))

        for row in rows:
            emoji = "❌"
            stack = str(row.get("stack", ""))
            plan_url = row.get("planUrl") or ""
            plan_summary = row.get("summary") or ""
            template_version = row.get("templateVersion") or "-"
            job_status = row.get("jobStatus") or ""
            row_has_changes = bool(row.get("hasChanges"))

            if job_status == "success":
                emoji = "🟩"
                if row_has_changes:
                    emoji = "🟧"
                    has_changes = True
            else:
                plan_summary = "Plan failed"
                success = False

            if not template_version:
                template_version = "-"

            if plan_url:
                stack_cell = f"[`{stack}`]({plan_url})"
            else:
                stack_cell = f"`{stack}`"

            summary_lines.append(f"|{emoji}|{stack_cell}|{template_version}|{plan_summary}|")

    summary = "\n".join(summary_lines)
    timestamp = datetime.now().strftime("%a %d. %b %T")
    short_sha = args.commit_sha[:8] if args.commit_sha else ""

    if parse_bool(args.is_pull_request):
        content = "\n".join(
            [
                summary,
                f"<!--terraform-pr-github-run-id:{args.github_run_id}-->",
                "<!--terraform-pr-summary-->",
                "",
                "---",
                "",
                "- [ ] Check this box to recreate plans <!--terraform-pr-recreate-->",
                "",
                f"_Time: {timestamp}, commit: {short_sha}_",
                "",
            ]
        )
    else:
        content = "\n".join(
            [
                summary,
                "",
                f"_Time: {timestamp}, commit: {short_sha}_",
                "",
            ]
        )

    output_file = Path(args.output_file)
    output_file.write_text(content, encoding="utf-8")

    if args.github_output:
        github_output = Path(args.github_output)
        write_github_output(github_output, "file", str(output_file))
        write_github_output(github_output, "success", str(success).lower())
        write_github_output(github_output, "has-changes", str(has_changes).lower())

    print(str(output_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
