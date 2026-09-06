"""Audit classified controls against curated binding conventions."""

from pathlib import Path

import yaml

from .control_analysis import aggregate_role_bindings, load_ability_roles

DEFAULT_RULE_FILE = Path("data/binding_rules.yaml")
AUDIT_STATUSES = {"PASS", "MISMATCH", "MISSING", "NOT_APPLICABLE"}


def load_binding_rules(path=DEFAULT_RULE_FILE):
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Binding rule data must be a mapping.")
    if data.get("version", 1) != 1:
        raise ValueError(f"Unsupported binding rule schema version: {data.get('version')!r}")
    rules = data.get("rules")
    if not isinstance(rules, dict):
        raise ValueError("Binding rule data must contain a 'rules' mapping.")

    normalized = {}
    for role, definition in rules.items():
        if not isinstance(role, str) or not role.strip():
            raise ValueError("Binding rule role names must be non-empty strings.")
        if not isinstance(definition, dict):
            raise ValueError(f"Binding rule {role!r} must be a mapping.")
        expected = definition.get("expected")
        if not isinstance(expected, dict):
            raise ValueError(f"Binding rule {role!r} must define expected source/binding.")
        source = expected.get("source")
        binding = expected.get("binding")
        if source not in {"key", "click"}:
            raise ValueError(f"Binding rule {role!r} source must be 'key' or 'click'.")
        if not isinstance(binding, str) or not binding.strip():
            raise ValueError(f"Binding rule {role!r} binding must be a non-empty string.")
        normalized[role.strip()] = {
            "expected": {"source": source, "binding": binding},
            "scope": definition.get("scope") or {},
        }
    return normalized


def _audit_assignment(assignment, expected):
    if not assignment.get("binding") or not assignment.get("source"):
        status = "MISSING"
    elif (
        assignment.get("source") == expected["source"]
        and assignment.get("binding") == expected["binding"]
    ):
        status = "PASS"
    else:
        status = "MISMATCH"
    return {
        **assignment,
        "expected_source": expected["source"],
        "expected_binding": expected["binding"],
        "status": status,
    }


def audit_assignments(assignments, rules):
    results = []
    for role, rule in rules.items():
        role_assignments = [item for item in assignments if item.get("role") == role]
        audited = [_audit_assignment(item, rule["expected"]) for item in role_assignments]
        if not audited:
            audited = [{
                "role": role,
                "status": "NOT_APPLICABLE",
                "expected_source": rule["expected"]["source"],
                "expected_binding": rule["expected"]["binding"],
            }]
        results.append({
            "role": role,
            "expected": rule["expected"],
            "scope": rule.get("scope") or {},
            "results": audited,
            "pass_count": sum(item["status"] == "PASS" for item in audited),
            "issue_count": sum(item["status"] in {"MISMATCH", "MISSING"} for item in audited),
        })
    return results


def audit_active_controls(documents, role_map=None, rules=None):
    role_map = load_ability_roles() if role_map is None else role_map
    rules = load_binding_rules() if rules is None else rules
    return audit_assignments(aggregate_role_bindings(documents, role_map), rules)
