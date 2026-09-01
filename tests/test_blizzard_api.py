import unittest
from unittest.mock import patch

import requests

from src.blizzard_api import fetch_enabled_character_sections


class BlizzardApiTests(unittest.TestCase):
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
