import unittest

from src.config_analysis import compare_specs, presentation_data, shared_spell_consistency


def spec(spec_id, name, key, spell_id, spell_name):
    return {
        "spec_id": spec_id,
        "spec_name": name,
        "key_bindings": [{
            "display_keys": [key],
            "command": "ACTIONBUTTON2",
            "action_bar_slot": 2,
            "action_type": "spell",
            "spell_id": spell_id,
            "spell_name": spell_name,
        }],
        "click_bindings": [],
    }


class ConfigAnalysisTests(unittest.TestCase):
    def test_presentation_data_is_ready_for_key_display(self):
        current_spec = spec(263, "Enhancement", "ALT-2", 57994, "Wind Shear")
        current_spec["click_bindings"] = [{
            "display_binding": "Shift + LeftButton",
            "action_type": "spell",
            "spell_id": 8004,
            "spell_name": "Healing Surge",
        }]
        data = presentation_data(current_spec)

        self.assertEqual(data["key_bindings"][0]["binding"], "ALT-2")
        self.assertEqual(data["key_bindings"][0]["label"], "Wind Shear")
        self.assertEqual(data["key_bindings"][0]["action_bar_slot"], 2)
        self.assertEqual(data["click_bindings"][0]["binding"], "Shift + LeftButton")
        self.assertEqual(data["click_bindings"][0]["label"], "Healing Surge")

    def test_compare_specs_identifies_exact_and_changed_shared_spells(self):
        specs = {
            "263": spec(263, "Enhancement", "ALT-2", 57994, "Wind Shear"),
            "262": spec(262, "Elemental", "CTRL-2", 57994, "Wind Shear"),
        }
        specs["263"]["key_bindings"].append({
            "display_keys": ["3"],
            "action_type": "spell",
            "spell_id": 188196,
            "spell_name": "Lightning Bolt",
        })

        comparison = compare_specs(specs)

        self.assertEqual(comparison["abilities"][0]["status"], "changed")
        self.assertEqual(comparison["abilities"][1]["status"], "missing")

    def test_shared_spell_consistency_excludes_spec_unique_spells(self):
        specs = {
            "263": spec(263, "Enhancement", "ALT-2", 57994, "Wind Shear"),
            "262": spec(262, "Elemental", "CTRL-2", 57994, "Wind Shear"),
        }

        result = shared_spell_consistency(specs)

        self.assertEqual(len(result["abilities"]), 1)
        self.assertEqual(result["abilities"][0]["status"], "changed")

    def test_compare_specs_identifies_exact_shared_spell_bindings(self):
        specs = {
            "264": spec(264, "Restoration", "ALT-2", 57994, "Wind Shear"),
            "262": spec(262, "Elemental", "ALT-2", 57994, "Wind Shear"),
        }

        result = compare_specs(specs)

        self.assertEqual(result["spec_ids"], ["262", "264"])
        self.assertEqual(result["abilities"][0]["status"], "exact_match")


if __name__ == "__main__":
    unittest.main()