import tempfile
import unittest
from pathlib import Path

import yaml

from src.binding_audit import audit_active_controls, audit_assignments, load_binding_rules


class BindingAuditTests(unittest.TestCase):
    def role_map(self):
        return {100: {"name": "Interrupt", "roles": ["interrupt"]}}

    def documents(self, source="key", binding="ALT-2"):
        spec = {
            "spec_id": 263,
            "spec_name": "Enhancement",
            "key_bindings": [],
            "click_bindings": [],
        }
        if source == "key":
            spec["key_bindings"] = [{
                "display_keys": [binding],
                "action_type": "spell",
                "spell_id": 100,
                "spell_name": "Interrupt",
            }]
        else:
            spec["click_bindings"] = [{
                "display_binding": binding,
                "action_type": "spell",
                "spell_id": 100,
                "spell_name": "Interrupt",
            }]
        return [{
            "character": {"name": "Example", "key": "us:id:1"},
            "local_client_data": {"specs": {"263": spec}},
        }]

    def rule_map(self, source="key", binding="ALT-2"):
        return {"interrupt": {"expected": {"source": source, "binding": binding}, "scope": {}}}

    def test_pass(self):
        result = audit_active_controls(self.documents(), self.role_map(), self.rule_map())
        self.assertEqual(result[0]["results"][0]["status"], "PASS")

    def test_mismatch(self):
        result = audit_active_controls(self.documents(binding="CTRL-2"), self.role_map(), self.rule_map())
        self.assertEqual(result[0]["results"][0]["status"], "MISMATCH")

    def test_key_click_mismatch(self):
        result = audit_active_controls(self.documents(source="click", binding="ALT-2"), self.role_map(), self.rule_map())
        self.assertEqual(result[0]["results"][0]["status"], "MISMATCH")

    def test_not_applicable(self):
        result = audit_active_controls([], self.role_map(), self.rule_map())
        self.assertEqual(result[0]["results"][0]["status"], "NOT_APPLICABLE")

    def test_missing(self):
        result = audit_assignments([{
            "role": "interrupt",
            "character": "Example",
            "spec_name": "Enhancement",
            "ability": "Interrupt",
            "source": None,
            "binding": None,
        }], self.rule_map())

        self.assertEqual(result[0]["results"][0]["status"], "MISSING")

    def test_malformed_rules_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.yaml"
            path.write_text(yaml.safe_dump({"rules": {"interrupt": {"expected": {"source": "bad", "binding": "ALT-2"}}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_binding_rules(path)

    def test_multiple_actual_bindings_are_audited_individually(self):
        documents = self.documents()
        documents[0]["local_client_data"]["specs"]["263"]["key_bindings"].append({
            "display_keys": ["CTRL-2"],
            "action_type": "spell",
            "spell_id": 100,
            "spell_name": "Interrupt",
        })
        result = audit_active_controls(documents, self.role_map(), self.rule_map())
        self.assertEqual(result[0]["pass_count"], 1)
        self.assertEqual(result[0]["issue_count"], 1)


if __name__ == "__main__":
    unittest.main()
