import unittest
from unittest.mock import patch

from src.config import DEFAULT_UPDATE_SETTINGS, selected_update_sections
from src.cli import (
    deactivate_if_public_profile_unavailable,
    main,
    public_profile_unavailable,
)


class CliTests(unittest.TestCase):
    def test_public_profile_unavailable_detects_403_and_404(self):
        for status_code in (403, 404):
            with self.subTest(status_code=status_code):
                self.assertTrue(public_profile_unavailable({
                    "profile": {
                        "status": "failed",
                        "status_code": status_code,
                    }
                }))

    def test_public_profile_unavailable_ignores_other_failures(self):
        self.assertFalse(public_profile_unavailable({
            "profile": {
                "status": "failed",
                "status_code": 500,
            }
        }))
        self.assertFalse(public_profile_unavailable({
            "equipment": {
                "status": "failed",
                "status_code": 404,
            }
        }))

    def test_deactivate_if_public_profile_unavailable_marks_character_inactive(self):
        character = {"name": "Example", "enabled": True}

        changed = deactivate_if_public_profile_unavailable(character, {
            "profile": {
                "status": "failed",
                "status_code": 404,
            }
        })

        self.assertTrue(changed)
        self.assertFalse(character["enabled"])

    def test_deactivate_if_public_profile_unavailable_keeps_accessible_character_active(self):
        character = {"name": "Example", "enabled": True}

        changed = deactivate_if_public_profile_unavailable(character, {
            "profile": {
                "status": "updated",
            }
        })

        self.assertFalse(changed)
        self.assertTrue(character["enabled"])

    def test_default_update_sections_include_phase_one_profile_endpoints(self):
        sections = selected_update_sections(DEFAULT_UPDATE_SETTINGS)

        self.assertEqual(sections, [
            "profile",
            "equipment",
            "specializations",
            "statistics",
            "professions",
            "mythic_plus",
            "media",
            "reputations",
            "titles",
        ])

    def test_no_arguments_start_the_local_page(self):
        with patch("src.cli.import_latest_local_data"), patch("src.cli.refresh_local_output_summaries"), patch(
            "src.cli.run_roster_ui", return_value=0
        ) as run_ui:
            self.assertEqual(main([]), 0)

        run_ui.assert_called_once_with(
            "127.0.0.1",
            8765,
            on_roster_change=unittest.mock.ANY,
        )


if __name__ == "__main__":
    unittest.main()
