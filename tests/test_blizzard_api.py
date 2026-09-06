import unittest
from unittest.mock import patch

import requests

from src.blizzard_api import (
    fetch_account_mounts,
    fetch_account_pets,
    fetch_enabled_character_sections,
)


class BlizzardApiTests(unittest.TestCase):
    @patch("src.blizzard_api.AccountProfileService")
    def test_fetch_account_collections_use_account_service(self, service_class):
        service = service_class.return_value
        service.get_mounts.return_value = {"mounts": []}
        service.get_pets.return_value = {"pets": []}

        self.assertEqual(
            fetch_account_mounts(
                {"region": "us", "locale": "en_US"}, {}, "token"
            ), {"mounts": []}
        )
        self.assertEqual(
            fetch_account_pets(
                {"region": "us", "locale": "en_US"}, {}, "token"
            ), {"pets": []}
        )
        service.get_mounts.assert_called_once_with()
        service.get_pets.assert_called_once_with()

    def test_fetch_enabled_character_sections_records_http_status_code(self):
        response = requests.Response()
        response.status_code = 404
        response._content = b"not found"
        error = requests.HTTPError(response=response)

        with patch("src.blizzard_api.fetch_character_resource", side_effect=error):
            _, section_status = fetch_enabled_character_sections(
                {"region": "us", "locale": "en_US"},
                {"api": "https://example.test"},
                "token",
                {"realm_slug": "windrunner", "name": "Example"},
                ["profile"],
            )

        self.assertEqual(section_status["profile"]["status"], "failed")
        self.assertEqual(section_status["profile"]["status_code"], 404)


if __name__ == "__main__":
    unittest.main()
