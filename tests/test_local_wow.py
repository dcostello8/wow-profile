import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.local_wow import (
    character_match_key,
    import_saved_variables,
    merge_local_character_data,
    normalize_action,
    normalize_click_binding,
    normalize_key_binding,
    normalized_characters,
    parse_saved_variables,
)


FIXTURE = Path(__file__).parent / "fixtures" / "WowProfileCollector.lua"


class LocalWowTests(unittest.TestCase):
    def test_parse_saved_variables(self):
        data = parse_saved_variables(FIXTURE)

        self.assertEqual(data["schema_version"], 1)
        self.assertIn("Windrunner", data["characters"])
        self.assertIn("Jaedon", data["characters"]["Windrunner"])

    def test_parse_saved_variables_rejects_unsupported_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "WowProfileCollector.lua"
            path.write_text(
                "WowProfileCollectorDB = { schema_version = 99, characters = {} }",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(Exception, "Unsupported .*schema version"):
                parse_saved_variables(path)

    def test_normalized_characters_preserve_specs_separately(self):
        data = parse_saved_variables(FIXTURE)
        data["characters"]["Windrunner"]["Jaedon"]["0"] = {"spec_name": None}
        characters = normalized_characters(data)

        self.assertEqual(len(characters), 1)
        specs = characters[0]["specs"]
        self.assertEqual(len(characters[0]["equipment_sets"]), 2)
        self.assertEqual(characters[0]["equipment_sets"][1]["name"], "Fishing")
        self.assertEqual(characters[0]["equipment_sets"][1]["item_level"]["equipped"], 645)
        self.assertNotIn("0", specs)
        self.assertEqual(specs["262"]["spec_name"], "Elemental")
        self.assertEqual(specs["262"]["item_level"]["equipped"], 681.25)
        self.assertEqual(specs["264"]["spec_name"], "Restoration")
        self.assertEqual(specs["262"]["client_configuration"]["action_bars"][0]["type"], "spell")

    def test_click_binding_normalization(self):
        data = parse_saved_variables(FIXTURE)
        character = normalized_characters(data)[0]
        binding = character["specs"]["264"]["click_bindings"][0]

        self.assertEqual(binding["action"], "Chain Heal")
        self.assertEqual(binding["spell_id"], 1064)
        self.assertEqual(binding["button"], "LeftButton")
        self.assertEqual(binding["modifiers"], ["SHIFT"])

    def test_key_binding_normalization_preserves_action_slot_relationship(self):
        binding = normalize_key_binding({
            "command": "ACTIONBUTTON4",
            "category": "Action Bar",
            "keys": ["ALT-5"],
            "action_bar_slot": 4,
            "action": {
                "slot": 4,
                "type": "spell",
                "id": 8004,
                "spell": {"id": 8004, "name": "Healing Surge"},
            },
        })

        self.assertEqual(binding["keys"], ["ALT-5"])
        self.assertEqual(binding["command"], "ACTIONBUTTON4")
        self.assertEqual(binding["action_bar_slot"], 4)
        self.assertEqual(binding["action_type"], "spell")
        self.assertEqual(binding["spell_name"], "Healing Surge")
        self.assertEqual(binding["display_keys"], ["ALT-5"])

    def test_click_binding_normalization_has_structured_modifiers_and_display(self):
        binding = normalize_click_binding({
            "type": "spell",
            "spell": {"id": 8004, "name": "Healing Surge"},
            "button": "LeftButton",
            "modifiers": ["SHIFT"],
        })

        self.assertEqual(binding["modifier_flags"], {"shift": True, "ctrl": False, "alt": False})
        self.assertEqual(binding["display_binding"], "Shift + LeftButton")

    def test_action_normalization_preserves_macro_resolution(self):
        action = normalize_action({
            "slot": 4,
            "type": "macro",
            "id": 17,
            "macro": {"id": 17, "name": "Mouseover Heal", "body": "/cast Healing Surge"},
        })

        self.assertEqual(action["type"], "macro")
        self.assertEqual(action["macro"]["body"], "/cast Healing Surge")

    def test_character_matching_is_name_and_realm_case_insensitive(self):
        self.assertEqual(
            character_match_key("Jaedon", "Windrunner"),
            character_match_key("jaedon", "WINDRUNNER"),
        )

    def test_merge_local_data_into_existing_document(self):
        local_character = normalized_characters(parse_saved_variables(FIXTURE))[0]
        document = {"character": {"name": "Jaedon", "realm": "Windrunner"}}

        merged = merge_local_character_data(document, local_character, "2026-08-31T19:00:00Z")

        self.assertIn("local_client_data", merged)
        self.assertEqual(len(merged["local_client_data"]["equipment_sets"]), 2)
        self.assertIn("262", merged["local_client_data"]["specs"])
        self.assertIn("264", merged["local_client_data"]["specs"])
        self.assertIn("configuration_comparison", merged["local_client_data"])
        self.assertIn("configuration_presentation", merged["local_client_data"]["specs"]["262"])

    def test_import_handles_missing_output_for_matched_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            roster_path = temp_path / "characters.yaml"
            roster_path.write_text(
                "characters:\n"
                "- name: Jaedon\n"
                "  realm: Windrunner\n"
                "  realm_slug: windrunner\n"
                "  id: 170301178\n",
                encoding="utf-8",
            )

            with patch("src.local_wow.load_character_roster") as load_roster:
                load_roster.return_value = (
                    {},
                    [{
                        "name": "Jaedon",
                        "realm": "Windrunner",
                        "realm_slug": "windrunner",
                        "id": 170301178,
                    }],
                )
                with patch("src.local_wow.character_output_path", return_value=temp_path / "missing.json"):
                    result = import_saved_variables(FIXTURE)

        self.assertEqual(result.matched, 0)
        self.assertEqual(result.missing_output, 1)
        self.assertEqual(result.unmatched, 0)

    def test_import_merges_existing_generated_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "jaedon.json"
            output_path.write_text(json.dumps({"character": {"name": "Jaedon"}}), encoding="utf-8")

            with patch("src.local_wow.load_character_roster") as load_roster:
                load_roster.return_value = (
                    {},
                    [{
                        "name": "Jaedon",
                        "realm": "Windrunner",
                        "realm_slug": "windrunner",
                        "id": 170301178,
                    }],
                )
                with patch("src.local_wow.character_output_path", return_value=output_path):
                    result = import_saved_variables(FIXTURE)

            merged = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.matched, 1)
        self.assertIn("local_client_data", merged)
        self.assertIn("262", merged["local_client_data"]["specs"])


if __name__ == "__main__":
    unittest.main()
