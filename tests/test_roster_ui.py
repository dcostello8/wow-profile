import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.roster_ui import (
    DiscoverState,
    HTML,
    UpdateState,
    activate_character_with_profile_update,
    roster_payload,
    set_all_enabled,
    set_character_enabled,
    start_initial_update,
)


class RosterUITests(unittest.TestCase):
    def write_roster(self, directory):
        path = Path(directory) / "characters.yaml"
        path.write_text(
            "defaults:\n"
            "  update:\n"
            "    profile: true\n"
            "characters:\n"
            "- key: us:id:1\n"
            "  name: Alpha\n"
            "  realm: Windrunner\n"
            "  realm_slug: windrunner\n"
            "  region: us\n"
            "  id: 1\n"
            "  enabled: false\n"
            "- key: us:id:2\n"
            "  name: Beta\n"
            "  realm: Darrowmere\n"
            "  realm_slug: darrowmere\n"
            "  region: us\n"
            "  id: 2\n"
            "  enabled: true\n",
            encoding="utf-8",
        )
        return path

    def test_roster_payload_lists_characters_and_counts_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_roster(directory)

            payload = roster_payload(path)

        self.assertEqual(payload["character_count"], 2)
        self.assertEqual(payload["enabled_count"], 1)
        self.assertEqual(payload["characters"][0]["identity"], "us:id:1")

    def test_set_character_enabled_updates_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_roster(directory)

            payload = set_character_enabled("us:id:1", True, path)
            saved = yaml.safe_load(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["enabled_count"], 2)
        self.assertTrue(saved["characters"][0]["enabled"])
        self.assertTrue(saved["characters"][1]["enabled"])

    def test_activate_character_fetches_profile_before_enabling(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_roster(directory)
            output_path = Path(directory) / "alpha.json"
            index_path = Path(directory) / "roster.json"

            with patch("src.roster_ui.load_config", return_value={"region": "us", "locale": "en_US"}), \
                    patch("src.roster_ui.region_hosts", return_value={"api": "https://example.test"}), \
                    patch("src.roster_ui.get_client_credentials_token", return_value="token"), \
                    patch("src.roster_ui.character_output_path", return_value=output_path), \
                    patch("src.roster_ui.ROSTER_INDEX_FILE", index_path), \
                    patch(
                        "src.roster_ui.fetch_enabled_character_sections",
                        return_value=(
                            {
                                "profile": {
                                    "level": 80,
                                    "character_class": {"name": "Mage"},
                                }
                            },
                            {"profile": {"status": "updated"}},
                        ),
                    ):
                result = activate_character_with_profile_update("us:id:1", path)

            saved = yaml.safe_load(path.read_text(encoding="utf-8"))
            output_exists = output_path.exists()
            index_exists = index_path.exists()

        self.assertTrue(saved["characters"][0]["enabled"])
        self.assertEqual(result["message"], "Activated Alpha - Windrunner.")
        self.assertTrue(output_exists)
        self.assertTrue(index_exists)

    def test_activate_character_keeps_character_inactive_when_profile_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_roster(directory)

            with patch("src.roster_ui.load_config", return_value={"region": "us", "locale": "en_US"}), \
                    patch("src.roster_ui.region_hosts", return_value={"api": "https://example.test"}), \
                    patch("src.roster_ui.get_client_credentials_token", return_value="token"), \
                    patch(
                        "src.roster_ui.fetch_enabled_character_sections",
                        return_value=(
                            {},
                            {
                                "profile": {
                                    "status": "failed",
                                    "status_code": 404,
                                    "error": "HTTP 404: not found",
                                }
                            },
                        ),
                    ):
                with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
                    activate_character_with_profile_update("us:id:1", path)

            saved = yaml.safe_load(path.read_text(encoding="utf-8"))

        self.assertFalse(saved["characters"][0]["enabled"])

    def test_set_all_enabled_can_scope_to_realm(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_roster(directory)

            set_all_enabled(False, realm="Darrowmere", path=path)
            saved = yaml.safe_load(path.read_text(encoding="utf-8"))

        self.assertFalse(saved["characters"][0]["enabled"])
        self.assertFalse(saved["characters"][1]["enabled"])

    def test_discover_state_runs_command(self):
        class Process:
            stdout = ["Wrote characters.yaml.\n"]

            def wait(self):
                return 0

        with patch("src.roster_ui.subprocess.Popen", return_value=Process()):
            state = DiscoverState()
            self.assertTrue(state.start())
            while state.snapshot()["running"]:
                pass

        snapshot = state.snapshot()
        self.assertEqual(snapshot["returncode"], 0)
        self.assertIn("Wrote", snapshot["output"])

    def test_update_state_parses_character_progress(self):
        state = UpdateState()
        state.append_output("Updating [3/13] Thaigan - Windrunner...")

        snapshot = state.snapshot()

        self.assertEqual(snapshot["progress"]["current"], 3)
        self.assertEqual(snapshot["progress"]["total"], 13)
        self.assertEqual(snapshot["progress"]["label"], "Thaigan - Windrunner")
        self.assertEqual(snapshot["progress"]["percent"], 23)

    def test_update_state_tracks_deactivated_characters(self):
        state = UpdateState()
        state.append_output("Set Absecon - Darrowmere inactive because its public profile is unavailable.")

        snapshot = state.snapshot()

        self.assertEqual(snapshot["deactivated"]["count"], 1)
        self.assertEqual(snapshot["deactivated"]["characters"], ["Absecon - Darrowmere"])

    def test_roster_ui_page_polls_update_status_without_starting_refresh(self):
        self.assertNotIn(".then(updateProfiles)", HTML)
        self.assertIn("pollUpdate();", HTML)
        self.assertIn('id="status-side-effects"', HTML)
        self.assertIn("Set inactive:", HTML)

    def test_roster_ui_uses_active_labels(self):
        self.assertIn('<div class="stat-label">Active</div>', HTML)
        self.assertIn('<option value="enabled">Active</option>', HTML)
        self.assertIn('<option value="disabled">Inactive</option>', HTML)
        self.assertIn("Activate Visible", HTML)
        self.assertIn("Deactivate Visible", HTML)
        self.assertIn("<th>Active</th>", HTML)
        self.assertNotIn(">Enabled<", HTML)
        self.assertNotIn(">Disabled<", HTML)

    def test_server_startup_starts_initial_update(self):
        class State:
            def __init__(self):
                self.started = False

            def start(self):
                self.started = True
                return True

        class Server:
            update_state = State()

        server = Server()

        self.assertTrue(start_initial_update(server))
        self.assertTrue(server.update_state.started)


if __name__ == "__main__":
    unittest.main()
