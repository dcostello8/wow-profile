import tempfile
import unittest
from pathlib import Path

import yaml

from src.config import (
    DEFAULT_UPDATE_SETTINGS,
    enabled_characters,
    merge_roster,
    selected_update_sections,
    update_settings_for_character,
)


def account_profile(*characters):
    return {
        "wow_accounts": [
            {
                "id": 101,
                "characters": list(characters),
            }
        ]
    }


def discovered_character(character_id, name, realm_name="Windrunner", realm_slug="windrunner"):
    return {
        "id": character_id,
        "name": name,
        "realm": {
            "id": 87,
            "name": realm_name,
            "slug": realm_slug,
        },
        "protected_character": {
            "href": f"https://example.test/profile/{character_id}",
        },
    }


class ConfigTests(unittest.TestCase):
    def test_hunter_pets_is_supported_but_disabled_by_default(self):
        self.assertFalse(DEFAULT_UPDATE_SETTINGS["hunter_pets"])
        self.assertNotIn("hunter_pets", selected_update_sections(DEFAULT_UPDATE_SETTINGS))

    def test_character_override_enables_hunter_pets(self):
        settings = update_settings_for_character(
            {"characters": []},
            {"update": {"hunter_pets": True}},
        )

        self.assertTrue(settings["hunter_pets"])
        self.assertIn("hunter_pets", selected_update_sections(settings))

    def test_merge_marks_absent_characters_stale_and_inactive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "characters.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "characters": [
                            {
                                "key": "us:id:1",
                                "name": "Present",
                                "enabled": True,
                                "region": "us",
                                "id": 1,
                                "realm": "Windrunner",
                                "realm_slug": "windrunner",
                                "stale": False,
                            },
                            {
                                "key": "us:id:2",
                                "name": "Missing",
                                "enabled": True,
                                "region": "us",
                                "id": 2,
                                "realm": "Darrowmere",
                                "realm_slug": "darrowmere",
                                "stale": False,
                            },
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            roster = merge_roster(
                {"region": "us"},
                account_profile(discovered_character(1, "Present")),
                path,
            )

        by_id = {character["id"]: character for character in roster["characters"]}
        self.assertFalse(by_id[1]["stale"])
        self.assertTrue(by_id[1]["enabled"])
        self.assertTrue(by_id[2]["stale"])
        self.assertFalse(by_id[2]["enabled"])

    def test_merge_rediscovered_character_returns_to_not_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "characters.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "characters": [
                            {
                                "key": "us:id:2",
                                "name": "Missing",
                                "enabled": False,
                                "region": "us",
                                "id": 2,
                                "realm": "Darrowmere",
                                "realm_slug": "darrowmere",
                                "stale": True,
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            roster = merge_roster(
                {"region": "us"},
                account_profile(discovered_character(2, "Missing", "Darrowmere", "darrowmere")),
                path,
            )

        character = roster["characters"][0]
        self.assertFalse(character["stale"])
        self.assertFalse(character["enabled"])

    def test_enabled_characters_excludes_stale_entries(self):
        characters = [
            {"name": "Active", "enabled": True, "stale": False},
            {"name": "Stale", "enabled": True, "stale": True},
            {"name": "Inactive", "enabled": False, "stale": False},
        ]

        self.assertEqual(enabled_characters(characters), [characters[0]])


if __name__ == "__main__":
    unittest.main()
