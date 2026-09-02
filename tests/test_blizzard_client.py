import tempfile
import unittest
from pathlib import Path

from src.blizzard.cache import JsonCache
from src.blizzard.client import BlizzardClient, namespace
from src.blizzard.game_data.classes import ClassService
from src.blizzard.game_data.items import ItemService
from src.blizzard.game_data.journal import JournalService
from src.blizzard.game_data.mythic_plus import MythicPlusService
from src.blizzard.game_data.professions import ProfessionService
from src.blizzard.game_data.realms import RealmService
from src.blizzard.game_data.spells import SpellService
from src.blizzard.game_data.talents import TalentService
from src.blizzard.profile.account import AccountProfileService
from src.blizzard.profile.character import CharacterProfileService


class Response:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        self.headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({
            "url": url,
            "headers": headers,
            "params": params,
            "timeout": timeout,
        })
        return self.response


class BlizzardClientTests(unittest.TestCase):
    def client(self, response=None):
        session = Session(response or Response({"ok": True}))
        client = BlizzardClient(
            {"region": "us", "locale": "en_US"},
            "token",
            hosts={"api": "https://us.api.blizzard.test"},
            session=session,
        )
        return client, session

    def assert_urls(self, session, paths):
        urls = [call["url"] for call in session.calls]
        self.assertEqual(
            urls,
            [f"https://us.api.blizzard.test{path}" for path in paths],
        )

    def test_namespace_uses_explicit_type_and_region(self):
        self.assertEqual(namespace("profile", "us"), "profile-us")
        self.assertEqual(namespace("static", "eu"), "static-eu")

    def test_client_adds_auth_namespace_locale_and_timeout(self):
        client, session = self.client()

        data = client.get("/profile/user/wow", namespace_type="profile")

        self.assertEqual(data, {"ok": True})
        self.assertEqual(session.calls[0]["url"], "https://us.api.blizzard.test/profile/user/wow")
        self.assertEqual(session.calls[0]["headers"]["Authorization"], "Bearer token")
        self.assertEqual(session.calls[0]["params"]["namespace"], "profile-us")
        self.assertEqual(session.calls[0]["params"]["locale"], "en_US")
        self.assertEqual(session.calls[0]["timeout"], 30)

    def test_account_profile_service_uses_profile_namespace(self):
        client, session = self.client()

        AccountProfileService(client).get_wow_profile()

        self.assertEqual(session.calls[0]["url"], "https://us.api.blizzard.test/profile/user/wow")
        self.assertEqual(session.calls[0]["params"]["namespace"], "profile-us")

    def test_account_profile_service_routes_collection_endpoints(self):
        client, session = self.client()
        service = AccountProfileService(client)

        service.get_collections()
        service.get_mounts()
        service.get_pets()

        self.assert_urls(session, [
            "/profile/user/wow/collections",
            "/profile/user/wow/collections/mounts",
            "/profile/user/wow/collections/pets",
        ])

    def test_character_service_routes_phase_one_sections(self):
        client, session = self.client()
        service = CharacterProfileService(client)
        character = {"realm_slug": "windrunner", "name": "Example"}

        service.get_statistics(character)
        service.get_media(character)
        service.get_reputations(character)
        service.get_titles(character)

        urls = [call["url"] for call in session.calls]
        self.assertIn("https://us.api.blizzard.test/profile/wow/character/windrunner/example/statistics", urls)
        self.assertIn("https://us.api.blizzard.test/profile/wow/character/windrunner/example/character-media", urls)
        self.assertIn("https://us.api.blizzard.test/profile/wow/character/windrunner/example/reputations", urls)
        self.assertIn("https://us.api.blizzard.test/profile/wow/character/windrunner/example/titles", urls)

    def test_character_service_routes_existing_and_optional_sections(self):
        client, session = self.client()
        service = CharacterProfileService(client)
        character = {"realm_slug": "windrunner", "name": "Example"}

        service.get_profile(character)
        service.get_equipment(character)
        service.get_specializations(character)
        service.get_professions(character)
        service.get_mythic_keystone_profile(character)
        service.get_mythic_keystone_profile_season(character, 12)
        service.get_pvp_bracket(character, "3v3")
        service.get_section(character, "achievements")
        service.get_section(character, "completed_quests")
        service.get_section(character, "soulbinds")

        self.assert_urls(session, [
            "/profile/wow/character/windrunner/example",
            "/profile/wow/character/windrunner/example/equipment",
            "/profile/wow/character/windrunner/example/specializations",
            "/profile/wow/character/windrunner/example/professions",
            "/profile/wow/character/windrunner/example/mythic-keystone-profile",
            "/profile/wow/character/windrunner/example/mythic-keystone-profile/season/12",
            "/profile/wow/character/windrunner/example/pvp-bracket/3v3",
            "/profile/wow/character/windrunner/example/achievements",
            "/profile/wow/character/windrunner/example/quests/completed",
            "/profile/wow/character/windrunner/example/soulbinds",
        ])

    def test_game_data_services_use_static_namespace(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            SpellService(client, cache).get_spell(8004)
            ItemService(client, cache).get_item(19019)
            ProfessionService(client, cache).get_recipe(12345)

        namespaces = [call["params"]["namespace"] for call in session.calls]
        self.assertEqual(namespaces, ["static-us", "static-us", "static-us"])
        urls = [call["url"] for call in session.calls]
        self.assertIn("https://us.api.blizzard.test/data/wow/spell/8004", urls)
        self.assertIn("https://us.api.blizzard.test/data/wow/item/19019", urls)
        self.assertIn("https://us.api.blizzard.test/data/wow/recipe/12345", urls)

    def test_class_service_routes_supported_endpoints(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            service = ClassService(client, cache)
            service.get_index()
            service.get_class(7)
            service.get_media(7)

        self.assert_urls(session, [
            "/data/wow/playable-class/index",
            "/data/wow/playable-class/7",
            "/data/wow/media/playable-class/7",
        ])

    def test_talent_service_routes_supported_endpoints(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            service = TalentService(client, cache)
            service.get_talent_index()
            service.get_talent(1)
            service.get_pvp_talent_index()
            service.get_pvp_talent(2)
            service.get_talent_tree_index()
            service.get_talent_tree(3)
            service.get_talent_tree(3, spec_id=264)

        self.assert_urls(session, [
            "/data/wow/talent/index",
            "/data/wow/talent/1",
            "/data/wow/pvp-talent/index",
            "/data/wow/pvp-talent/2",
            "/data/wow/talent-tree/index",
            "/data/wow/talent-tree/3",
            "/data/wow/talent-tree/3/playable-specialization/264",
        ])

    def test_profession_service_routes_supported_endpoints(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            service = ProfessionService(client, cache)
            service.get_index()
            service.get_profession(182)
            service.get_skill_tier(182, 2477)
            service.get_media(182)
            service.get_recipe(12345)
            service.get_recipe_media(12345)

        self.assert_urls(session, [
            "/data/wow/profession/index",
            "/data/wow/profession/182",
            "/data/wow/profession/182/skill-tier/2477",
            "/data/wow/media/profession/182",
            "/data/wow/recipe/12345",
            "/data/wow/media/recipe/12345",
        ])

    def test_mythic_plus_service_routes_supported_endpoints(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            service = MythicPlusService(client, cache)
            service.get_dungeon_index()
            service.get_dungeon(500)
            service.get_period_index()
            service.get_period(1000)
            service.get_season_index()
            service.get_season(12)
            service.get_affix_index()
            service.get_affix(10)
            service.get_affix_media(10)

        self.assert_urls(session, [
            "/data/wow/mythic-keystone/dungeon/index",
            "/data/wow/mythic-keystone/dungeon/500",
            "/data/wow/mythic-keystone/period/index",
            "/data/wow/mythic-keystone/period/1000",
            "/data/wow/mythic-keystone/season/index",
            "/data/wow/mythic-keystone/season/12",
            "/data/wow/keystone-affix/index",
            "/data/wow/keystone-affix/10",
            "/data/wow/media/keystone-affix/10",
        ])

    def test_journal_service_routes_supported_endpoints(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            service = JournalService(client, cache)
            service.get_expansion_index()
            service.get_expansion(10)
            service.get_instance_index()
            service.get_instance(1271)
            service.get_encounter_index()
            service.get_encounter(2902)
            service.search_encounters(name="Example")

        self.assert_urls(session, [
            "/data/wow/journal-expansion/index",
            "/data/wow/journal-expansion/10",
            "/data/wow/journal-instance/index",
            "/data/wow/journal-instance/1271",
            "/data/wow/journal-encounter/index",
            "/data/wow/journal-encounter/2902",
            "/data/wow/search/journal-encounter",
        ])

    def test_realm_service_routes_supported_endpoints(self):
        client, session = self.client()
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            service = RealmService(client, cache)
            service.get_region_index()
            service.get_region(1)
            service.get_realm_index()
            service.get_realm("windrunner")
            service.search_realms(name="Windrunner")
            service.get_connected_realm_index()
            service.get_connected_realm(11)
            service.search_connected_realms(id=11)

        self.assert_urls(session, [
            "/data/wow/region/index",
            "/data/wow/region/1",
            "/data/wow/realm/index",
            "/data/wow/realm/windrunner",
            "/data/wow/search/realm",
            "/data/wow/connected-realm/index",
            "/data/wow/connected-realm/11",
            "/data/wow/search/connected-realm",
        ])

    def test_json_cache_reuses_persistent_reference_data(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))

            first = cache.get_or_fetch("spells", "8004", lambda: calls.append("fetch") or {"id": 8004})
            second = cache.get_or_fetch("spells", "8004", lambda: calls.append("again") or {"id": 0})

        self.assertEqual(first, {"id": 8004})
        self.assertEqual(second, {"id": 8004})
        self.assertEqual(calls, ["fetch"])


if __name__ == "__main__":
    unittest.main()
