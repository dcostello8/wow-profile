import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import requests

from src.blizzard.cache import JsonCache
from src.config import DEFAULT_UPDATE_SETTINGS, selected_update_sections
from src.output import account_collections_section
from src.cli import (
    deactivate_if_public_profile_unavailable,
    discover,
    ensure_collection_catalogs,
    fetch_account_collection,
    main,
    public_profile_unavailable,
)


class CliTests(unittest.TestCase):
    def test_update_continues_profile_updates_when_catalog_warming_fails(self):
        character = {
            "key": "us:id:1",
            "name": "Example",
            "realm": "Windrunner",
            "realm_slug": "windrunner",
            "region": "us",
            "id": 1,
            "enabled": True,
            "stale": False,
        }
        with patch("src.cli.load_config", return_value={"region": "us"}), patch(
            "src.cli.region_hosts", return_value={"api": "https://example.test"}
        ), patch(
            "src.cli.load_character_roster", return_value=(
                {"characters": [character]}, [character]
            )
        ), patch(
            "src.cli.get_client_credentials_token", return_value="token"
        ), patch(
            "src.cli.ensure_collection_catalogs",
            return_value={
                "mounts": {"status": "failed"},
                "pets": {"status": "failed"},
            },
        ), patch(
            "src.cli.selected_update_sections", return_value=["profile"]
        ), patch(
            "src.cli.fetch_enabled_character_sections",
            return_value=({"profile": {}}, {"profile": {"status": "updated"}}),
        ) as fetch_sections, patch(
            "src.cli.character_output_path", return_value=Path("output/example.json")
        ), patch(
            "src.cli.load_json_file", return_value=None
        ), patch(
            "src.cli.write_json"
        ), patch(
            "src.cli.refresh_local_output_summaries"
        ):
            result = __import__("src.cli", fromlist=["update"]).update()

        self.assertEqual(result, 0)
        fetch_sections.assert_called_once()

    def test_successful_catalog_warming_feeds_account_summary_calculations(self):
        class FakeClient:
            def get(self, path, namespace_type=None, params=None):
                return {
                    "mounts": [{"id": 1, "name": "Swift Horse"}]
                } if path.endswith("mount/index") else {
                    "pets": [{"id": 2, "name": "Cat"}]
                }

        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            with patch("src.cli.BlizzardClient", return_value=FakeClient()):
                result = ensure_collection_catalogs(
                    {"region": "us", "locale": "en_US"}, {}, "token", cache
                )
            html = account_collections_section({
                "mounts": {"status": "updated", "data": {"mounts": [{"id": 1}]}},
                "pets": {"status": "updated", "data": {"pets": [{"id": 2}]}},
            }, cache)

        self.assertEqual(result["mounts"]["status"], "updated")
        self.assertEqual(result["pets"]["status"], "updated")
        self.assertIn("1 collected / 0 missing", html)
    def test_missing_collection_catalogs_are_fetched_and_cached(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            def get(self, path, namespace_type=None, params=None):
                self.calls.append(path)
                return {"path": path}

        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            client = FakeClient()
            with patch("src.cli.BlizzardClient", return_value=client):
                result = ensure_collection_catalogs(
                    {"region": "us", "locale": "en_US"}, {}, "token", cache
                )

            self.assertEqual(result["mounts"]["status"], "updated")
            self.assertEqual(result["pets"]["status"], "updated")
            self.assertEqual(client.calls, [
                "/data/wow/mount/index",
                "/data/wow/pet/index",
            ])
            self.assertEqual(
                cache.get("mounts", "/data/wow/mount/index"),
                {"path": "/data/wow/mount/index"},
            )
            self.assertEqual(
                cache.get("pets", "/data/wow/pet/index"),
                {"path": "/data/wow/pet/index"},
            )

    def test_existing_collection_catalogs_are_reused(self):
        class FakeClient:
            def get(self, *args, **kwargs):
                raise AssertionError("cached catalog should not fetch")

        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            cache.set("mounts", "/data/wow/mount/index", {"mounts": []})
            cache.set("pets", "/data/wow/pet/index", {"pets": []})
            with patch("src.cli.BlizzardClient", return_value=FakeClient()):
                result = ensure_collection_catalogs(
                    {"region": "us", "locale": "en_US"}, {}, "token", cache
                )

        self.assertEqual(result, {
            "mounts": {"status": "updated"},
            "pets": {"status": "updated"},
        })

    def test_catalog_fetch_failure_isolated_from_other_catalog(self):
        class FakeClient:
            def get(self, path, namespace_type=None, params=None):
                if path.endswith("mount/index"):
                    raise RuntimeError("mount service unavailable")
                return {"pets": []}

        with tempfile.TemporaryDirectory() as directory:
            with patch("src.cli.BlizzardClient", return_value=FakeClient()):
                result = ensure_collection_catalogs(
                    {"region": "us", "locale": "en_US"}, {}, "token",
                    JsonCache(Path(directory)),
                )

        self.assertEqual(result["mounts"]["status"], "failed")
        self.assertEqual(result["pets"]["status"], "updated")

    def test_fetch_account_collection_preserves_http_failure_details(self):
        response = requests.Response()
        response.status_code = 503
        response._content = b"temporarily unavailable"
        error = requests.HTTPError(response=response)

        result = fetch_account_collection(
            lambda *_: (_ for _ in ()).throw(error), {}, {}, "token"
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["status_code"], 503)
        self.assertIn("temporarily unavailable", result["error"])

    @patch("src.cli.save_roster")
    @patch("src.cli.merge_roster", return_value={"characters": []})
    @patch("src.cli.write_json")
    @patch("src.cli.fetch_account_pets", side_effect=RuntimeError("pets unavailable"))
    @patch("src.cli.fetch_account_mounts", return_value={"mounts": []})
    @patch("src.cli.exchange_code_for_token", return_value="token")
    @patch("src.cli.wait_for_authorization_code", return_value="code")
    @patch("src.cli.load_config", return_value={"region": "us"})
    def test_discover_writes_collections_when_pet_fetch_fails(
        self,
        load_config,
        wait_for_code,
        exchange_token,
        fetch_mounts,
        fetch_pets,
        write_json,
        merge,
        save,
    ):
        with patch("src.cli.fetch_account_profile", return_value={"wow_accounts": []}), patch(
            "src.cli.region_hosts", return_value={"api": "https://example.test"}
        ):
            discover()

        collection_file, collections = write_json.call_args_list[0].args
        self.assertEqual(collection_file, Path("output/account_collections.json"))
        self.assertEqual(collections["mounts"], {"status": "updated", "data": {"mounts": []}})
        self.assertEqual(collections["pets"]["status"], "failed")
        self.assertEqual(collections["pets"]["error"], "pets unavailable")
        merge.assert_called_once()
        save.assert_called_once()

    def test_discover_continues_when_mount_fetch_fails(self):
        with patch("src.cli.load_config", return_value={"region": "us"}), patch(
            "src.cli.region_hosts", return_value={"api": "https://example.test"}
        ), patch("src.cli.wait_for_authorization_code", return_value="code"), patch(
            "src.cli.exchange_code_for_token", return_value="token"
        ), patch(
            "src.cli.fetch_account_profile", return_value={"wow_accounts": []}
        ), patch(
            "src.cli.fetch_account_mounts", side_effect=RuntimeError("mounts unavailable")
        ), patch(
            "src.cli.fetch_account_pets", return_value={"pets": []}
        ), patch(
            "src.cli.write_json"
        ), patch(
            "src.cli.merge_roster", return_value={"characters": []}
        ) as merge, patch("src.cli.save_roster") as save:
            discover()

        merge.assert_called_once()
        save.assert_called_once()

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
