import tempfile
import unittest
from pathlib import Path

import yaml

from src.control_analysis import (
    aggregate_role_bindings,
    analyze_active_controls,
    classify_spec_controls,
    load_ability_roles,
)


class ControlAnalysisTests(unittest.TestCase):
    def role_map(self):
        return {
            100: {"name": "Interrupt One", "roles": ["interrupt"]},
            200: {"name": "Interrupt Two", "roles": ["interrupt", "utility"]},
        }

    def spec(self):
        return {
            "spec_id": 263,
            "spec_name": "Enhancement",
            "key_bindings": [{
                "display_keys": ["ALT-2"],
                "action_type": "spell",
                "spell_id": 100,
                "spell_name": "Interrupt One",
            }],
            "click_bindings": [{
                "display_binding": "Shift + Left Click",
                "action_type": "spell",
                "spell_id": 200,
                "spell_name": "Interrupt Two",
            }],
        }

    def test_load_role_file_validates_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roles.yaml"
            path.write_text(yaml.safe_dump({"abilities": {"100": {"roles": ["interrupt"]}}}), encoding="utf-8")
            roles = load_ability_roles(path)

        self.assertEqual(roles[100]["roles"], ["interrupt"])

    def test_invalid_role_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roles.yaml"
            path.write_text("abilities: []", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_ability_roles(path)

    def test_classifies_spell_by_id_and_supports_multiple_roles(self):
        assignments = classify_spec_controls(self.spec(), self.role_map())

        self.assertEqual({item["role"] for item in assignments}, {"interrupt", "utility"})
        self.assertEqual(assignments[0]["spell_id"], 100)

    def test_unknown_spell_is_preserved_as_unclassified(self):
        spec = self.spec()
        spec["key_bindings"][0]["spell_id"] = 999

        self.assertEqual(classify_spec_controls(spec, self.role_map()), [
            {
                "role": None,
                "spell_id": 999,
                "ability": "Interrupt One",
                "binding": "ALT-2",
                "source": "key",
                "spec_id": 263,
                "spec_name": "Enhancement",
            },
            {
                "role": "interrupt",
                "spell_id": 200,
                "ability": "Interrupt Two",
                "binding": "Shift + Left Click",
                "source": "click",
                "spec_id": 263,
                "spec_name": "Enhancement",
            },
            {
                "role": "utility",
                "spell_id": 200,
                "ability": "Interrupt Two",
                "binding": "Shift + Left Click",
                "source": "click",
                "spec_id": 263,
                "spec_name": "Enhancement",
            },
        ])

    def test_aggregates_across_characters_and_preserves_source(self):
        documents = [
            {
                "character": {"name": "First", "key": "one"},
                "local_client_data": {"specs": {"263": self.spec()}},
            },
            {
                "character": {"name": "Second", "key": "two"},
                "local_client_data": {"specs": {"264": {
                    "spec_id": 264,
                    "spec_name": "Retribution",
                    "key_bindings": [{
                        "display_keys": ["ALT-2"],
                        "action_type": "spell",
                        "spell_id": 200,
                        "spell_name": "Interrupt Two",
                    }],
                    "click_bindings": [],
                }}},
            },
        ]

        assignments = aggregate_role_bindings(documents, self.role_map())

        self.assertEqual(len(assignments), 5)
        self.assertEqual(assignments[0]["source"], "key")
        self.assertEqual(assignments[1]["source"], "click")
        self.assertEqual(assignments[-1]["character"], "Second")

    def test_analyze_active_controls_marks_same_role_consistent(self):
        documents = [{
            "character": {"name": "First"},
            "local_client_data": {"specs": {"263": self.spec()}},
        }]

        results = analyze_active_controls(documents, self.role_map())
        by_role = {result["role"]: result for result in results}

        self.assertEqual(by_role["interrupt"]["status"], "varied")
        self.assertEqual(by_role["utility"]["status"], "consistent")


if __name__ == "__main__":
    unittest.main()
