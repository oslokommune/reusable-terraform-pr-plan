#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def sanitize_artifact_name(stack: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9-]", "-", stack)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return f"summary-{cleaned}"


def write_github_output(path: Path, key: str, value: str) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a per-stack summary JSON artifact.")
    parser.add_argument("--stack", required=True)
    parser.add_argument("--job-status", required=True)
    parser.add_argument("--has-changes", required=True)
    parser.add_argument("--summary", default="")
    parser.add_argument("--template-version", default="-")
    parser.add_argument("--plan-url", default="")
    parser.add_argument("--output-dir", default="/tmp")
    parser.add_argument("--output-file")
    parser.add_argument("--github-output")
    args = parser.parse_args()

    has_changes = parse_bool(args.has_changes)
    artifact_name = sanitize_artifact_name(args.stack)
    output_file = Path(args.output_file) if args.output_file else Path(args.output_dir) / f"{artifact_name}.json"

    payload = {
        "stack": args.stack,
        "hasChanges": has_changes,
        "jobStatus": args.job_status,
        "summary": args.summary,
        "templateVersion": args.template_version,
        "planUrl": args.plan_url,
    }

    output_file.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    if args.github_output:
        github_output = Path(args.github_output)
        write_github_output(github_output, "artifact-name", artifact_name)
        write_github_output(github_output, "file", str(output_file))

    print(str(output_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
