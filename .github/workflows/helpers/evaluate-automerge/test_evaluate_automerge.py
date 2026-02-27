import json
import unittest

import evaluate_automerge as ea


def _make_commit_message(upgrades: list) -> str:
    """Build a commit message containing the golden-path-renovate-summary marker."""
    inner = ",".join(json.dumps(u, separators=(",", ":")) for u in upgrades)
    return f"some text\n<!--golden-path-renovate-summary:[{inner}]-->\nmore text"


def _upgrade(
    *,
    package_file_dir="stacks/dev/app",
    dep_name="app",
    update_type="minor",
    current_value="1.0.0",
    new_value="1.1.0",
    package_name="oslokommune/golden-path-boilerplate",
):
    return {
        "packageName": package_name,
        "packageFileDir": package_file_dir,
        "depName": dep_name,
        "updateType": update_type,
        "currentValue": current_value,
        "newValue": new_value,
    }


DEFAULT_RULES = [
    {"pattern": "**/prod/**", "major": "never", "minor": "no-changes", "patch": "any-changes"},
    {"pattern": "**", "major": "no-changes", "minor": "any-changes", "patch": "any-changes"},
]


class TestBasicApproval(unittest.TestCase):
    def test_approves_minor_dev_any_changes(self):
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="minor")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True}
        self.assertTrue(ea.evaluate(commit_message, DEFAULT_RULES, stack_changes))

    def test_approves_patch_no_changes(self):
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": False}
        self.assertTrue(ea.evaluate(commit_message, DEFAULT_RULES, stack_changes))


class TestUnknownPackage(unittest.TestCase):
    def test_rejects_unknown_package(self):
        upgrades = [_upgrade(package_name="oslokommune/some-other-repo")]
        commit_message = _make_commit_message(upgrades)
        self.assertFalse(ea.evaluate(commit_message, DEFAULT_RULES, {}))


