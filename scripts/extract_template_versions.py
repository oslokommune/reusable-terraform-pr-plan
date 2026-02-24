#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def clean_value(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    value = re.split(r"\s+#", value, 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


def extract_boilerplate_versions(stack_dir: Path) -> list[str]:
    versions: list[str] = []
    boilerplate_dir = stack_dir / ".boilerplate"
    if not boilerplate_dir.is_dir():
        return versions
    for path in sorted(boilerplate_dir.glob("_template_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = str(data.get("name") or "").strip()
        version = str(data.get("version") or "").strip()
        if version:
            entry = f"{name}@{version}" if name else version
            versions.append(entry)
    return versions


def parse_packages_file(path: Path) -> list[str]:
    entries: list[str] = []
    in_packages = False
    template = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        if re.match(r"^\s*Packages\s*:", line):
            in_packages = True
            continue
        if not in_packages:
            continue
        template_match = re.match(r"^\s*Template\s*:\s*(.+)$", line)
        if template_match:
            template = clean_value(template_match.group(1))
            continue
        ref_match = re.match(r"^\s*Ref\s*:\s*(.+)$", line)
        if ref_match:
            ref = clean_value(ref_match.group(1))
            if ref:
                entry = ref
                if template:
                    pattern = rf"^{re.escape(template)}[-_]?v?(.+)$"
                    match = re.match(pattern, ref)
                    if match:
                        entry = f"{template}@{match.group(1)}"
                    else:
                        entry = f"{template}@{ref}"
                entries.append(entry)
            template = ""
            continue
    return entries


def extract_packages_versions(stack_dir: Path) -> list[str]:
    for filename in ("packages.yml", "packages.yaml"):
        path = stack_dir / filename
        if path.is_file():
            return parse_packages_file(path)
    return []


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def write_github_output(path: Path, key: str, value: str) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract template versions for a stack.")
    parser.add_argument("--stack-dir", default=".", help="Path to the stack directory.")
    parser.add_argument("--github-output", help="Path to GITHUB_OUTPUT to write key=value.")
    parser.add_argument("--output-key", default="result", help="Output key for GITHUB_OUTPUT.")
    parser.add_argument("--output-file", help="Optional file to write the versions string.")
    args = parser.parse_args()

    stack_dir = Path(args.stack_dir)
    versions = extract_boilerplate_versions(stack_dir) + extract_packages_versions(stack_dir)
    versions = dedupe(versions)
    result = ", ".join(versions) if versions else "-"

    if args.output_file:
        Path(args.output_file).write_text(result + "\n", encoding="utf-8")

    if args.github_output:
        write_github_output(Path(args.github_output), args.output_key, result)

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
