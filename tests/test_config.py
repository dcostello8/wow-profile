import tempfile
import unittest
from pathlib import Path

import yaml

from src.config import (
    DEFAULT_UPDATE_SETTINGS,
    enabled_characters,
    is_hunter,
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


def discovered_character(
    character_id,
    name,
    realm_name="Windrunner",
    realm_slug="windrunner",
    class_id=None,
    class_name=None,
):
    playable_class = {}
    if class_id is not None:
        playable_class["id"] = class_id
    if class_name is not None:
        playable_class["name"] = class_name
    return {
        "id": character_id,
        "name": name,
        "realm": {
            "id": 87,
            "name": realm_name,
            "slug": realm_slug,
        },
        "playable_class": playable_class,
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

    def test_hunter_detection_prefers_class_id_over_name(self):
        self.assertTrue(is_hunter({"class_id": 3, "class_name": "Not Hunter"}))
        self.assertFalse(is_hunter({"class_id": 8, "class_name": "Hunter"}))
        self.assertTrue(is_hunter({"class_name": "Hunter"}))
        self.assertFalse(is_hunter({"class_id": 8}))

    def test_hunters_auto_enable_hunter_pets_without_override(self):
        hunter_settings = update_settings_for_character(
            {"characters": []},
            {"class_id": 3, "class_name": "Hunter"},
        )
        non_hunter_settings = update_settings_for_character(
            {"characters": []},
            {"class_id": 8, "class_name": "Mage"},
        )

        self.assertTrue(hunter_settings["hunter_pets"])
        self.assertFalse(non_hunter_settings["hunter_pets"])

    def test_explicit_hunter_pet_overrides_remain_authoritative(self):
        character_settings = update_settings_for_character(
            {"characters": []},
            {"class_id": 3, "update": {"hunter_pets": False}},
        )
        default_settings = update_settings_for_character(
            {"defaults": {"update": {"hunter_pets": False}}},
            {"class_id": 3},
        )

        self.assertFalse(character_settings["hunter_pets"])
        self.assertFalse(default_settings["hunter_pets"])

    def test_merge_preserves_class_metadata_state_and_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "characters.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "characters": [{
                            "key": "us:id:1",
                            "name": "Hunter",
                            "enabled": True,
                            "region": "us",
                            "id": 1,
                            "realm": "Windrunner",
                            "realm_slug": "windrunner",
                            "stale": False,
                            "update": {"hunter_pets": False},
                        }]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            roster = merge_roster(
                {"region": "us"},
                account_profile(discovered_character(1, "Hunter", class_id=3, class_name="Hunter")),
                path,
            )

        character = roster["characters"][0]
        self.assertEqual(character["class_id"], 3)
        self.assertEqual(character["class_name"], "Hunter")
        self.assertTrue(character["enabled"])
        self.assertFalse(character["stale"])
        self.assertEqual(character["update"], {"hunter_pets": False})

    def test_merge_keeps_existing_class_metadata_when_discovery_omits_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "characters.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "characters": [{
                            "key": "us:id:3",
                            "name": "Hunter",
                            "enabled": False,
                            "region": "us",
                            "id": 3,
                            "class_id": 3,
                            "class_name": "Hunter",
                            "stale": False,
                        }]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            roster = merge_roster(
                {"region": "us"},
                account_profile(discovered_character(3, "Hunter")),
                path,
            )

        character = roster["characters"][0]
        self.assertEqual(character["class_id"], 3)
        self.assertEqual(character["class_name"], "Hunter")

    def test_stale_merge_preserves_class_metadata_and_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "characters.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "characters": [{
                            "key": "us:id:2",
                            "name": "Hunter",
                            "enabled": True,
                            "region": "us",
                            "id": 2,
                            "class_id": 3,
                            "class_name": "Hunter",
                            "update": {"hunter_pets": True},
                        }]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            roster = merge_roster(
                {"region": "us"},
                account_profile(),
                path,
            )

        character = roster["characters"][0]
        self.assertTrue(character["stale"])
        self.assertFalse(character["enabled"])
        self.assertEqual(character["class_id"], 3)
        self.assertEqual(character["class_name"], "Hunter")
        self.assertEqual(character["update"], {"hunter_pets": True})

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