class TestPatternMatching(unittest.TestCase):
    def test_first_match_wins_prod(self):
        """prod pattern matches first, so major=never applies."""
        upgrades = [_upgrade(package_file_dir="stacks/prod/app", update_type="major")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/prod/app": False}
        self.assertFalse(ea.evaluate(commit_message, DEFAULT_RULES, stack_changes))

    def test_first_match_wins_dev(self):
        """dev doesn't match prod pattern, falls through to ** catch-all."""
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="major")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": False}
        self.assertTrue(ea.evaluate(commit_message, DEFAULT_RULES, stack_changes))

    def test_no_matching_rule_rejects(self):
        """If no rule pattern matches, the upgrade is rejected."""
        rules = [{"pattern": "stacks/prod/**", "patch": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        self.assertFalse(ea.evaluate(commit_message, rules, {}))

    def test_glob_pattern_with_nested_dirs(self):
        rules = [{"pattern": "stacks/**/networking/**", "minor": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/networking/vpc", update_type="minor")]
        commit_message = _make_commit_message(upgrades)
        self.assertTrue(ea.evaluate(commit_message, rules, {}))

    def test_prod_at_root(self):
        """prod/my-stack matches **/prod/**."""
        rules = [{"pattern": "**/prod/**", "patch": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="prod/my-stack", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        self.assertTrue(ea.evaluate(commit_message, rules, {}))

    def test_environments_prod(self):
        rules = [{"pattern": "**/prod/**", "patch": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="environments/prod/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        self.assertTrue(ea.evaluate(commit_message, rules, {}))

    def test_terraform_prod(self):
        rules = [{"pattern": "**/prod/**", "patch": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="terraform/prod/dns", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        self.assertTrue(ea.evaluate(commit_message, rules, {}))

    def test_deeply_nested_prod(self):
        rules = [{"pattern": "**/prod/**", "patch": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="a/b/prod/c/d", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        self.assertTrue(ea.evaluate(commit_message, rules, {}))

    def test_dev_does_not_match_prod_pattern(self):
        rules = [{"pattern": "**/prod/**", "patch": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        self.assertFalse(ea.evaluate(commit_message, rules, {}))


class TestPolicies(unittest.TestCase):
    def test_never_always_rejects(self):
        rules = [{"pattern": "**", "minor": "never"}]
        upgrades = [_upgrade(update_type="minor")]
        commit_message = _make_commit_message(upgrades)
        self.assertFalse(ea.evaluate(commit_message, rules, {}))

    def test_no_changes_allows_when_no_changes(self):
        rules = [{"pattern": "**", "patch": "no-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": False}
        self.assertTrue(ea.evaluate(commit_message, rules, stack_changes))

    def test_no_changes_rejects_when_has_changes(self):
        rules = [{"pattern": "**", "patch": "no-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True}
        self.assertFalse(ea.evaluate(commit_message, rules, stack_changes))

    def test_any_changes_allows_regardless(self):
        rules = [{"pattern": "**", "major": "any-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="major")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True}
        self.assertTrue(ea.evaluate(commit_message, rules, stack_changes))

    def test_default_policy_is_no_changes(self):
        """If the rule doesn't specify a policy for the update type, default to no-changes."""
        rules = [{"pattern": "**"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="minor")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": False}
        self.assertTrue(ea.evaluate(commit_message, rules, stack_changes))

    def test_default_policy_rejects_with_changes(self):
        rules = [{"pattern": "**"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="minor")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True}
        self.assertFalse(ea.evaluate(commit_message, rules, stack_changes))

    def test_no_changes_with_missing_stack_in_changes(self):
        """If a stack is not in stack_changes, it's treated as no changes."""
        rules = [{"pattern": "**", "patch": "no-changes"}]
        upgrades = [_upgrade(package_file_dir="stacks/dev/app", update_type="patch")]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {}
        self.assertTrue(ea.evaluate(commit_message, rules, stack_changes))


class TestEdgeCases(unittest.TestCase):
    def test_empty_upgrades_rejects(self):
        commit_message = "<!--golden-path-renovate-summary:[]-->"
        self.assertFalse(ea.evaluate(commit_message, DEFAULT_RULES, {}))

    def test_missing_marker_rejects(self):
        commit_message = "just a normal commit message"
        self.assertFalse(ea.evaluate(commit_message, DEFAULT_RULES, {}))

    def test_empty_commit_message_rejects(self):
        self.assertFalse(ea.evaluate("", DEFAULT_RULES, {}))


class TestMultipleUpgrades(unittest.TestCase):
    def test_all_must_pass(self):
        upgrades = [
            _upgrade(package_file_dir="stacks/dev/app", update_type="minor"),
            _upgrade(package_file_dir="stacks/prod/app", update_type="minor"),
        ]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True, "stacks/prod/app": False}
        self.assertTrue(ea.evaluate(commit_message, DEFAULT_RULES, stack_changes))

    def test_one_failure_rejects_all(self):
        upgrades = [
            _upgrade(package_file_dir="stacks/dev/app", update_type="minor"),
            _upgrade(package_file_dir="stacks/prod/app", update_type="major"),
        ]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True, "stacks/prod/app": False}
        self.assertFalse(ea.evaluate(commit_message, DEFAULT_RULES, stack_changes))

    def test_multiple_upgrades_different_stacks(self):
        rules = [
            {"pattern": "stacks/dev/**", "patch": "any-changes"},
            {"pattern": "stacks/prod/**", "patch": "no-changes"},
        ]
        upgrades = [
            _upgrade(package_file_dir="stacks/dev/app", update_type="patch"),
            _upgrade(package_file_dir="stacks/prod/app", update_type="patch"),
        ]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True, "stacks/prod/app": False}
        self.assertTrue(ea.evaluate(commit_message, rules, stack_changes))

    def test_multiple_upgrades_one_stack_has_changes(self):
        rules = [
            {"pattern": "stacks/dev/**", "patch": "any-changes"},
            {"pattern": "stacks/prod/**", "patch": "no-changes"},
        ]
        upgrades = [
            _upgrade(package_file_dir="stacks/dev/app", update_type="patch"),
            _upgrade(package_file_dir="stacks/prod/app", update_type="patch"),
        ]
        commit_message = _make_commit_message(upgrades)
        stack_changes = {"stacks/dev/app": True, "stacks/prod/app": True}
        self.assertFalse(ea.evaluate(commit_message, rules, stack_changes))


if __name__ == "__main__":
    unittest.main()
