"""Evaluate whether a Renovate PR should be automerged.

Parses structured upgrade info from the commit body and evaluates it against
per-stack automerge rules and Terraform plan results.

Usage:
  python3 evaluate_automerge.py --commit-body <str> --rules <json> --stack-changes <json> --success true|false

Output: prints "true" or "false" to stdout.
"""

import argparse
import fnmatch
import json
import re
import sys

MARKER_PATTERN = re.compile(
    r"<!--golden-path-renovate-summary:\[(.+?)\]-->"
)

ALLOWED_PACKAGE = "oslokommune/golden-path-boilerplate"
VALID_POLICIES = {"never", "no-changes", "any-changes"}
DEFAULT_POLICY = "no-changes"


def parse_upgrades(commit_body: str) -> list[dict] | None:
    """Extract the upgrades array from the commit body marker.

    Returns None if the marker is not found.
    """
    match = MARKER_PATTERN.search(commit_body)
    if not match:
        return None
    return json.loads(f"[{match.group(1)}]")


def match_rule(package_file_dir: str, rules: list[dict]) -> dict | None:
    """Find the first rule whose pattern matches the packageFileDir."""
    for rule in rules:
        if fnmatch.fnmatch(package_file_dir, rule["pattern"]):
            return rule
    return None


def evaluate_upgrade(
    upgrade: dict,
    rule: dict,
    stack_changes: dict,
) -> bool:
    """Evaluate a single upgrade against its matched rule and plan result."""
    update_type = upgrade["updateType"]
    policy = rule.get(update_type, DEFAULT_POLICY)

    if policy not in VALID_POLICIES:
        print(
            f"Warning: unknown policy '{policy}' for update type "
            f"'{update_type}', treating as '{DEFAULT_POLICY}'",
            file=sys.stderr,
        )
        policy = DEFAULT_POLICY

    if policy == "never":
        return False

    if policy == "any-changes":
        return True

    # policy == "no-changes": allow only if the stack has no Terraform changes
    package_file_dir = upgrade["packageFileDir"]
    has_changes = stack_changes.get(package_file_dir, False)
    return not has_changes


def evaluate(
    commit_body: str,
    rules: list[dict],
    stack_changes: dict,
    success: bool,
) -> bool:
    """Main evaluation: returns True if the PR should be automerged."""
    if not success:
        return False

    upgrades = parse_upgrades(commit_body)
    if upgrades is None:
        return False

    if len(upgrades) == 0:
        return False

    for upgrade in upgrades:
        if upgrade.get("packageName") != ALLOWED_PACKAGE:
            return False

        rule = match_rule(upgrade["packageFileDir"], rules)
        if rule is None:
            return False

        if not evaluate_upgrade(upgrade, rule, stack_changes):
            return False

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Renovate PR automerge eligibility")
    parser.add_argument("--commit-body", required=True, help="Full commit message body")
    parser.add_argument("--rules", required=True, help="JSON array of automerge rules")
    parser.add_argument("--stack-changes", required=True, help="JSON object mapping stack paths to booleans")
    parser.add_argument("--success", required=True, choices=["true", "false"], help="Whether all Terraform plans succeeded")
    args = parser.parse_args()

    result = evaluate(
        args.commit_body,
        json.loads(args.rules),
        json.loads(args.stack_changes),
        args.success == "true",
    )
    print("true" if result else "false")
