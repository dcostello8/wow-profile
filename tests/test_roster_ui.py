import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.roster_ui import (
    DiscoverState,
    HTML,
    UpdateState,
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
            "  region: us\n"
            "  id: 1\n"
            "  enabled: false\n"
            "- key: us:id:2\n"
            "  name: Beta\n"
            "  realm: Darrowmere\n"
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

    def test_roster_ui_page_polls_update_status_without_starting_refresh(self):
        self.assertNotIn(".then(updateProfiles)", HTML)
        self.assertIn("pollUpdate();", HTML)

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
